"""Omega AI v3 — Crypto Price Ticker & Alerts
Live crypto prices via CoinGecko API with mock fallback.
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path
from typing import Any


# Coin mapping: symbol -> CoinGecko ID
_COINS: dict[str, str] = {
    "btc": "bitcoin", "eth": "ethereum", "sol": "solana",
    "xrp": "ripple", "ada": "cardano", "doge": "dogecoin",
    "bnb": "binancecoin", "trx": "tron", "link": "chainlink",
}

# Mock prices for when API is unavailable
_MOCK_PRICES: dict[str, dict] = {
    "btc": {"price": 105230.0, "change": 2.4}, "eth": {"price": 5180.0, "change": -0.8},
    "sol": {"price": 185.0, "change": 5.2}, "xrp": {"price": 0.62, "change": 1.1},
    "ada": {"price": 0.48, "change": -1.5}, "doge": {"price": 0.12, "change": 3.3},
    "bnb": {"price": 720.0, "change": 0.5}, "trx": {"price": 0.13, "change": -0.3},
    "link": {"price": 15.8, "change": 2.1},
}


class PriceTicker:
    """Crypto price lookup with caching and alerts."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, float, float]] = {}  # symbol -> (price, change, ts)
        self._alert_file = Path.home() / ".omega_ai" / "price_alerts.json"

    def get_price(self, symbol: str) -> dict[str, Any]:
        """Get price for a symbol. Uses cache if < 30s old."""
        sym = symbol.lower()
        if sym in self._cache:
            price, change, ts = self._cache[sym]
            if time.time() - ts < 30:
                return {"symbol": sym.upper(), "price_usd": price, "change_24h_percent": change,
                        "source": "cache", "last_updated": time.strftime("%H:%M:%S")}
        return self._fetch_price(sym)

    def _fetch_price(self, symbol: str) -> dict[str, Any]:
        coin_id = _COINS.get(symbol, symbol)
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read())
                if coin_id in data:
                    p = data[coin_id]
                    price = p.get("usd", 0)
                    change = p.get("usd_24h_change", 0)
                    self._cache[symbol] = (price, change, time.time())
                    return {"symbol": symbol.upper(), "price_usd": price,
                            "change_24h_percent": round(change, 2), "source": "coingecko",
                            "last_updated": time.strftime("%H:%M:%S")}
        except Exception:
            pass
        # Mock fallback
        mock = _MOCK_PRICES.get(symbol, {"price": 0, "change": 0})
        return {"symbol": symbol.upper(), "price_usd": mock["price"],
                "change_24h_percent": mock["change"], "source": "mock",
                "last_updated": time.strftime("%H:%M:%S")}

    def get_prices(self, symbols: list[str]) -> list[dict]:
        return [self.get_price(s) for s in symbols]

    def format_table(self, prices: list[dict]) -> str:
        lines = [
            "┌─────────┬──────────────┬──────────┬──────────┐",
            "│ Symbol  │ Price        │ 24h Chg  │ Source   │",
            "├─────────┼──────────────┼──────────┼──────────┤",
        ]
        for p in prices:
            sym = p["symbol"]
            pr = f"${p['price_usd']:,.2f}" if p["price_usd"] >= 1 else f"${p['price_usd']:.4f}"
            chg = f"{p['change_24h_percent']:+.1f}%"
            src = p["source"][:8]
            lines.append(f"│ {sym:<7} │ {pr:>12} │ {chg:>8} │ {src:<8} │")
        lines.append("└─────────┴──────────────┴──────────┴──────────┘")
        return "\n".join(lines)

    def set_alert(self, symbol: str, condition: str, target: float) -> dict:
        """Set a price alert. condition: 'above' or 'below'."""
        alerts = self._read_alerts()
        alert_id = f"{symbol.lower()}_{condition}_{target}"
        alerts.append({"id": alert_id, "symbol": symbol.lower(), "condition": condition,
                       "target": float(target), "created": time.strftime("%Y-%m-%dT%H:%M:%S")})
        self._write_alerts(alerts)
        return {"id": alert_id, "status": "set"}

    def check_alerts(self) -> list[dict]:
        """Check all alerts against current prices."""
        alerts = self._read_alerts()
        triggered = []
        for a in alerts:
            p = self.get_price(a["symbol"])
            price = p["price_usd"]
            if (a["condition"] == "above" and price >= a["target"]) or \
               (a["condition"] == "below" and price <= a["target"]):
                triggered.append({**a, "current_price": price})
        return triggered

    def list_alerts(self) -> list[dict]:
        return self._read_alerts()

    def delete_alert(self, alert_id: str) -> bool:
        alerts = [a for a in self._read_alerts() if a["id"] != alert_id]
        self._write_alerts(alerts)
        return True

    def _read_alerts(self) -> list:
        if not self._alert_file.exists():
            return []
        try:
            return json.loads(self._alert_file.read_text())
        except (json.JSONDecodeError, OSError):
            return []

    def _write_alerts(self, alerts: list) -> None:
        self._alert_file.parent.mkdir(parents=True, exist_ok=True)
        self._alert_file.write_text(json.dumps(alerts, indent=2), encoding="utf-8")

    def handle_command(self, args: list[str]) -> str:
        """Route CLI-style commands."""
        if not args:
            return self.format_table(self.get_prices(["btc", "eth", "sol"]))
        cmd = args[0].lower()

        if cmd == "alert" and len(args) >= 4:
            r = self.set_alert(args[1], args[2], float(args[3]))
            return f"✅ Alert set: {r['id']}"
        elif cmd == "alerts":
            alerts = self.list_alerts()
            if not alerts:
                return "No active alerts."
            return "\n".join(f"  {a['id']}: {a['symbol']} {a['condition']} ${a['target']}" for a in alerts)
        elif cmd == "check":
            triggered = self.check_alerts()
            if not triggered:
                return "No alerts triggered."
            return "\n".join(f"  🔔 {t['symbol']} ${t['current_price']:,.2f} is {t['condition']} ${t['target']}" for t in triggered)
        else:
            # Price lookup for symbols
            symbols = [a.lower() for a in args if a.lower() in _COINS or a.lower() in _MOCK_PRICES]
            if not symbols:
                symbols = ["btc", "eth", "sol"]
            return self.format_table(self.get_prices(symbols))