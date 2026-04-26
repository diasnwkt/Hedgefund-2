"""
2-step live mode activation script.
Step 1: Set ALPACA_LIVE_ENABLED=true in .env + restart backend.
Step 2: Run this script (calls POST /settings/mode).

Usage: python scripts/enable_live_mode.py
"""
import sys

import httpx


def main() -> None:
    base_url = input("Backend URL [http://localhost:8000]: ").strip() or "http://localhost:8000"
    username = input("Admin username: ").strip()
    password = input("Admin password: ").strip()

    print("\n⚠️  WARNING: You are about to enable LIVE trading with real money.")
    print("This will submit real orders to Alpaca live account.")
    confirm = input('Type "I_UNDERSTAND_RISK" to continue: ').strip()
    if confirm != "I_UNDERSTAND_RISK":
        print("Aborted.")
        sys.exit(0)

    with httpx.Client(base_url=base_url) as client:
        # Login
        resp = client.post("/auth/login", data={"username": username, "password": password})
        if resp.status_code != 200:
            print(f"Login failed: {resp.text}")
            sys.exit(1)
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Logged in.")

        # Check current mode
        resp = client.get("/settings/mode", headers=headers)
        print(f"Current mode: {resp.json()}")

        # Switch to live
        resp = client.post(
            "/settings/mode",
            json={"mode": "live", "confirm": "I_UNDERSTAND_RISK"},
            headers=headers,
        )
        if resp.status_code == 200:
            print(f"\n✅ Live mode activated: {resp.json()}")
        elif resp.status_code == 403:
            print(f"\n❌ ALPACA_LIVE_ENABLED is not set to true in .env. Restart backend after setting it.")
        else:
            print(f"\n❌ Failed: {resp.status_code} — {resp.text}")


if __name__ == "__main__":
    main()
