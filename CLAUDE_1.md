# 🏦 Personal Hedge Fund — Claude Code Context File

> **Keep this file in the project root.** Claude Code reads it automatically. Reference it at the start of every session.

---

## Project Overview

A personal AI-driven hedge fund system for tracking, analyzing, and trading US equities. Starts in paper trading mode, then switches to live trading via Alpaca. Built for a single user. No external investors.

**Core capabilities:**
- AI/ML-driven buy/sell signal generation (XGBoost classifier)
- Portfolio tracking with real-time P&L (realized + unrealized)
- Risk management with hard enforcement rules & kill-switch
- Paper trading simulation → live trading switch (with 2-step activation)
- React dashboard for monitoring
- Benchmark comparison vs SPY
- Full observability (logs, metrics, alerts)

**Guiding principles:**
1. **Safety first** — kill-switch, hard risk limits, 2-step live activation
2. **Testable** — every module has unit tests, strategies have backtests
3. **Idempotent** — jobs can re-run without corrupting data
4. **Observable** — structured logs, no silent failures
5. **Reproducible** — Docker Compose, pinned versions, seeded randomness

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Backend | Python + FastAPI | 3.11+ / fastapi 0.110+ |
| Frontend | React + Vite + Tailwind + Recharts | React 18 / Vite 5 |
| Database | PostgreSQL | 15 |
| Cache | Redis | 7 |
| ORM | SQLAlchemy 2.0 + Alembic | 2.0+ |
| Validation | Pydantic | 2.x |
| ML | scikit-learn + XGBoost | latest stable |
| Market Data | yfinance + Alpaca WebSocket | latest |
| Broker | Alpaca-py SDK | latest |
| Scheduler | APScheduler | 3.x |
| Market Calendar | pandas_market_calendars | latest |
| HTTP client | httpx (async) | latest |
| Auth | JWT via python-jose + bcrypt | latest |
| Testing | pytest + pytest-asyncio + httpx TestClient | latest |
| Linting | ruff + black + mypy | latest |
| Logging | structlog (JSON logs) | latest |
| Infra | Docker Compose | v2 |

---

## Project Structure

