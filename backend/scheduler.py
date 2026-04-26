from datetime import date, timedelta

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import Settings

log = structlog.get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


def _make_scheduler(timezone: str) -> AsyncIOScheduler:
    return AsyncIOScheduler(timezone=timezone)


async def _job_fetch_prices() -> None:
    log.info("job_start", job="fetch_prices")
    try:
        from data.calendar import is_trading_day
        if not is_trading_day():
            log.info("job_skipped_holiday", job="fetch_prices")
            return

        from db.session import get_async_session
        from data.fetcher import fetch_and_store_prices
        from sqlalchemy import select
        from db.models import Ticker
        from config import get_settings

        settings = get_settings()
        end = date.today()
        start = end - timedelta(days=7)

        async with get_async_session() as session:
            result = await session.execute(select(Ticker).where(Ticker.active == True))
            symbols = [t.symbol for t in result.scalars()]
            counts = await fetch_and_store_prices(
                session, symbols, start, end,
                batch_size=settings.yfinance_batch_size,
                retry_attempts=settings.yfinance_retry_attempts,
            )
        log.info("job_done", job="fetch_prices", symbols_updated=len(counts))
    except Exception as exc:
        log.error("job_error", job="fetch_prices", error=str(exc), exc_info=True)
        await _write_audit_error("fetch_prices", str(exc))


async def _job_compute_features() -> None:
    log.info("job_start", job="compute_features")
    try:
        from data.calendar import is_trading_day
        if not is_trading_day():
            return

        from db.session import get_async_session
        from data.preprocessor import compute_and_store_features
        from sqlalchemy import select
        from db.models import Ticker

        async with get_async_session() as session:
            result = await session.execute(select(Ticker).where(Ticker.active == True))
            tickers = result.scalars().all()
            for ticker in tickers:
                await compute_and_store_features(session, ticker.id)
        log.info("job_done", job="compute_features")
    except Exception as exc:
        log.error("job_error", job="compute_features", error=str(exc), exc_info=True)
        await _write_audit_error("compute_features", str(exc))


async def _job_generate_signals() -> None:
    log.info("job_start", job="generate_signals")
    try:
        from data.calendar import is_trading_day
        if not is_trading_day():
            return

        from db.session import get_async_session
        from strategies.signal_generator import generate_signals_for_all

        async with get_async_session() as session:
            signals = await generate_signals_for_all(session)
        log.info("job_done", job="generate_signals", count=len(signals))
    except Exception as exc:
        log.error("job_error", job="generate_signals", error=str(exc), exc_info=True)
        await _write_audit_error("generate_signals", str(exc))


async def _job_execute_signals() -> None:
    log.info("job_start", job="execute_signals")
    try:
        from data.calendar import is_trading_day
        if not is_trading_day():
            return

        from db.session import get_async_session
        from db.models import Signal, Ticker
        from sqlalchemy import select
        from datetime import datetime, timezone
        from config import get_settings
        from portfolio.paper_broker import PaperBroker
        from portfolio.manager import PortfolioManager
        import yfinance as yf
        from decimal import Decimal

        settings = get_settings()
        today = datetime.now(timezone.utc).date()
        start_dt = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)

        async with get_async_session() as session:
            result = await session.execute(
                select(Signal).where(
                    Signal.generated_at >= start_dt,
                    Signal.executed == False,
                    Signal.confidence >= Decimal(str(settings.signal_confidence_threshold)),
                )
            )
            signals = result.scalars().all()

            symbols = []
            for sig in signals:
                t = await session.get(Ticker, sig.ticker_id)
                if t:
                    symbols.append(t.symbol)

            prices_raw = {}
            if symbols:
                data = yf.download(" ".join(set(symbols)), period="1d", progress=False, auto_adjust=True)
                for sym in set(symbols):
                    try:
                        close = float(data["Close"][sym].iloc[-1]) if len(set(symbols)) > 1 else float(data["Close"].iloc[-1])
                        prices_raw[sym] = Decimal(str(round(close, 4)))
                    except Exception:
                        pass

            broker = PaperBroker(settings, prices_raw)
            manager = PortfolioManager(session, broker, settings)

            for sig in signals:
                ticker = await session.get(Ticker, sig.ticker_id)
                if not ticker or ticker.symbol not in prices_raw:
                    continue
                price = prices_raw[ticker.symbol]
                order = await manager.execute_signal(ticker, sig.signal, float(sig.confidence), price, sig.id, "paper")
                if order:
                    sig.executed = True

        log.info("job_done", job="execute_signals", signals_processed=len(signals))
    except Exception as exc:
        log.error("job_error", job="execute_signals", error=str(exc), exc_info=True)
        await _write_audit_error("execute_signals", str(exc))


