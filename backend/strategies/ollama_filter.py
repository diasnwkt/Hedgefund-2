"""
Local LLM signal filter using llama-cpp-python (CPU inference, no Metal).

Loads the GGUF model from Ollama's on-disk cache (auto-detected from the
manifest) so no separate download is needed. Model is kept in a module-level
singleton — it loads once on first filter call and is reused for every
subsequent signal in the same process.

XGBoost generates a signal numerically; this filter asks the LLM to reason
about whether the technical indicators support that signal. If the LLM
disagrees, the signal is downgraded to HOLD. All errors fall through
transparently — the original XGBoost signal passes through unchanged.
"""
import asyncio
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

import structlog

from strategies.base import SignalResult

log = structlog.get_logger(__name__)

_llm = None  # module-level singleton, loaded lazily


def _find_gguf_from_ollama(model_name: str) -> Optional[str]:
    """Resolve a model name like 'llama3.2:3b' to its GGUF blob path in ~/.ollama."""
    parts = model_name.split(":")
    library = parts[0]
    tag = parts[1] if len(parts) > 1 else "latest"

    manifest_path = (
        Path.home()
        / ".ollama/models/manifests/registry.ollama.ai/library"
        / library
        / tag
    )
    if not manifest_path.exists():
        return None

    with open(manifest_path) as f:
        manifest = json.load(f)

    for layer in manifest.get("layers", []):
        if "model" in layer.get("mediaType", ""):
            digest = layer["digest"].replace(":", "-")
            blob = Path.home() / f".ollama/models/blobs/{digest}"
            if blob.exists():
                return str(blob)

    return None


def _load_model(model_path: str, n_ctx: int = 1024) -> object:
    from llama_cpp import Llama  # imported lazily to avoid startup cost
    log.info("llm_loading", path=model_path)
    llm = Llama(
        model_path=model_path,
        n_gpu_layers=0,  # CPU-only — no Metal
        n_ctx=n_ctx,
        verbose=False,
    )
    log.info("llm_loaded", path=model_path)
    return llm


def _get_llm(model_path: str) -> Optional[object]:
    global _llm
    if _llm is None:
        try:
            _llm = _load_model(model_path)
        except Exception as exc:
            log.error("llm_load_failed", error=str(exc))
            return None
    return _llm


def _build_prompt(signal_result: SignalResult, features: dict) -> str:
    rsi = features.get("rsi_14")
    macd = features.get("macd")
    macd_signal_val = features.get("macd_signal")
    ma_20 = features.get("ma_20")
    ma_50 = features.get("ma_50")
    ma_cross = features.get("ma_cross", 0)
    momentum_5d = features.get("momentum_5d")
    momentum_20d = features.get("momentum_20d")
    volume_zscore = features.get("volume_zscore")
    bb_pct_b = features.get("bb_pct_b")
    atr_14 = features.get("atr_14")
    adx_14 = features.get("adx_14")

    rsi_label = ""
    if rsi is not None:
        if rsi < 30:
            rsi_label = " (oversold)"
        elif rsi > 70:
            rsi_label = " (overbought)"

    macd_trend = ""
    if macd is not None and macd_signal_val is not None:
        macd_trend = "bullish crossover" if macd > macd_signal_val else "bearish crossover"

    ma_position = "above both MAs" if ma_cross and ma_cross > 0 else "below both MAs"

    def fmt(v, d=4):
        return f"{v:.{d}f}" if v is not None else "N/A"

    def fmt_pct(v):
        return f"{v:+.2%}" if v is not None else "N/A"

    return (
        f"You are a quantitative trading analyst. Evaluate whether the proposed trading signal "
        f"is supported by the technical indicators below.\n\n"
        f"Stock: {signal_result.ticker}\n"
        f"Proposed signal: {signal_result.signal} (XGBoost confidence: {signal_result.confidence:.1%})\n\n"
        f"Technical indicators (latest values):\n"
        f"- RSI(14): {fmt(rsi, 1)}{rsi_label}\n"
        f"- MACD: {fmt(macd)}, Signal line: {fmt(macd_signal_val)} — {macd_trend}\n"
        f"- MA20: {fmt(ma_20, 2)}, MA50: {fmt(ma_50, 2)} — price is {ma_position}\n"
        f"- 5d momentum: {fmt_pct(momentum_5d)}, 20d momentum: {fmt_pct(momentum_20d)}\n"
        f"- Volume Z-score: {fmt(volume_zscore, 2)}\n"
        f"- Bollinger %B: {fmt(bb_pct_b, 3)} (0=lower band, 1=upper band)\n"
        f"- ATR(14): {fmt(atr_14, 2)} (volatility)\n"
        f"- ADX(14): {fmt(adx_14, 1)} (trend strength; >25=trending)\n\n"
        f"Respond with JSON only:\n"
        f'{{ "confirmed": true, "reasoning": "one sentence", '
        f'"rationale": "2-3 sentence recommendation explanation for a portfolio manager", '
        f'"adjusted_confidence": 0.72 }}\n\n'
        f"Rules: confirmed=true if technicals support the {signal_result.signal} signal; "
        f"adjusted_confidence is your 0.0–1.0 estimate."
    )


