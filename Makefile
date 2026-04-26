.PHONY: up down restart build logs migrate makemigrations test lint format train backtest \
        seed backfill shell psql redis-cli init clean help

# ── Docker ────────────────────────────────────────────────────────────────────
up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose restart

build:
	docker-compose build

logs:
	tail -f logs/hedgefund.log

docker-logs:
	docker-compose logs -f backend

# ── Database / Alembic ────────────────────────────────────────────────────────
migrate:
	docker-compose exec backend alembic upgrade head

makemigrations:
	docker-compose exec backend alembic revision --autogenerate -m "$(msg)"

migrate-local:
	cd backend && alembic upgrade head

seed:
	docker-compose exec backend python /app/../scripts/init_db.py

backfill:
	docker-compose exec backend python /app/../scripts/backfill_prices.py

# ── Tests ─────────────────────────────────────────────────────────────────────
test:
	pytest backend/tests -v

test-cov:
	pytest backend/tests -v --cov=backend --cov-report=term-missing

# ── Lint / Format ─────────────────────────────────────────────────────────────
lint:
	ruff check backend ml scripts
	black --check backend ml scripts
	mypy backend

format:
	black backend ml scripts
	ruff check --fix backend ml scripts

# ── ML ────────────────────────────────────────────────────────────────────────
train:
	python ml/train.py

backtest:
	python ml/evaluate.py

# ── Live mode (requires 2-step, be careful) ───────────────────────────────────
enable-live:
	python scripts/enable_live_mode.py

# ── Shells ────────────────────────────────────────────────────────────────────
shell:
	docker-compose exec backend bash

psql:
	docker-compose exec postgres psql -U hedgefund_user -d hedgefund

redis-cli:
	docker-compose exec redis redis-cli

# ── Init ─────────────────────────────────────────────────────────────────────
init:
	cp -n .env_1.example .env || true
	$(MAKE) up
	sleep 5
	$(MAKE) migrate
	$(MAKE) seed

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -name "*.pyc" -delete 2>/dev/null; true

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Docker:       up | down | restart | build | logs | docker-logs"
	@echo "Database:     migrate | makemigrations msg=... | seed | backfill"
	@echo "Tests:        test | test-cov"
	@echo "Code quality: lint | format"
	@echo "ML:           train | backtest"
	@echo "Shells:       shell | psql | redis-cli"
	@echo "Setup:        init | clean"
