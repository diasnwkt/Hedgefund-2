import pytest


@pytest.mark.asyncio
async def test_health_endpoint(async_client):
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_portfolio_summary(async_client):
    resp = await async_client.get("/portfolio/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "cash" in data
    assert "total_equity" in data
    assert "mode" in data


@pytest.mark.asyncio
async def test_portfolio_positions_empty(async_client):
    resp = await async_client.get("/portfolio/positions")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_portfolio_history_empty(async_client):
    resp = await async_client.get("/portfolio/history")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_signals_today_empty(async_client):
    resp = await async_client.get("/signals/today")
    assert resp.status_code == 200
    data = resp.json()
    assert "signals" in data
    assert data["generated_count"] == 0


@pytest.mark.asyncio
async def test_signals_history_empty(async_client):
    resp = await async_client.get("/signals/history")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_risk_metrics(async_client):
    resp = await async_client.get("/risk/metrics")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_killswitch_get(async_client):
    resp = await async_client.get("/risk/killswitch")
    assert resp.status_code == 200
    data = resp.json()
    assert data["active"] is False


@pytest.mark.asyncio
async def test_killswitch_activate_deactivate(async_client):
    resp = await async_client.post("/risk/killswitch", json={"active": True, "reason": "test"})
    assert resp.status_code == 200
    assert resp.json()["active"] is True

    resp = await async_client.post("/risk/killswitch", json={"active": False, "reason": "test done"})
    assert resp.status_code == 200
    assert resp.json()["active"] is False


@pytest.mark.asyncio
async def test_watchlist_get(async_client):
    resp = await async_client.get("/settings/watchlist")
    assert resp.status_code == 200
    data = resp.json()
    assert "symbols" in data


@pytest.mark.asyncio
async def test_watchlist_update(async_client):
    resp = await async_client.post("/settings/watchlist", json={"symbols": ["AAPL", "MSFT"]})
    assert resp.status_code == 200
    data = resp.json()
    assert set(data["symbols"]) == {"AAPL", "MSFT"}


@pytest.mark.asyncio
async def test_mode_get(async_client):
    resp = await async_client.get("/settings/mode")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] in ("paper", "live")


@pytest.mark.asyncio
async def test_mode_switch_to_paper(async_client):
    resp = await async_client.post("/settings/mode", json={"mode": "paper", "confirm": ""})
    assert resp.status_code == 200
    assert resp.json()["mode"] == "paper"


@pytest.mark.asyncio
async def test_live_mode_blocked_without_env(async_client):
    resp = await async_client.post("/settings/mode", json={"mode": "live", "confirm": "I_UNDERSTAND_RISK"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_audit_log(async_client):
    resp = await async_client.get("/settings/audit/log")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_equity_history(async_client):
    resp = await async_client.get("/portfolio/equity/history?days=30")
    assert resp.status_code == 200
    data = resp.json()
    assert "points" in data
    assert "initial_equity" in data