def _parse_response(text: str) -> Optional[dict]:
    text = text.strip()
    match = re.search(r"\{[^{}]+\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    try:
        data = json.loads(text)
        return {
            "confirmed": bool(data.get("confirmed", True)),
            "reasoning": str(data.get("reasoning", "")),
            "rationale": str(data.get("rationale", "")),
            "adjusted_confidence": max(0.0, min(1.0, float(data.get("adjusted_confidence", 0.5)))),
        }
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def _run_inference(llm, prompt: str, max_tokens: int = 250) -> str:
    result = llm.create_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_tokens=max_tokens,
        temperature=0.1,
        seed=42,
    )
    return result["choices"][0]["message"]["content"]


@dataclass
class OllamaSignalFilter:
    model_name: str
    model_path: str  # explicit path; empty = auto-detect from Ollama cache
    confirm_threshold: float = 0.5

    def _resolve_model_path(self) -> Optional[str]:
        if self.model_path:
            return self.model_path
        return _find_gguf_from_ollama(self.model_name)

    async def filter(self, signal_result: SignalResult, latest_features: dict) -> SignalResult:
        resolved = self._resolve_model_path()
        if resolved is None:
            log.warning("llm_model_not_found", model=self.model_name)
            return signal_result

        loop = asyncio.get_event_loop()
        try:
            llm = await loop.run_in_executor(None, _get_llm, resolved)
            if llm is None:
                return signal_result

            prompt = _build_prompt(signal_result, latest_features)
            raw = await loop.run_in_executor(None, _run_inference, llm, prompt, 250)
        except Exception as exc:
            log.warning("llm_filter_error", ticker=signal_result.ticker, error=str(exc))
            return signal_result

        parsed = _parse_response(raw)
        if parsed is None:
            log.warning("llm_parse_failed", ticker=signal_result.ticker, raw=raw[:200])
            return signal_result

        log.info(
            "llm_filter_result",
            ticker=signal_result.ticker,
            original_signal=signal_result.signal,
            confirmed=parsed["confirmed"],
            reasoning=parsed["reasoning"],
            rationale=parsed["rationale"][:100],
            adjusted_confidence=round(parsed["adjusted_confidence"], 4),
        )

        if not parsed["confirmed"]:
            return SignalResult(
                ticker=signal_result.ticker,
                signal="HOLD",
                confidence=parsed["adjusted_confidence"],
                model_version=signal_result.model_version + "+llm_override",
                rationale=parsed.get("rationale", ""),
            )

        return SignalResult(
            ticker=signal_result.ticker,
            signal=signal_result.signal,
            confidence=parsed["adjusted_confidence"],
            model_version=signal_result.model_version + "+llm",
            rationale=parsed.get("rationale", ""),
        )
