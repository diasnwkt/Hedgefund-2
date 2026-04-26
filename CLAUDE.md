# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running locally (no Docker)

This project runs without Docker on macOS using Homebrew Postgres and Redis.

**Backend** (must run from `backend/` directory so module imports resolve without the `backend.` prefix):
```bash
cd backend && ../.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
cd frontend && npm run dev
```

**Database migrations** (also from `backend/`):
```bash
cd backend && alembic upgrade head
cd backend && alembic revision --autogenerate -m "describe change"
```

**Seed DB** (from project root):
```bash
.venv/bin/python scripts/init_db.py --password <plain_password>
```

## Tests, lint, format

```bash
# Run all tests
pytest backend/tests -v

# Single test file
pytest backend/tests/test_risk_limits.py -v

# With coverage
pytest backend/tests -v --cov=backend --cov-report=term-missing

# Lint (ruff + black check + mypy)
ruff check backend ml scripts
black --check backend ml scripts
mypy backend

# Auto-fix formatting
black backend ml scripts && ruff check --fix backend ml scripts
```

Tests use SQLite in-memory (not Postgres) and fakeredis. `SCHEDULER_ENABLED=false` is set via `pyproject.toml` pytest env so the scheduler never starts during tests.

## ML training

```bash
# From project root — downloads yfinance data directly (no DB needed)
.venv/bin/python ml/train.py

# Backfill 5 years of price history into Postgres, then compute features
.venv/bin/python scripts/backfill_prices.py
```

The trained model is saved to `ml/models/xgb_<date>_<time>.pkl` with a `.json` metadata sidecar. `SignalGenerator` auto-loads the latest `.pkl` by mtime.

## Architecture

### Request path
```
HTTP → FastAPI (main.py) → routers/ → services/ or direct DB → response
```
All routers require JWT auth via `get_current_user` (Bearer token). The only unprotected routes are `POST /auth/login` and `GET /health`.

### Key module boundaries

| Layer | Location | Responsibility |
|---|---|---|
| Config | `backend/config.py` | Single `Settings` Pydantic class; `get_settings()` is `@lru_cache` — one instance for app lifetime |
| DB models | `backend/db/models.py` | 8 SQLAlchemy 2.0 tables: `tickers`, `prices`, `features`, `signals`, `positions`, `orders`, `equity_snapshots`, `audit_log` + `app_settings` |
| Data pipeline | `backend/data/` | `fetcher.py` (yfinance → DB), `preprocessor.py` (prices → features), `calendar.py` (NYSE holiday checks) |
| Strategy | `backend/strategies/` | `ml_strategy.py` wraps XGBoost; `signal_generator.py` runs it for all active tickers |
| Portfolio | `backend/portfolio/` | `manager.py` orchestrates orders; `paper_broker.py` simulates fills with slippage/commission |
| Broker | `backend/broker/` | `base.py` abstract interface; `alpaca.py` live implementation via alpaca-py SDK |
| Risk | `backend/risk/` | `limits.py` has `PreTradeChecker.check_all()` (6-step chain) + `check_stop_losses` + `check_portfolio_drawdown`; `metrics.py` computes Sharpe/drawdown/beta |
| Scheduler | `backend/scheduler.py` | APScheduler cron jobs; all jobs lazy-import from their modules to avoid circular imports |
| Frontend | `frontend/src/` | React 18 + Vite 5 + Tailwind; pages in `pages/`, shared components in `components/`, API calls in `api/` |

### Scheduler job schedule (ET, market days only)
- `16:30` fetch_prices
- `16:45` compute_features
- `17:00` generate_signals
- `17:05` execute_signals (off by default: `JOB_EXECUTE_SIGNALS_ENABLED=false`)
- `17:10` snapshot_equity
- `*/30` check_stops (off by default), check_drawdown
- Sunday `23:00` retrain_model (off by default)

### Kill-switch
Stored in Redis keys `killswitch:active`, `killswitch:reason`, `killswitch:activated_at`. Auto-activates when portfolio drawdown exceeds `PORTFOLIO_DRAWDOWN_LIMIT` (default 20%). Manual control via `POST /risk/killswitch`.

### Trading mode
`app_settings` table key `trading_mode` overrides the `.env` default at runtime. Switching to `live` requires both `ALPACA_LIVE_ENABLED=true` in `.env` (requires restart) and `confirm: "I_UNDERSTAND_RISK"` in the API body.

### .env critical notes
- Inline comments in `.env` are parsed as part of the value by pydantic-settings — keep all lines comment-free.
- `config.py` walks up from `backend/` to find `.env`, so it works whether uvicorn is started from `backend/` or the project root.
- `model_dir` is a settings field that uses Pydantic's reserved `model_` prefix — `protected_namespaces=("settings_",)` suppresses the warning.

### Frontend auth flow
JWT stored in `localStorage`. `AuthGuard` in `App.jsx` checks for token and redirects to `/login` if absent. Token is sent as `Authorization: Bearer <token>` on every API call.

### Local LLM signal filter (Ollama / llama-cpp-python)

After XGBoost generates a signal, an optional LLM filter reasons about whether the technical indicators support it. Controlled by `OLLAMA_ENABLED=true` in `.env`.

**Runtime:** Uses `llama-cpp-python` (CPU-only, Metal disabled) — NOT the Ollama HTTP server. The Ollama server has a Metal/GPU incompatibility on macOS 16 (Darwin 25.x). The filter loads the GGUF model file directly from `~/.ollama/models/blobs/` using the model manifest for auto-detection.

**How it works:**
- `OllamaSignalFilter` in `backend/strategies/ollama_filter.py`
- Model loaded lazily into a module-level singleton on first call
- Async: runs synchronous llama-cpp inference in a thread pool via `run_in_executor`
- `confirmed=true` → use LLM's adjusted confidence; `confirmed=false` → downgrade to HOLD
- Model version is suffixed with `+llm` (confirmed) or `+llm_override` (overridden)
- Any error (load failure, parse failure) falls through transparently — original XGBoost signal used

**Config keys:** `OLLAMA_ENABLED`, `OLLAMA_MODEL` (e.g. `llama3.2:3b`), `OLLAMA_MODEL_PATH` (empty = auto-detect from `~/.ollama`), `OLLAMA_CONFIRM_THRESHOLD`

**Install:** `CMAKE_ARGS="-DGGML_METAL=OFF -DGGML_BLAS=OFF" pip install llama-cpp-python --no-cache-dir`

### Adding a new API route
1. Create `backend/routers/<name>.py` with an `APIRouter`
2. Add schema(s) to `backend/schemas/<name>.py`
3. Register with `app.include_router(...)` in `backend/main.py`
