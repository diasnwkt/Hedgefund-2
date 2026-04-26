from datetime import date, datetime

import pandas_market_calendars as mcal
import structlog

log = structlog.get_logger(__name__)

_calendar = mcal.get_calendar("NYSE")


def is_market_open(dt: datetime | None = None) -> bool:
    if dt is None:
        dt = datetime.now()
    schedule = _calendar.schedule(start_date=dt.date(), end_date=dt.date())
    if schedule.empty:
        return False
    row = schedule.iloc[0]
    market_open = row["market_open"].to_pydatetime()
    market_close = row["market_close"].to_pydatetime()
    if market_open.tzinfo is None:
        import pytz
        tz = pytz.UTC
        market_open = tz.localize(market_open)
        market_close = tz.localize(market_close)
    if dt.tzinfo is None:
        import pytz
        dt = pytz.UTC.localize(dt)
    return market_open <= dt <= market_close


def is_trading_day(d: date | None = None) -> bool:
    if d is None:
        d = date.today()
    schedule = _calendar.schedule(start_date=d, end_date=d)
    return not schedule.empty


def get_trading_days(start: date, end: date) -> list[date]:
    schedule = _calendar.schedule(start_date=start, end_date=end)
    return [idx.date() for idx in schedule.index]


def next_trading_day(d: date | None = None) -> date:
    if d is None:
        d = date.today()
    from datetime import timedelta
    candidate = d + timedelta(days=1)
    for _ in range(10):
        if is_trading_day(candidate):
            return candidate
        candidate += timedelta(days=1)
    raise RuntimeError("Could not find next trading day within 10 calendar days")
