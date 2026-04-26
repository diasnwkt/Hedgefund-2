# Personal AI Hedge Fund

A full-stack algorithmic trading system powered by machine learning, technical analysis, and a local LLM for signal rationale. Runs in paper trading mode by default with optional live trading via Alpaca.

---

## Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI, SQLAlchemy 2.0 async, Alembic, APScheduler |
| ML | XGBoost, 13 technical + fundamental features |
| LLM | llama-cpp-python (reads GGUF from local Ollama cache) |
| Database | PostgreSQL, Redis |
| Frontend | React 18, Vite 5, Tailwind CSS, Recharts |
| Broker | Alpaca (paper + live), yfinance for market data |

---

## Features

- **Signal generation** — XGBoost classifier trained on 13 features (RSI, MACD, Bollinger Bands, ATR, OBV, ADX, momentum, moving averages)
- **Composite scoring** — `0.6 × ML confidence + 0.4 × technical score`
- **LLM rationale** — local Llama 3.2 filters and explains each signal in plain English
- **Fundamental data** — P/E, forward P/E, beta, analyst target price, 52-week range fetched weekly via yfinance
- **Recommendations page** — ranked BUY signals with score bars, metric pills, and collapsible technical detail
- **Paper trading** — simulated fills with slippage and commission, full P&L tracking
- **Risk management** — position size limits, sector exposure caps, stop-losses, portfolio drawdown kill-switch
- **Scheduler** — automated daily pipeline: fetch prices → compute features → generate signals → execute trades → snapshot equity
- **Dashboard** — equity curve, positions, benchmark comparison, audit log

---

## Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- [Ollama](https://ollama.com) with `llama3.2:3b` pulled (optional — for LLM rationale)

---

## Setup

### 1. Clone and configure

```bash
git clone https://github.com/diasnwkt/Hedgefund-2.git
cd Hedgefund-2
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD, SECRET_KEY, and optionally Alpaca keys
```

### 2. Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 3. Frontend dependencies

```bash
cd frontend && npm install && cd ..
```

### 4. Database

```bash
createdb hedgefund
cd backend && alembic upgrade head && cd ..
```

### 5. Seed watchlist and backfill prices

```bash
source .venv/bin/activate
python scripts/init_db.py
python scripts/backfill_prices.py
```

### 6. Train the ML model

```bash
python ml/train.py
```

### 7. Start services

```bash
# Backend (from backend/)
cd backend && ../.venv/bin/uvicorn main:app --reload

# Frontend (from frontend/)
cd frontend && npm run dev
```

Open [http://localhost:5173](http://localhost:5173) — default login: `dias` / password from `ADMIN_PASSWORD` in `.env`.

---

## Environment Variables

Key variables in `.env` (see `.env.example` for the full list):

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing key (min 32 chars) |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `ADMIN_PASSWORD` | Dashboard login password |
| `DEFAULT_WATCHLIST` | Comma-separated ticker symbols |
| `TRADING_MODE` | `paper` or `live` |
| `SIGNAL_CONFIDENCE_THRESHOLD` | Minimum confidence to execute (default `0.65`) |
| `ALPACA_PAPER_API_KEY` | Alpaca paper trading key |
| `ALPACA_LIVE_API_KEY` | Alpaca live trading key |
| `ALPACA_LIVE_ENABLED` | Set `true` to unlock live mode |
| `OLLAMA_ENABLED` | Set `true` to enable LLM signal filtering |
| `OLLAMA_MODEL` | Ollama model name (default `llama3.2:3b`) |
| `JOB_EXECUTE_SIGNALS_ENABLED` | Set `true` to auto-execute signals |

---

## Scheduler Jobs

Jobs run automatically on weekdays (Eastern Time):

| Job | Time | Description |
|-----|------|-------------|
| `fetch_prices` | 16:30 | Download latest OHLCV from Yahoo Finance |
| `compute_features` | 16:45 | Compute 13 technical features per ticker |
| `generate_signals` | 17:00 | Run XGBoost + LLM filter, compute composite score |
| `execute_signals` | 17:05 | Execute qualifying signals via paper/live broker |
| `snapshot_equity` | 17:10 | Record portfolio equity snapshot |
| `check_stops` | every 30m | Intraday stop-loss checks |
| `check_drawdown` | every 30m | Portfolio drawdown kill-switch check |
| `fetch_fundamentals` | Sunday 18:00 | Update fundamental snapshots for all tickers |
| `retrain_model` | Sunday 23:00 | Retrain XGBoost on latest data (if enabled) |

---

## Project Structure

```
├── backend/
│   ├── data/           # Price fetching, feature engineering, fundamentals
│   ├── db/             # SQLAlchemy models, Alembic migrations
│   ├── ml/             # XGBoost training and feature pipeline
│   ├── portfolio/      # Paper broker, portfolio manager
│   ├── risk/           # Stop-loss, drawdown, position limits
│   ├── routers/        # FastAPI route handlers
│   ├── schemas/        # Pydantic request/response models
│   ├── services/       # Business logic layer
│   ├── strategies/     # Signal generation, LLM filter
│   └── scheduler.py    # APScheduler cron jobs
├── frontend/
│   └── src/
│       ├── pages/      # Dashboard, Portfolio, Signals, Recommendations, Risk, Settings
│       └── components/ # Shared UI components
├── ml/                 # Model training scripts
└── scripts/            # DB init, backfill, live mode helper
```

---

## Live Trading

Live trading is disabled by default. To enable:

1. Add Alpaca live API keys to `.env`
2. Set `ALPACA_LIVE_ENABLED=true` and restart the backend
3. Go to Settings → Trading Mode → click LIVE and confirm with `I_UNDERSTAND_RISK`

---

## License

MIT
