from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
import structlog

log = structlog.get_logger(__name__)


class KillSwitchActiveError(Exception):
    pass


class RiskLimitBreached(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class InsufficientFundsError(Exception):
    pass


class TickerNotFoundError(Exception):
    pass


class LiveModeNotEnabledError(Exception):
    pass


class OrderRejectedError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


async def killswitch_handler(request: Request, exc: KillSwitchActiveError) -> JSONResponse:
    log.warning("killswitch_blocked_request", path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_423_LOCKED,
        content={"detail": "Kill-switch is active. All trading is suspended."},
    )


async def risk_limit_handler(request: Request, exc: RiskLimitBreached) -> JSONResponse:
    log.warning("risk_limit_breached", reason=exc.reason, path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": f"Risk limit breached: {exc.reason}"},
    )


async def generic_http_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled_exception", path=request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred."},
    )