async def _job_snapshot_equity() -> None:
    log.info("job_start", job="snapshot_equity")
    try:
        from data.calendar import is_trading_day
        if not is_trading_day():
            return

        from db.session import get_async_session
        from db.models import AppSettings, Position, Ticker
        from sqlalchemy import select
        from config import get_settings
        import yfinance as yf
        from decimal import Decimal

        settings = get_settings()

        async with get_async_session() as session:
            pos_result = await session.execute(select(Position).where(Position.closed_at.is_(None)))
            positions = pos_result.scalars().all()
            symbols = []
            for pos in positions:
                t = await session.get(Ticker, pos.ticker_id)
                if t:
                    symbols.append(t.symbol)

            prices_raw: dict[str, Decimal] = {}
            if symbols:
                data = yf.download(" ".join(set(symbols)), period="1d", progress=False, auto_adjust=True)
                for sym in set(symbols):
                    try:
                        close = float(data["Close"][sym].iloc[-1]) if len(set(symbols)) > 1 else float(data["Close"].iloc[-1])
                        prices_raw[sym] = Decimal(str(round(close, 4)))
                    except Exception:
                        pass

            mode_row = await session.execute(select(AppSettings).where(AppSettings.key == "trading_mode"))
            mode = mode_row.scalars().first()
            mode_str = mode.value if mode else settings.trading_mode

            from portfolio.paper_broker import PaperBroker
            from portfolio.manager import PortfolioManager
            broker = PaperBroker(settings, prices_raw)
            manager = PortfolioManager(session, broker, settings)
            snapshot = await manager.snapshot_equity(prices_raw, mode_str)

        log.info("job_done", job="snapshot_equity", total_equity=str(snapshot.total_equity))
    except Exception as exc:
        log.error("job_error", job="snapshot_equity", error=str(exc), exc_info=True)
        await _write_audit_error("snapshot_equity", str(exc))


async def _job_check_stops() -> None:
    log.info("job_start", job="check_stops")
    try:
        from data.calendar import is_market_open
        if not is_market_open():
            return

        from db.session import get_async_session
        from db.models import AppSettings, Ticker
        from sqlalchemy import select
        from config import get_settings
        from risk.limits import check_stop_losses
        import yfinance as yf
        from decimal import Decimal

        settings = get_settings()
        async with get_async_session() as session:
            from db.models import Position
            pos_result = await session.execute(select(Position).where(Position.closed_at.is_(None)))
            positions = pos_result.scalars().all()
            symbols = []
            for pos in positions:
                t = await session.get(Ticker, pos.ticker_id)
                if t:
                    symbols.append(t.symbol)

            prices_raw: dict[str, Decimal] = {}
            if symbols:
                data = yf.download(" ".join(set(symbols)), period="1d", progress=False, auto_adjust=True)
                for sym in set(symbols):
                    try:
                        close = float(data["Close"][sym].iloc[-1]) if len(set(symbols)) > 1 else float(data["Close"].iloc[-1])
                        prices_raw[sym] = Decimal(str(round(close, 4)))
                    except Exception:
                        pass

            mode_row = await session.execute(select(AppSettings).where(AppSettings.key == "trading_mode"))
            mode = mode_row.scalars().first()
            mode_str = mode.value if mode else settings.trading_mode

            triggered = await check_stop_losses(session, settings, prices_raw, mode_str)

        if triggered:
            log.warning("stop_losses_triggered", symbols=triggered)
    except Exception as exc:
        log.error("job_error", job="check_stops", error=str(exc), exc_info=True)


async def _job_check_drawdown() -> None:
    log.info("job_start", job="check_drawdown")
    try:
        from data.calendar import is_market_open
        if not is_market_open():
            return

        from db.session import get_async_session
        from config import get_settings
        from risk.limits import check_portfolio_drawdown
        from services.portfolio_service import get_portfolio_summary

        settings = get_settings()
        async with get_async_session() as session:
            summary = await get_portfolio_summary(session)
            triggered = await check_portfolio_drawdown(
                session, settings, summary.total_equity, summary.mode
            )
        if triggered:
            log.error("auto_killswitch_activated", equity=str(summary.total_equity))
    except Exception as exc:
        log.error("job_error", job="check_drawdown", error=str(exc), exc_info=True)