```
hedge-fund/
├── CLAUDE.md                       ← YOU ARE HERE
├── README.md
├── .env                            ← secrets (git-ignored)
├── .env.example                    ← template (committed)
├── .gitignore
├── .dockerignore
├── docker-compose.yml
├── docker-compose.override.yml     ← dev overrides (optional)
├── pyproject.toml                  ← ruff, black, mypy, pytest config
├── Makefile                        ← shortcuts: make up/down/test/lint
│
├── backend/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app entrypoint
│   ├── config.py                   # Pydantic Settings from ENV
│   ├── logging_config.py           # structlog setup
│   ├── auth.py                     # JWT login endpoint
│   ├── dependencies.py             # FastAPI DI (get_db, get_current_user, etc.)
│   ├── exceptions.py               # Custom exceptions + handlers
│   ├── Dockerfile
│   ├── requirements.txt
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py               # SQLAlchemy ORM models
│   │   ├── session.py              # Engine + session factory
│   │   └── migrations/             # Alembic migrations
│   │       └── versions/
│   │
│   ├── schemas/                    # Pydantic request/response models
│   │   ├── __init__.py
│   │   ├── portfolio.py
│   │   ├── signals.py
│   │   ├── risk.py
│   │   └── settings.py
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── fetcher.py              # yfinance OHLCV pipeline (with retries)
│   │   ├── preprocessor.py         # Feature engineering
│   │   └── calendar.py             # Market holidays / open-close check
│   │
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstract Strategy class
│   │   ├── ml_strategy.py          # XGBoost signal model
│   │   └── signal_generator.py     # Outputs BUY/SELL/HOLD + confidence
│   │
│   ├── portfolio/
│   │   ├── __init__.py
│   │   ├── manager.py              # Position sizing, rebalancing
│   │   └── paper_broker.py         # Paper trading engine
│   │
│   ├── risk/
│   │   ├── __init__.py
│   │   ├── metrics.py              # Sharpe, Sortino, VaR, drawdown, beta
│   │   └── limits.py               # Pre-trade hard enforcement rules
│   │
│   ├── broker/
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstract Broker interface
│   │   └── alpaca.py               # Live trading via alpaca-py
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── portfolio.py
│   │   ├── signals.py
│   │   ├── risk.py
│   │   ├── settings.py
│   │   └── health.py               # /health for liveness check
│   │
│   ├── services/                   # Business logic (called by routers)
│   │   ├── __init__.py
│   │   ├── portfolio_service.py
│   │   └── signal_service.py
│   │
│   ├── scheduler.py                # APScheduler job definitions
│   │
│   └── tests/
│       ├── conftest.py             # Fixtures (test DB, mock broker)
│       ├── test_fetcher.py
│       ├── test_preprocessor.py
│       ├── test_ml_strategy.py
│       ├── test_paper_broker.py
│       ├── test_risk_limits.py
│       ├── test_risk_metrics.py
│       ├── test_routers.py
│       └── test_integration.py     # Full paper-trading flow
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── index.html
│   ├── Dockerfile
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── router.jsx
│       ├── api/
│       │   ├── client.js           # Axios instance + interceptors
│       │   └── endpoints.js        # Typed endpoint functions
│       ├── hooks/
│       │   ├── usePolling.js       # Reusable polling hook
│       │   └── useAuth.js
│       ├── pages/
│       │   ├── Login.jsx
│       │   ├── Dashboard.jsx
│       │   ├── Portfolio.jsx
│       │   ├── Signals.jsx
│       │   └── Risk.jsx
│       └── components/
│           ├── EquityCurve.jsx
│           ├── HoldingsTable.jsx
│           ├── SignalCard.jsx
│           ├── RiskGauge.jsx
│           ├── KillSwitch.jsx
│           ├── ModeIndicator.jsx   # Paper/Live badge
│           └── Layout.jsx
│
├── ml/
│   ├── train.py                    # Offline training entrypoint
│   ├── evaluate.py                 # Backtest + metrics
│   ├── features.py                 # Shared feature engineering logic
│   └── models/                     # Saved .pkl files (git-ignored)
│       └── .gitkeep
│
├── scripts/
│   ├── init_db.py                  # Create tables + seed watchlist
│   ├── backfill_prices.py          # Historical data loader
│   └── enable_live_mode.py         # 2-step live mode activation
│
└── logs/                           # App logs (git-ignored)
    └── .gitkeep
```

---

## Database Schema

All tables use SQLAlchemy 2.0 mapped classes. All migrations via Alembic.
Timestamps: `timestamp with time zone` (UTC).
Money fields: `NUMERIC(18, 4)` — NEVER use FLOAT for money.

### `tickers`
| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| symbol | VARCHAR(10) UNIQUE NOT NULL | e.g. "AAPL" |
| name | VARCHAR(200) | company name |
| active | BOOLEAN NOT NULL DEFAULT true | in watchlist |
| created_at | TIMESTAMPTZ NOT NULL DEFAULT NOW() | |
| **Index** | `idx_tickers_symbol` on symbol | |

### `prices`
| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| ticker_id | INT FK tickers(id) NOT NULL | |
| date | DATE NOT NULL | |
| open, high, low, close | NUMERIC(18,4) NOT NULL | |
| adj_close | NUMERIC(18,4) NOT NULL | split/dividend-adjusted |
| volume | BIGINT NOT NULL | |
| **Unique** | `(ticker_id, date)` | prevents duplicates |
| **Index** | `idx_prices_ticker_date` on (ticker_id, date DESC) | |

### `features`
| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| ticker_id | INT FK tickers(id) NOT NULL | |
| date | DATE NOT NULL | |
| rsi_14, macd, macd_signal | NUMERIC(12,6) | nullable (warmup period) |
| volume_zscore | NUMERIC(12,6) | |
| ma_20, ma_50 | NUMERIC(18,4) | |
| ma_cross | SMALLINT | −1, 0, or 1 |
| momentum_5d, momentum_20d | NUMERIC(12,6) | |
| **Unique** | `(ticker_id, date)` | |

