from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Walk up from this file to find .env (supports running from backend/ or project root)
_here = Path(__file__).parent
_env_candidates = [_here / ".env", _here.parent / ".env"]
_env_file = next((str(p) for p in _env_candidates if p.exists()), ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    # App
    app_name: str = "hedge-fund"
    app_env: Literal["development", "staging", "production", "testing"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = False
    app_timezone: str = "America/New_York"

    # Auth
    secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    admin_username: str = "dias"
    admin_password_hash: str = ""
    admin_password: str = ""
    cors_allowed_origins: str = "http://localhost:5173,http://localhost:3000"
    rate_limit_per_minute: int = 60

    # Postgres
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "hedgefund"
    postgres_user: str = "hedgefund_user"
    postgres_password: str = ""
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0
    redis_timeout_sec: int = 5

    # Trading
    trading_mode: Literal["paper", "live"] = "paper"
    alpaca_live_enabled: bool = False

    # Alpaca paper
    alpaca_paper_api_key: str = ""
    alpaca_paper_secret_key: str = ""
    alpaca_paper_base_url: str = "https://paper-api.alpaca.markets"
    alpaca_paper_data_url: str = "https://data.alpaca.markets"

    # Alpaca live
    alpaca_live_api_key: str = ""
    alpaca_live_secret_key: str = ""
    alpaca_live_base_url: str = "https://api.alpaca.markets"
    alpaca_live_data_url: str = "https://data.alpaca.markets"

    broker_http_timeout_sec: int = 10
    broker_retry_attempts: int = 3
    broker_retry_backoff_sec: int = 2

    # Paper simulation
    paper_initial_cash: float = 100_000.0
    paper_slippage_pct: float = 0.0005
    paper_commission_usd: float = 1.00
    paper_fill_model: str = "next_bar_open"

    # yfinance
    yfinance_retry_attempts: int = 3
    yfinance_retry_backoff_sec: int = 5
    yfinance_timeout_sec: int = 30
    yfinance_batch_size: int = 10
    historical_backfill_years: int = 5

    # ML
    signal_confidence_threshold: float = 0.65
    model_dir: str = "ml/models"
    feature_lookback_days: int = 252
    walk_forward_test_days: int = 252
    ml_random_seed: int = 42
    ml_n_jobs: int = -1

    # Risk
    max_position_size_pct: float = 0.15
    max_sector_exposure_pct: float = 0.40
    stop_loss_pct: float = 0.08
    portfolio_drawdown_limit: float = 0.20
    max_orders_per_day: int = 10
    max_order_volume_pct: float = 0.25
    wash_trade_window_days: int = 30

    # Scheduler
    scheduler_timezone: str = "America/New_York"
    scheduler_enabled: bool = True
    market_close_hour: int = 16
    market_close_minute: int = 30
    job_fetch_prices_enabled: bool = True
    job_compute_features_enabled: bool = True
    job_generate_signals_enabled: bool = True
    job_execute_signals_enabled: bool = False
    job_check_stops_enabled: bool = False
    job_retrain_model_enabled: bool = False
    job_fetch_fundamentals_enabled: bool = True

    # Watchlist
    default_watchlist: str = "AAPL,MSFT,GOOGL,AMZN,NVDA,META,TSLA,JPM,V,UNH"
    benchmark_ticker: str = "SPY"

    # Frontend
    vite_api_base_url: str = "http://localhost:8000"
    vite_polling_interval_ms: int = 60000
    vite_app_name: str = "Personal Hedge Fund"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: str = "logs/hedgefund.log"
    log_rotation: str = "weekly"
    log_retention_days: int = 30

    # Alerting
    alerts_enabled: bool = False
    alert_email_from: str = ""
    alert_email_to: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Local LLM signal filter (llama-cpp-python, CPU inference)
    ollama_enabled: bool = False
    ollama_model: str = "llama3.2:3b"
    ollama_model_path: str = ""  # explicit GGUF path; empty = auto-detect from ~/.ollama cache
    ollama_confirm_threshold: float = 0.5

    # Testing
    test_database_url: str = ""
    test_redis_db: int = 15

    # Feature flags
    feature_benchmark_comparison: bool = True
    feature_sector_exposure_check: bool = False
    feature_wash_trade_check: bool = True
    feature_intraday_stops: bool = True

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field
    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @computed_field
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @computed_field
    @property
    def watchlist(self) -> list[str]:
        return [s.strip() for s in self.default_watchlist.split(",") if s.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
