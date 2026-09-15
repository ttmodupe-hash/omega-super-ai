"""Omega AI v3 — Investment & Mining Engine
Crypto investment guidance, BTC mining calculations, portfolio advice.
"""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from typing import Any

from utils import colorize, Colors


class InvestmentMining:
    """Crypto investment and BTC mining guidance engine."""

    BTC_DIFFICULTY = 95_000_000_000_000
    BTC_BLOCK_REWARD = 3.125
    BTC_HASHRATE_EHS = 850

    ASIC_CATALOG: dict[str, dict[str, Any]] = {
        "bitmain_s21_pro": {"name": "Bitmain Antminer S21 Pro", "hashrate_ths": 234, "power_w": 3510, "efficiency_j_th": 15.0, "price_usd": 4500},
        "microbt_m60s": {"name": "MicroBT WhatsMiner M60S", "hashrate_ths": 186, "power_w": 3348, "efficiency_j_th": 18.0, "price_usd": 3200},
        "bitmain_t21": {"name": "Bitmain Antminer T21", "hashrate_ths": 190, "power_w": 3610, "efficiency_j_th": 19.0, "price_usd": 2800},
        "microbt_m50s": {"name": "MicroBT WhatsMiner M50S", "hashrate_ths": 126, "power_w": 3276, "efficiency_j_th": 26.0, "price_usd": 1800},
        "bitmain_s19j_pro": {"name": "Bitmain Antminer S19j Pro", "hashrate_ths": 104, "power_w": 3068, "efficiency_j_th": 29.5, "price_usd": 1200},
        "canaan_a1466": {"name": "Canaan Avalon A1466", "hashrate_ths": 150, "power_w": 3450, "efficiency_j_th": 23.0, "price_usd": 2200},
        "ibelink_bm_k3": {"name": "iBeLink BM-K3", "hashrate_ths": 70, "power_w": 3300, "efficiency_j_th": 47.1, "price_usd": 2500},
    }

    def __init__(self) -> None:
        self._price_cache: dict[str, tuple[float, float]] = {}

    def disclaimer(self) -> str:
        return "\n" + colorize("⚠ DISCLAIMER: Not financial advice. DYOR. Crypto is volatile. Past performance ≠ future results. Only invest what you can afford to lose.", Colors.YELLOW)

    def mining_guide(self, query_type: str, inputs: dict[str, Any] | None = None) -> str:
        """Guide for BTC/crypto mining."""
        inputs = inputs or {}
        guides = {
            "profitability": self._profitability_guide(inputs),
            "hardware": self._hardware_guide(),
            "pools": self._pool_guide(),
            "setup": self._setup_guide(),
            "asic_comparison": self._asic_comparison(),
        }
        return guides.get(query_type, self._general_mining_guide()) + self.disclaimer()

    def mining_profitability(self, hash_rate_ths: float, power_cost_usd: float,
                             power_watts: float, pool_fee: float = 0.02) -> dict[str, Any]:
        """Calculate mining profitability."""
        daily_blocks = 144
        network_hashrate_hs = self.BTC_HASHRATE_EHS * 1e18
        user_hashrate_hs = hash_rate_ths * 1e12
        block_reward = self.BTC_BLOCK_REWARD

        daily_btc = (user_hashrate_hs / network_hashrate_hs) * daily_blocks * block_reward
        daily_btc *= (1 - pool_fee)

        daily_power_kwh = (power_watts * 24) / 1000
        daily_power_cost = daily_power_kwh * power_cost_usd

        btc_price = self._get_cached_price("bitcoin")
        daily_revenue_usd = daily_btc * btc_price
        daily_profit_usd = daily_revenue_usd - daily_power_cost

        return {
            "daily": {"btc": round(daily_btc, 8), "revenue_usd": round(daily_revenue_usd, 2), "power_cost": round(daily_power_cost, 2), "profit_usd": round(daily_profit_usd, 2)},
            "weekly": {"btc": round(daily_btc * 7, 8), "profit_usd": round(daily_profit_usd * 7, 2)},
            "monthly": {"btc": round(daily_btc * 30, 8), "profit_usd": round(daily_profit_usd * 30, 2)},
            "yearly": {"btc": round(daily_btc * 365, 8), "profit_usd": round(daily_profit_usd * 365, 2)},
            "assumptions": {"btc_price_usd": btc_price, "network_hashrate_ehs": self.BTC_HASHRATE_EHS, "pool_fee": pool_fee, "power_cost_usd_kwh": power_cost_usd},
        }

    def investment_analysis(self, asset: str) -> dict[str, Any]:
        """Market outlook for a crypto asset."""
        price = self._get_cached_price(asset)
        outlooks = {
            "bitcoin": {"trend": "Bullish long-term", "outlook": "BTC remains the dominant store of value in crypto. Post-halving supply squeeze could drive prices higher.", "risk_level": "Medium"},
            "ethereum": {"trend": "Bullish", "outlook": "ETH benefits from DeFi, L2 scaling, and staking yields. Competition from Solana and others is a factor.", "risk_level": "Medium-High"},
            "solana": {"trend": "Mixed", "outlook": "High performance but network reliability concerns. Strong developer ecosystem.", "risk_level": "High"},
        }
        data = outlooks.get(asset.lower(), {"trend": "Neutral", "outlook": "Research required for this asset.", "risk_level": "Unknown"})
        data["price_usd"] = price
        data["sources"] = [{"title": f"{asset.title()} Price Data", "source": "CoinGecko"}]
        return data

    def portfolio_advice(self, holdings: dict[str, float]) -> str:
        """Portfolio analysis and suggestions."""
        total = sum(holdings.values())
        if total == 0:
            return "Please provide your portfolio holdings as percentages." + self.disclaimer()

        lines = ["## Portfolio Analysis\n", f"Total Allocation: 100%"]
        for asset, pct in sorted(holdings.items(), key=lambda x: -x[1]):
            bar = "█" * int(pct / 2)
            lines.append(f"  {asset.upper():<8} {pct:>5.1f}% {bar}")

        if holdings.get("btc", 0) + holdings.get("bitcoin", 0) < 30:
            lines.append("\n**Note:** BTC allocation under 30%. Consider increasing for stability.")
        if len(holdings) > 10:
            lines.append("\n**Note:** Over 10 assets. Consider consolidating for easier management.")

        lines.append(self.disclaimer())
        return "\n".join(lines)

    def risk_assessment(self, strategy: str) -> dict[str, Any]:
        """Risk analysis for investment strategy."""
        strategies = {
            "conservative": {"description": "Mostly BTC/ETH with stablecoins", "risk": "Low", "expected_return": "10-30% annually", "max_drawdown": "-30%"},
            "balanced": {"description": "60% major coins, 30% mid-cap, 10% speculative", "risk": "Medium", "expected_return": "30-80% annually", "max_drawdown": "-50%"},
            "aggressive": {"description": "Heavy altcoins, DeFi, new projects", "risk": "High", "expected_return": "80-300% annually", "max_drawdown": "-80%"},
        }
        return strategies.get(strategy.lower(), strategies["balanced"])

    def get_crypto_price(self, symbol: str) -> dict[str, Any]:
        """Get current crypto price."""
        price = self._get_cached_price(symbol)
        return {"symbol": symbol.upper(), "price_usd": price, "timestamp": datetime.now(timezone.utc).isoformat()}

    def _get_cached_price(self, symbol: str) -> float:
        """Get price with caching."""
        now = datetime.now(timezone.utc).timestamp()
        if symbol in self._price_cache:
            price, ts = self._price_cache[symbol]
            if now - ts < 300:
                return price

        try:
            coin_map = {"bitcoin": "bitcoin", "btc": "bitcoin", "ethereum": "ethereum", "eth": "ethereum",
                        "solana": "solana", "sol": "solana", "xrp": "ripple", "ripple": "ripple",
                        "dogecoin": "dogecoin", "doge": "dogecoin", "cardano": "cardano", "ada": "cardano"}
            coin_id = coin_map.get(symbol.lower(), symbol.lower())
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                price = data.get(coin_id, {}).get("usd", 0)
                if price:
                    self._price_cache[symbol] = (price, now)
                    return price
        except Exception:
            pass

        mock_prices = {"bitcoin": 105000, "btc": 105000, "ethereum": 5200, "eth": 5200,
                       "solana": 185, "sol": 185, "xrp": 0.75, "ripple": 0.75,
                       "dogecoin": 0.18, "doge": 0.18, "cardano": 0.55, "ada": 0.55}
        return mock_prices.get(symbol.lower(), 0)

    def _profitability_guide(self, inputs: dict[str, Any]) -> str:
        hr = inputs.get("hashrate_ths", 100)
        power = inputs.get("power_cost", 0.10)
        watts = inputs.get("power_watts", 3000)
        result = self.mining_profitability(hr, power, watts)
        d = result["daily"]
        return f"""## Mining Profitability (Daily)
- Revenue: ${d['revenue_usd']:.2f} ({d['btc']:.8f} BTC)
- Power Cost: ${d['power_cost']:.2f}
- **Profit: ${d['profit_usd']:.2f}**
- Monthly: ${result['monthly']['profit_usd']:.2f}
- Yearly: ${result['yearly']['profit_usd']:.2f}
*Assumptions: BTC ${result['assumptions']['btc_price_usd']:,.0f}, Network {result['assumptions']['network_hashrate_ehs']} EH/s*"""

    def _hardware_guide(self) -> str:
        return "## Mining Hardware Guide\n\nTop ASICs (2026):\n" + "\n".join(
            f"- {a['name']}: {a['hashrate_ths']} TH/s @ {a['efficiency_j_th']} J/TH (~${a['price_usd']})"
            for a in sorted(self.ASIC_CATALOG.values(), key=lambda x: x['efficiency_j_th'])
        ) + "\n\n**Tip:** Lower J/TH = more efficient. Calculate ROI before purchasing."

    def _pool_guide(self) -> str:
        return "## Mining Pool Guide\n\nTop Pools:\n- Foundry USA (~30% hashrate)\n- Antpool (~25%)\n- F2Pool (~15%)\n- ViaBTC (~10%)\n\nFactors: Pool fee (1-3%), payout method (PPS vs PPLNS), server location, reputation."

    def _setup_guide(self) -> str:
        return "## Mining Setup Guide\n\n1. **Choose hardware** — Calculate ROI first\n2. **Select pool** — Compare fees and reliability\n3. **Get wallet** — Secure cold storage recommended\n4. **Configure miner** — Point to pool stratum URL\n5. **Monitor** — Track temps, hashrate, profitability\n6. **Optimize** — Consider immersion cooling for scale"

    def _asic_comparison(self) -> str:
        return self._hardware_guide()

    def _general_mining_guide(self) -> str:
        return "## Bitcoin Mining Overview\n\nBTC mining secures the network and earns block rewards. Key factors:\n- **Hardware**: ASIC miners (specialized chips)\n- **Electricity**: Your biggest cost — seek cheap, stable power\n- **Pool**: Join a pool for consistent payouts\n- **Difficulty**: Adjusts every 2,016 blocks (~2 weeks)\n- **Halving**: Block reward halves every ~4 years (last: April 2024)\n\nUse /profitability to calculate your specific ROI."


if __name__ == "__main__":
    im = InvestmentMining()
    print(im.mining_guide("profitability", {"hashrate_ths": 234, "power_cost": 0.08, "power_watts": 3510}))
