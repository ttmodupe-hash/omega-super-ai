"""Omega AI v3 — Web Search Integration
Serper API for Google search, news, and images.
"""
from __future__ import annotations

import json
import urllib.request
from typing import Any

from config import CONFIG
from utils import print_warning


class WebSearch:
    """Web search via Serper API with mock fallback."""

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key or str(CONFIG.get("SERPER_API_KEY", ""))
        self.base_url = "https://google.serper.dev"
        self.timeout = int(CONFIG.get("REQUEST_TIMEOUT", 15))

    def search(self, query: str, num_results: int = 5) -> list[dict[str, Any]]:
        """Perform Google search. Returns list of result dicts."""
        return self._request("/search", query, num_results)

    def news_search(self, query: str, num_results: int = 5) -> list[dict[str, Any]]:
        """Search news."""
        return self._request("/news", query, num_results)

    def image_search(self, query: str, num_results: int = 3) -> list[dict[str, Any]]:
        """Search images."""
        return self._request("/images", query, num_results)

    def _request(self, endpoint: str, query: str, num: int) -> list[dict[str, Any]]:
        """Make API request with fallback to mock data."""
        if not self.api_key:
            return self._mock_data(query, endpoint)

        try:
            payload = json.dumps({"q": query, "num": num}).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}{endpoint}",
                data=payload,
                headers={
                    "X-API-KEY": self.api_key,
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read())
                return self._parse_results(data, endpoint)
        except Exception as e:
            print_warning(f"Search API error: {e}. Using mock data.")
            return self._mock_data(query, endpoint)

    def _parse_results(self, data: dict, endpoint: str) -> list[dict[str, Any]]:
        """Parse API response into standard format."""
        results: list[dict[str, Any]] = []
        key = "news" if endpoint == "/news" else "images" if endpoint == "/images" else "organic"
        for item in data.get(key, []):
            results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", item.get("imageUrl", "")),
                "source": item.get("source", self._extract_domain(item.get("link", ""))),
                "date": item.get("date", ""),
            })
        return results

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            return url.split("/")[2].replace("www.", "")
        except IndexError:
            return "web"

    def _mock_data(self, query: str, endpoint: str) -> list[dict[str, Any]]:
        """Generate contextual mock search results."""
        q = query.lower()
        if "bitcoin" in q or "btc" in q or "crypto" in q:
            return [
                {"title": "Bitcoin Mining Profitability Calculator 2026", "link": "https://www.coinwarz.com/mining/bitcoin", "snippet": "Calculate BTC mining ROI with current difficulty and price.", "source": "CoinWarz", "date": "2026-07-01"},
                {"title": "Best Bitcoin Mining Hardware (2026)", "link": "https://www.asicminervalue.com", "snippet": "ASIC comparison: S21 Pro, M60S, T21 efficiency rankings.", "source": "ASIC Miner Value", "date": "2026-06-20"},
                {"title": "Crypto Tax Guide for South Africa", "link": "https://www.sars.gov.za", "snippet": "SARS guidance on cryptocurrency taxation and compliance.", "source": "SARS", "date": "2026-05-15"},
            ]
        elif "tax" in q:
            return [
                {"title": "South African Tax Guide 2026/2027", "link": "https://www.sars.gov.za", "snippet": "Updated tax brackets, rebates, and filing deadlines.", "source": "SARS", "date": "2026-03-01"},
                {"title": "Nigeria FIRS Tax Filing Procedures", "link": "https://www.firs.gov.ng", "snippet": "How to file personal income tax in Nigeria.", "source": "FIRS", "date": "2026-04-10"},
            ]
        elif "opportunity" in q or "business" in q:
            return [
                {"title": "Top Business Opportunities in Africa 2026", "link": "https://www.africabusiness.com", "snippet": "Agriculture tech, fintech, renewable energy sectors.", "source": "Africa Business", "date": "2026-06-01"},
                {"title": "African Startup Ecosystem Report", "link": "https://www.disruptafrica.com", "snippet": "Funding trends, emerging markets, and success stories.", "source": "Disrupt Africa", "date": "2026-05-20"},
            ]
        else:
            return [
                {"title": f"Search Results for: {query}", "link": "https://example.com", "snippet": f"Information about {query} from various sources.", "source": "Web", "date": "2026-07-15"},
                {"title": f"Understanding {query}", "link": "https://example.com/guide", "snippet": f"Comprehensive guide to {query}.", "source": "GuideHub", "date": "2026-07-10"},
            ]


if __name__ == "__main__":
    ws = WebSearch()
    results = ws.search("Bitcoin mining profitability 2026")
    for r in results:
        print(f"- {r['title']} ({r['source']})")