async def _job_retrain_model() -> None:
    log.info("job_start", job="retrain_model")
    try:
        import subprocess
        result = subprocess.run(["python", "ml/train.py"], capture_output=True, text=True)
        if result.returncode != 0:
            log.error("retrain_failed", stderr=result.stderr)
        else:
            log.info("retrain_success", stdout=result.stdout[:500])
    except Exception as exc:
        log.error("job_error", job="retrain_model", error=str(exc), exc_info=True)


async def _job_fetch_fundamentals() -> None:
    log.info("job_start", job="fetch_fundamentals")
    try:
        from db.session import get_async_session
        from data.fundamentals import fetch_and_store_fundamentals
        from sqlalchemy import select
        from db.models import Ticker

        async with get_async_session() as session:
            result = await session.execute(select(Ticker).where(Ticker.active == True))
            symbols = [t.symbol for t in result.scalars()]
            count = await fetch_and_store_fundamentals(session, symbols)
        log.info("job_done", job="fetch_fundamentals", count=count)
    except Exception as exc:
        log.error("job_error", job="fetch_fundamentals", error=str(exc), exc_info=True)
        await _write_audit_error("fetch_fundamentals", str(exc))


async def _job_cleanup_logs() -> None:
    log.info("job_start", job="cleanup_logs")
    try:
        import os
        from pathlib import Path
        from datetime import timedelta

        log_dir = Path("logs")
        cutoff = date.today() - timedelta(days=30)
        removed = 0
        for f in log_dir.glob("*.log.*"):
            mtime = date.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                f.unlink()
                removed += 1
        log.info("job_done", job="cleanup_logs", removed=removed)
    except Exception as exc:
        log.error("job_error", job="cleanup_logs", error=str(exc), exc_info=True)


async def _write_audit_error(job_name: str, error: str) -> None:
    try:
        from db.session import get_async_session
        from db.models import AuditLog
        async with get_async_session() as session:
            session.add(AuditLog(event_type="error", actor="scheduler", details={"job": job_name, "error": error}))
    except Exception:
        pass


def start_scheduler(settings: Settings) -> None:
    global _scheduler
    if not settings.scheduler_enabled:
        log.info("scheduler_disabled")
        return

    tz = settings.scheduler_timezone
    _scheduler = _make_scheduler(tz)

    if settings.job_fetch_prices_enabled:
        _scheduler.add_job(_job_fetch_prices, CronTrigger(day_of_week="mon-fri", hour=16, minute=30, timezone=tz), id="fetch_prices", replace_existing=True)
    if settings.job_compute_features_enabled:
        _scheduler.add_job(_job_compute_features, CronTrigger(day_of_week="mon-fri", hour=16, minute=45, timezone=tz), id="compute_features", replace_existing=True)
    if settings.job_generate_signals_enabled:
        _scheduler.add_job(_job_generate_signals, CronTrigger(day_of_week="mon-fri", hour=17, minute=0, timezone=tz), id="generate_signals", replace_existing=True)
    if settings.job_execute_signals_enabled:
        _scheduler.add_job(_job_execute_signals, CronTrigger(day_of_week="mon-fri", hour=17, minute=5, timezone=tz), id="execute_signals", replace_existing=True)
    _scheduler.add_job(_job_snapshot_equity, CronTrigger(day_of_week="mon-fri", hour=17, minute=10, timezone=tz), id="snapshot_equity", replace_existing=True)
    if settings.job_check_stops_enabled:
        _scheduler.add_job(_job_check_stops, CronTrigger(day_of_week="mon-fri", minute="*/30", timezone=tz), id="check_stops", replace_existing=True)
    _scheduler.add_job(_job_check_drawdown, CronTrigger(day_of_week="mon-fri", minute="*/30", timezone=tz), id="check_drawdown", replace_existing=True)
    if settings.job_retrain_model_enabled:
        _scheduler.add_job(_job_retrain_model, CronTrigger(day_of_week="sun", hour=23, minute=0, timezone=tz), id="retrain_model", replace_existing=True)
    if settings.job_fetch_fundamentals_enabled:
        _scheduler.add_job(_job_fetch_fundamentals, CronTrigger(day_of_week="sun", hour=18, minute=0, timezone=tz), id="fetch_fundamentals", replace_existing=True)
    _scheduler.add_job(_job_cleanup_logs, CronTrigger(day_of_week="sun", hour=2, minute=0, timezone=tz), id="cleanup_logs", replace_existing=True)

    _scheduler.start()
    log.info("scheduler_started", jobs=[job.id for job in _scheduler.get_jobs()])


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("scheduler_stopped")