### `signals`
| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| ticker_id | INT FK tickers(id) NOT NULL | |
| generated_at | TIMESTAMPTZ NOT NULL | |
| signal | VARCHAR(4) NOT NULL | 'BUY', 'SELL', 'HOLD' |
| confidence | NUMERIC(5,4) NOT NULL | 0.0000–1.0000 |
| model_version | VARCHAR(50) NOT NULL | e.g. "xgb_20260120_001" |
| executed | BOOLEAN NOT NULL DEFAULT false | was it traded? |
| **Check** | `confidence BETWEEN 0 AND 1` | |
| **Check** | `signal IN ('BUY','SELL','HOLD')` | |
| **Index** | on (generated_at DESC) | |

### `positions`
| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| ticker_id | INT FK tickers(id) NOT NULL | |
| shares | NUMERIC(18,6) NOT NULL | fractional OK |
| avg_cost | NUMERIC(18,4) NOT NULL | VWAP |
| opened_at | TIMESTAMPTZ NOT NULL | |
| closed_at | TIMESTAMPTZ | null = still open |
| realized_pnl | NUMERIC(18,4) NOT NULL DEFAULT 0 | populated on close |
| mode | VARCHAR(5) NOT NULL | 'paper' or 'live' |
| **Index** | on (mode, closed_at) WHERE closed_at IS NULL | open positions |

### `orders`
| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| external_id | VARCHAR(100) | Alpaca order ID (live mode) |
| ticker_id | INT FK tickers(id) NOT NULL | |
| side | VARCHAR(4) NOT NULL | 'buy' or 'sell' |
| shares | NUMERIC(18,6) NOT NULL | |
| requested_price | NUMERIC(18,4) | limit price (null=market) |
| filled_price | NUMERIC(18,4) | null until filled |
| slippage | NUMERIC(18,4) NOT NULL DEFAULT 0 | |
| commission | NUMERIC(18,4) NOT NULL DEFAULT 0 | |
| status | VARCHAR(20) NOT NULL | 'pending','filled','cancelled','rejected' |
| reason | TEXT | why rejected/cancelled |
| signal_id | INT FK signals(id) | what triggered this order |
| submitted_at | TIMESTAMPTZ NOT NULL | |
| executed_at | TIMESTAMPTZ | null until filled |
| mode | VARCHAR(5) NOT NULL | |
| **Index** | on (executed_at DESC) | |

### `equity_snapshots`
| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| timestamp | TIMESTAMPTZ NOT NULL | |
| cash | NUMERIC(18,4) NOT NULL | |
| positions_value | NUMERIC(18,4) NOT NULL | mark-to-market |
| total_equity | NUMERIC(18,4) NOT NULL | cash + positions_value |
| realized_pnl_total | NUMERIC(18,4) NOT NULL | lifetime realized |
| benchmark_value | NUMERIC(18,4) | SPY-equivalent portfolio value |
| mode | VARCHAR(5) NOT NULL | |
| **Unique** | `(timestamp, mode)` | |
| **Index** | on (mode, timestamp DESC) | |

### `audit_log`
| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| timestamp | TIMESTAMPTZ NOT NULL DEFAULT NOW() | |
| event_type | VARCHAR(50) NOT NULL | 'mode_switch','killswitch','order','error' |
| actor | VARCHAR(50) | 'user','scheduler','system' |
| details | JSONB NOT NULL | |
| **Index** | on (timestamp DESC) | |

---

## API Endpoints

All endpoints except `/auth/login` and `/health` require JWT via `Authorization: Bearer <token>`.
All responses are JSON. All request/response bodies validated via Pydantic.

