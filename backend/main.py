from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from auth import router as auth_router
from config import get_settings
from exceptions import (
    KillSwitchActiveError,
    RiskLimitBreached,
    generic_http_handler,
    killswitch_handler,
    risk_limit_handler,
    unhandled_exception_handler,
)
from logging_config import configure_logging
from routers.health import router as health_router
from routers.portfolio import router as portfolio_router
from routers.risk import router as risk_router
from routers.settings import router as settings_router
from routers.signals import router as signals_router
from scheduler import start_scheduler, stop_scheduler

settings = get_settings()
configure_logging(
    log_level=settings.log_level,
    log_format=settings.log_format,
    log_file=settings.log_file,
)
log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup", app=settings.app_name, env=settings.app_env, mode=settings.trading_mode)
    start_scheduler(settings)
    yield
    stop_scheduler()
    log.info("shutdown")


app = FastAPI(
    title="Personal Hedge Fund API",
    version="1.0.0",
    docs_url="/docs" if settings.app_debug else None,
    redoc_url="/redoc" if settings.app_debug else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(KillSwitchActiveError, killswitch_handler)
app.add_exception_handler(RiskLimitBreached, risk_limit_handler)
app.add_exception_handler(HTTPException, generic_http_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(portfolio_router)
app.include_router(signals_router)
app.include_router(risk_router)
app.include_router(settings_router)