```
# Health
GET  /health                     → {"status":"ok", "db":"ok", "redis":"ok"}

# Auth
POST /auth/login                 → {access_token, token_type}

# Portfolio
GET  /portfolio/summary          → cash, equity, total_return, realized_pnl, mode
GET  /portfolio/positions        → open positions with unrealized P&L
GET  /portfolio/history          → closed positions

# Equity
GET  /equity/history?days=90     → equity snapshots for chart
GET  /equity/benchmark?days=90   → SPY benchmark comparison

# Signals
GET  /signals/today              → today's BUY/SELL/HOLD signals
GET  /signals/history?limit=100  → past signals log

# Risk
GET  /risk/metrics               → Sharpe, Sortino, VaR, drawdown, beta
GET  /risk/killswitch            → current kill-switch state
POST /risk/killswitch            → body: {"active": true|false, "reason": "..."}

# Settings
GET  /settings/watchlist         → current ticker list
POST /settings/watchlist         → body: {"symbols": ["AAPL","MSFT",...]}
GET  /settings/mode              → current mode + live-enabled flag
POST /settings/mode              → body: {"mode":"paper"|"live", "confirm":"I_UNDERSTAND_RISK"}

# Audit
GET  /audit/log?event_type=...   → audit trail
```

---

## ML Model Spec

| Aspect | Value |
|---|---|
| Model | XGBoost Classifier (binary) |
| Target | 5-day forward return direction (1 = +return ≥ 1%, 0 = below) |
| Features | RSI-14, MACD, MACD signal, volume z-score, MA-20, MA-50, MA cross, 5d momentum, 20d momentum |
| Training | Walk-forward CV (expanding window, 252-day test folds) |
| Random seed | 42 (pinned for reproducibility) |
| Train/test split | Time-series only (never shuffle) |
| Execution threshold | Signal fires only when `confidence ≥ 0.65` |
| Retraining | Weekly, Sunday 23:00 ET |
| Artifact path | `ml/models/xgb_{YYYYMMDD}_{runid}.pkl` |
| Metadata file | `ml/models/xgb_{YYYYMMDD}_{runid}.json` (metrics, feature list, training period) |
| Output schema | `{ticker, signal, confidence, timestamp, model_version}` |

**Backtest must report:** Sharpe, Sortino, CAGR, max drawdown, hit rate, Calmar ratio, avg trade duration, turnover.

---

## Risk Rules (Hard Enforcement)

| Rule | Value | Enforcement |
|---|---|---|
| Max single position size | 15% of portfolio | Pre-trade check |
| Max sector exposure | 40% | Pre-trade check (post Phase 4) |
| Stop-loss per position | −8% from avg cost | Intraday job every 30 min |
| Portfolio drawdown kill-switch | −20% from peak equity | Snapshot job |
| Min signal confidence | 0.65 | Signal generator |
| Max orders per day | 10 | Pre-trade check |
| Max order size | 25% of avg daily volume | Pre-trade check |
| Wash-trade prevention | No re-buy within 30 days of sell-at-loss | Pre-trade check |

**Kill-switch implementation:**
- State: Redis key `killswitch:active` (boolean) + mirrored in `audit_log`
- Triggers: manual via API OR automatic (drawdown breach)
- Effect: ALL order submissions return HTTP 423 Locked
- Reset: requires manual API call with reason

**Pre-trade check flow** (`limits.py`):
```
check_killswitch() → check_daily_order_count() → check_position_size()
→ check_sector_exposure() → check_volume_liquidity() → check_wash_trade()
→ APPROVED or REJECTED (with reason)
```

---

## Scheduler Jobs (APScheduler)

Timezone: `America/New_York`. Jobs skipped on market holidays (via `pandas_market_calendars`).

| Job | Schedule | Action | Idempotent |
|---|---|---|---|
| `fetch_prices` | Mon–Fri 16:30 ET | Pull OHLCV for active tickers | ✅ (upsert) |
| `compute_features` | Mon–Fri 16:45 ET | Run preprocessor | ✅ (upsert) |
| `generate_signals` | Mon–Fri 17:00 ET | Run ML model | ✅ (one row per day) |
| `execute_signals` | Mon–Fri 17:05 ET | Auto-trade if conf ≥ 0.65 | ✅ (check signal.executed) |
| `snapshot_equity` | Mon–Fri 17:10 ET | Save equity snapshot | ✅ (unique on timestamp,mode) |
| `check_stops` | Every 30 min, market hours only | Enforce stop-loss | ✅ |
| `check_drawdown` | Every 30 min, market hours only | Auto kill-switch | ✅ |
| `retrain_model` | Sunday 23:00 ET | Walk-forward retrain | ✅ (versioned artifacts) |
| `cleanup_logs` | Sunday 02:00 ET | Rotate logs > 30 days | ✅ |

**Failure handling:** Every job wrapped in try/except → logs error + writes to `audit_log` with `event_type='error'`. Retry logic for `fetch_prices` only (3 retries, exponential backoff).

---

## Trading Mode & Safety

Controlled by `TRADING_MODE` in `.env` AND `DB settings.mode`. DB is source of truth at runtime.

| Mode | Broker | Behavior |
|---|---|---|
| `paper` | `paper_broker.py` | Simulated orders, slippage + commission applied |
| `live` | `alpaca.py` | Real orders via Alpaca REST API |

**Live mode requires 2-step activation:**
1. Set `ALPACA_LIVE_ENABLED=true` in `.env` AND restart backend
2. Call `POST /settings/mode` with `{"mode":"live","confirm":"I_UNDERSTAND_RISK"}`

This prevents accidental live trading. Both steps logged to `audit_log`.

**Paper broker defaults:** slippage = 0.05%, commission = $1.00/trade, fills at next-bar open.

---

## Testing Strategy

All tests run via: `pytest backend/tests -v`
Coverage target: 80% minimum for `risk/`, `portfolio/`, `strategies/`, `data/`.

| Test Type | Scope |
|---|---|
| Unit | Every module in `risk/`, `portfolio/`, `data/`, `strategies/` |
| Integration | Full paper-trading flow: fetch → features → signal → order → position → snapshot |
| API | All routes via FastAPI `TestClient` |
| Backtest | Run `ml/evaluate.py` against 5 years of data — must pass Sharpe > 0 sanity check |

**Fixtures (`conftest.py`):**
- `db` — ephemeral test Postgres via Docker or SQLite
- `redis` — fake redis via `fakeredis`
- `sample_prices` — fixture with 1 year of mock OHLCV
- `mock_alpaca` — mock broker for live-mode tests

**Never** run live-mode code paths in tests without mocks. `ALPACA_LIVE_ENABLED` must be false in CI.

---

## Logging & Observability

**Framework:** `structlog` with JSON output.
**Levels:** DEBUG/INFO/WARNING/ERROR.
**File:** `logs/hedgefund.log` (rotated weekly, kept 30 days).
**Every log includes:** `timestamp`, `level`, `module`, `event`, `correlation_id`, + custom fields.

**Must log:**
- Every order (submission, fill, rejection)
- Every signal generated
- Every risk check failure
- Mode switches
- Kill-switch activations
- Scheduler job start/end/error
- API errors (stack trace)

**Never log:** API keys, JWT tokens, full request bodies containing secrets.

---

## Data Validation Rules

All external data validated before DB insertion:
- Prices: `high ≥ low`, `high ≥ open`, `high ≥ close`, `volume ≥ 0`, no NaN
- Features: drop rows with NaN in required columns (first ~50 days of warmup)
- Signals: `confidence ∈ [0, 1]`, `signal ∈ {BUY,SELL,HOLD}`
- Orders: `shares > 0`, `ticker.active = true`, symbol exists

All API inputs validated via Pydantic v2 schemas.

---

## How to Start a Claude Code Session

Paste this at the beginning of each new session:

```
Project: Personal AI Hedge Fund
Context: CLAUDE.md in root (read it first)
Current phase: [Phase X — Name]
Previous phases completed: [list]

Current file structure:
[paste output of: tree -I 'node_modules|__pycache__|.git|venv|logs/*.log' -L 4]

Session goal: [specific deliverable, e.g. "Implement data/fetcher.py with yfinance and retry logic"]

Constraints:
- Follow CLAUDE.md exactly (schema, naming, structure)
- Write unit tests alongside code
- Use structlog for logging
- Use Pydantic for all schemas
```

---

## Build Phases Checklist

- [ ] **Phase 0** — Project Scaffolding
  - Docker Compose (Postgres + Redis)
  - Backend skeleton (FastAPI + config + logging + health endpoint)
  - Alembic initialized
  - `pyproject.toml` with ruff/black/mypy/pytest
  - Makefile
  - `.gitignore`, `.dockerignore`

- [ ] **Phase 1** — Data Pipeline & Infrastructure
  - DB models + initial migration
  - `data/fetcher.py` (yfinance + retries + validation)
  - `data/preprocessor.py` (features)
  - `data/calendar.py` (market holidays)
  - Scheduler wiring (fetch + features jobs)
  - Backfill script
  - Unit tests

- [ ] **Phase 2** — ML Strategy Engine
  - `strategies/base.py` (abstract)
  - `strategies/ml_strategy.py` (XGBoost)
  - `strategies/signal_generator.py`
  - `ml/train.py` (walk-forward CV)
  - `ml/evaluate.py` (backtest metrics)
  - Unit + backtest tests

- [ ] **Phase 3** — Paper Trading Engine
  - `broker/base.py` (abstract Broker)
  - `portfolio/paper_broker.py`
  - `portfolio/manager.py` (sizing)
  - Integration test: fetch → signal → trade → snapshot
  - Scheduler wiring (execute_signals, snapshot_equity)

- [ ] **Phase 4** — Risk Management
  - `risk/metrics.py` (Sharpe, VaR, etc.)
  - `risk/limits.py` (pre-trade checks)
  - Kill-switch (Redis + API)
  - `check_stops` + `check_drawdown` jobs
  - Unit tests for each rule

- [ ] **Phase 5** — React Dashboard
  - Vite + React + Tailwind setup
  - Login page + JWT client
  - 4 main pages + polling hook
  - Equity curve with SPY overlay
  - Kill-switch UI
  - Mode indicator badge

- [ ] **Phase 6** — Live Trading Switch
  - `broker/alpaca.py` (alpaca-py SDK)
  - 2-step activation flow
  - Mode switch API + audit logging
  - Docs for going live

---

## Important Notes for Claude Code

### Must-do
- Run `docker-compose up -d` to start Postgres + Redis before backend
- All DB changes via Alembic migrations (never manual `ALTER TABLE`)
- Read secrets from `config.py` (Pydantic Settings) which loads `.env`
- Write unit tests in the same session as the code
- Use `structlog` — never bare `print()` or `logging.info()`
- Use `NUMERIC` for money, never `FLOAT`
- Use `TIMESTAMPTZ` for timestamps, always store UTC
- Pin random seeds for ML reproducibility (seed=42)
- Call `limits.py` pre-trade check before EVERY order in BOTH brokers

### Must-not-do
- Never hardcode API keys, URLs, or magic numbers
- Never run live-mode code in tests
- Never use `eval()` or deserialize untrusted input
- Never delete `audit_log` entries
- Never commit `.env`, `ml/models/*.pkl`, or `logs/`

### URLs
- Alpaca paper: `https://paper-api.alpaca.markets`
- Alpaca live: `https://api.alpaca.markets`
- Alpaca docs: `https://docs.alpaca.markets`

### Common commands (via Makefile)
```
make up            # docker-compose up -d
make down          # docker-compose down
make migrate       # alembic upgrade head
make test          # pytest backend/tests -v
make lint          # ruff check + black --check + mypy
make format        # black + ruff --fix
make train         # python ml/train.py
make backtest      # python ml/evaluate.py
make logs          # tail -f logs/hedgefund.log
```
