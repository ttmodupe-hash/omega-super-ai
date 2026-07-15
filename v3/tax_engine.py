"""Omega AI v3 — Global Tax Engine
Tax support for all countries with African focus.
"""
from __future__ import annotations

from typing import Any

from utils import colorize, Colors


class TaxEngine:
    """Global tax guidance engine."""

    DISCLAIMER = "\n" + colorize("⚠ DISCLAIMER: General guidance only. Tax laws change frequently. Consult a qualified tax professional for your specific situation.", Colors.YELLOW)

    COUNTRIES: dict[str, dict[str, Any]] = {
        "south_africa": {
            "name": "South Africa", "code": "ZA", "currency": "ZAR",
            "personal_brackets": [(0, 237100, 0.18), (237101, 370500, 0.26), (370501, 512800, 0.31),
                                   (512801, 673000, 0.36), (673001, 857900, 0.39), (857901, 1817000, 0.41), (1817001, float('inf'), 0.45)],
            "primary_rebate": 17235, "secondary_rebate": 9444, "tertiary_rebate": 3145,
            "corporate_rate": 0.27, "vat_rate": 0.15,
            "cg_discount": 0.40, "crypto_taxable": True,
            "filing_deadline": "Individual: Usually end of October (eFiling). Provisional: Aug & Feb.",
            "authority": "SARS (South African Revenue Service)", "url": "https://www.sars.gov.za",
        },
        "nigeria": {
            "name": "Nigeria", "code": "NG", "currency": "NGN",
            "personal_brackets": [(0, 300000, 0.07), (300001, 600000, 0.11), (600001, 1100000, 0.15),
                                   (1100001, 1600000, 0.19), (1600001, 3200000, 0.21), (3200001, float('inf'), 0.24)],
            "consolidated_relief": 200000, "minimum_tax_rate": 0.01,
            "corporate_rate": 0.30, "vat_rate": 0.075,
            "crypto_taxable": True, "crypto_note": "Treated as taxable assets. FIRS guidance applies.",
            "filing_deadline": "Individual: March 31. Companies: 6 months after accounting year-end.",
            "authority": "FIRS (Federal Inland Revenue Service)", "url": "https://www.firs.gov.ng",
        },
        "kenya": {
            "name": "Kenya", "code": "KE", "currency": "KES",
            "personal_brackets_monthly": [(0, 24000, 0.10), (24001, 32333, 0.25), (32334, 500000, 0.30),
                                           (500001, 800000, 0.325), (800001, float('inf'), 0.35)],
            "nssf_rate": 0.06, "nhif_rate_note": "NHIF is a fixed amount based on income bands",
            "housing_levy": 0.015, "corporate_rate": 0.30, "vat_rate": 0.16,
            "crypto_taxable": True, "digital_service_tax": 0.015,
            "filing_deadline": "Individual: June 30. Companies: 6 months after year-end.",
            "authority": "KRA (Kenya Revenue Authority)", "url": "https://www.kra.go.ke",
        },
        "ghana": {
            "name": "Ghana", "code": "GH", "currency": "GHS",
            "personal_brackets": [(0, 490, 0.0), (491, 600, 0.05), (601, 730, 0.10), (731, 3896.67, 0.175),
                                   (3896.68, 19896.67, 0.25), (19896.68, 50416.67, 0.30), (50416.68, float('inf'), 0.35)],
            "corporate_rate": 0.25, "vat_rate": 0.15, "nhil": 0.025, "getfl": 0.025, "chsl": 0.01,
            "crypto_taxable": True,
            "filing_deadline": "Individual: April 30. Companies: 6 months after year-end.",
            "authority": "GRA (Ghana Revenue Authority)", "url": "https://www.gra.gov.gh",
        },
        "egypt": {
            "name": "Egypt", "code": "EG", "currency": "EGP",
            "personal_brackets": [(0, 60000, 0.0), (60001, 80000, 0.10), (80001, 140000, 0.15),
                                   (140001, 200000, 0.20), (200001, 400000, 0.225), (400001, float('inf'), 0.25)],
            "personal_exemption": 21000, "corporate_rate": 0.225, "vat_rate": 0.14,
            "crypto_note": "CBE warns against crypto; no clear tax framework yet.",
            "filing_deadline": "March 31 or April 1 depending on category.",
            "authority": "ETA (Egyptian Tax Authority)", "url": "https://www.eta.gov.eg",
        },
        "morocco": {
            "name": "Morocco", "code": "MA", "currency": "MAD",
            "personal_brackets": [(0, 30000, 0.0), (30001, 50000, 0.10), (50001, 60000, 0.20),
                                   (60001, 80000, 0.30), (80001, 180000, 0.34), (180001, float('inf'), 0.37)],
            "corporate_rate": 0.20, "vat_rate": 0.20, "cnss_rate": 0.0448,
            "crypto_note": "Bank Al-Maghrib prohibits crypto transactions; tax treatment unclear.",
            "filing_deadline": "March 31 for individuals.",
            "authority": "DGI (Direction Générale des Impôts)", "url": "https://www.portnet.ma",
        },
        "united_states": {
            "name": "United States", "code": "US", "currency": "USD",
            "personal_brackets_2026_single": [(0, 11600, 0.10), (11601, 47150, 0.12), (47151, 100525, 0.22),
                                                (100526, 191950, 0.24), (191951, 243725, 0.32), (243726, 609350, 0.35), (609351, float('inf'), 0.37)],
            "standard_deduction_single": 14600, "corporate_rate": 0.21, "vat_note": "No federal VAT; state sales taxes vary",
            "crypto_taxable": True, "crypto_classification": "Property (IRS Notice 2014-21)",
            "filing_deadline": "April 15 (extended to April 18 some years). Extensions available.",
            "authority": "IRS (Internal Revenue Service)", "url": "https://www.irs.gov",
        },
        "united_kingdom": {
            "name": "United Kingdom", "code": "GB", "currency": "GBP",
            "personal_allowance": 12570, "basic_rate": 0.20, "higher_rate": 0.40, "additional_rate": 0.45,
            "basic_threshold": 37700, "higher_threshold": 125140,
            "corporate_rate_small": 0.19, "corporate_rate_main": 0.25, "vat_rate": 0.20,
            "crypto_taxable": True, "crypto_note": "Subject to CGT. HMRC guidance applies.",
            "filing_deadline": "Self Assessment: January 31 (online).",
            "authority": "HMRC", "url": "https://www.gov.uk/hmrc",
        },
        "australia": {
            "name": "Australia", "code": "AU", "currency": "AUD",
            "personal_brackets": [(0, 18200, 0.0), (18201, 45000, 0.16), (45001, 135000, 0.30),
                                   (135001, 190000, 0.37), (190001, float('inf'), 0.45)],
            "medicare_levy": 0.02, "corporate_rate": 0.30, "vat_note": "GST 10%",
            "crypto_taxable": True,
            "filing_deadline": "October 31 (self-lodgers). Tax year: July 1 - June 30.",
            "authority": "ATO (Australian Taxation Office)", "url": "https://www.ato.gov.au",
        },
    }

    ALIASES: dict[str, str] = {
        "south africa": "south_africa", "sa": "south_africa", "za": "south_africa", "rsa": "south_africa",
        "nigeria": "nigeria", "ng": "nigeria",
        "kenya": "kenya", "ke": "kenya",
        "ghana": "ghana", "gh": "ghana",
        "egypt": "egypt", "eg": "egypt",
        "morocco": "morocco", "ma": "morocco",
        "united states": "united_states", "us": "united_states", "usa": "united_states", "america": "united_states",
        "united kingdom": "united_kingdom", "uk": "united_kingdom", "britain": "united_kingdom", "england": "united_kingdom",
        "australia": "australia", "au": "australia", "aus": "australia",
    }

    def tax_query(self, country: str, query_type: str, income: float = 0) -> str:
        """General tax query response."""
        c = self._get_country(country)
        if not c:
            return self._generic_response(country, query_type) + self.DISCLAIMER

        responses = {
            "personal_income": self._personal_income_tax(c, income),
            "corporate": f"## Corporate Tax in {c['name']}\nRate: {c.get('corporate_rate', 'N/A')*100:.1f}%\nCheck {c.get('url', 'official website')} for details.",
            "vat": f"## VAT/GST in {c['name']}\nStandard rate: {c.get('vat_rate', 'N/A')*100:.1f}%\nNote: {c.get('vat_note', 'Standard rate applies.')}",
            "capital_gains": f"## Capital Gains in {c['name']}\n{c.get('cg_discount', 'Regular rates apply. Check local rules.')}",
            "crypto": self._crypto_tax(c),
            "filing_deadline": f"## Filing Deadlines: {c['name']}\n{c.get('filing_deadline', 'Check with ' + c.get('authority', 'tax authority'))}",
            "deductions": f"## Deductions: {c['name']}\nStandard deductions/rebates vary. Contact {c.get('authority', 'tax authority')}.",
            "treaty": f"## Tax Treaties: {c['name']}\n{c['name']} has double taxation agreements with many countries. Check {c.get('url', 'official website')}.",
        }
        return responses.get(query_type, self._all_tax_info(c)) + f"\n\nAuthority: {c.get('authority', '')} | {c.get('url', '')}" + self.DISCLAIMER

    def calculate_estimate(self, country: str, income: float, deductions: dict[str, float] | None = None) -> dict[str, Any]:
        """Calculate estimated tax."""
        c = self._get_country(country)
        deductions = deductions or {}
        if not c or not income:
            return {"country": country, "income": income, "tax": 0, "note": "Insufficient data"}

        taxable = income - sum(deductions.values())
        tax = 0.0
        brackets = c.get("personal_brackets", [])

        for low, high, rate in brackets:
            if taxable <= 0:
                break
            taxable_in_bracket = min(max(taxable - low, 0), high - low)
            tax += taxable_in_bracket * rate

        if "south_africa" in c.get("name", "").lower().replace(" ", "_"):
            tax = max(0, tax - c.get("primary_rebate", 0))

        effective_rate = (tax / income * 100) if income > 0 else 0

        return {
            "country": c["name"],
            "gross_income": income,
            "deductions": sum(deductions.values()),
            "taxable_income": taxable,
            "estimated_tax": round(tax, 2),
            "effective_rate": f"{effective_rate:.1f}%",
            "net_income": round(income - tax, 2),
            "note": "Simplified estimate. Actual tax may differ.",
        }

    def filing_guide(self, country: str, year: int = 2026) -> str:
        """Step-by-step filing guide."""
        c = self._get_country(country)
        if not c:
            return f"## Tax Filing Guide ({year})\n\n1. Identify your tax authority\n2. Gather income documents\n3. Calculate deductions\n4. File online or via tax practitioner\n5. Pay by deadline\n6. Keep records for 5+ years" + self.DISCLAIMER

        return f"""## {c['name']} Tax Filing Guide ({year})

**Authority:** {c.get('authority', '')} | {c.get('url', '')}
**Deadline:** {c.get('filing_deadline', 'Check official website')}

### Steps:
1. **Register** — Get tax number if you don't have one
2. **Gather documents** — IRP5/PAYE, bank statements, investment records
3. **Calculate income** — All sources (salary, freelance, investments, crypto)
4. **Claim deductions** — Medical, retirement, donations, home office
5. **File return** — eFiling/online portal recommended
6. **Pay balance** — Or await refund
7. **Keep records** — Minimum 5 years

### Crypto Specific:
{c.get('crypto_note', 'Check if crypto is taxable in your jurisdiction.')}""" + self.DISCLAIMER

    def compare_regimes(self, countries: list[str]) -> str:
        """Compare tax across countries."""
        lines = ["## Tax Comparison\n"]
        lines.append(f"{'Country':<20} {'Corp Rate':<12} {'VAT':<10} {'Crypto Tax':<12}")
        lines.append("-" * 60)
        for cn in countries:
            c = self._get_country(cn)
            if c:
                corp = f"{c.get('corporate_rate', 0)*100:.1f}%"
                vat = f"{c.get('vat_rate', 0)*100:.1f}%"
                crypto = "Yes" if c.get('crypto_taxable') else "Unclear"
                lines.append(f"{c['name']:<20} {corp:<12} {vat:<10} {crypto:<12}")
        return "\n".join(lines) + self.DISCLAIMER

    def crypto_tax(self, country: str) -> str:
        """Crypto-specific tax rules."""
        c = self._get_country(country)
        if not c:
            return "Crypto tax rules vary. Most countries treat crypto as property/assets." + self.DISCLAIMER
        return self._crypto_tax(c) + self.DISCLAIMER

    def get_tax_summary(self, country: str) -> dict[str, Any]:
        """Key tax facts for a country."""
        c = self._get_country(country)
        if not c:
            return {"error": f"Country '{country}' not found"}
        return {
            "name": c["name"], "code": c.get("code", ""), "currency": c.get("currency", ""),
            "corporate_rate": f"{c.get('corporate_rate', 0)*100:.1f}%",
            "vat_rate": f"{c.get('vat_rate', 0)*100:.1f}%",
            "crypto_taxable": c.get("crypto_taxable", False),
            "authority": c.get("authority", ""), "url": c.get("url", ""),
        }

    def _get_country(self, name: str) -> dict[str, Any] | None:
        """Resolve country name to profile."""
        key = self.ALIASES.get(name.lower().strip())
        if key:
            return self.COUNTRIES.get(key)
        for k, v in self.COUNTRIES.items():
            if name.lower() in k or k.replace("_", " ") in name.lower():
                return v
            if name.lower() in v["name"].lower():
                return v
        return None

    def _personal_income_tax(self, c: dict[str, Any], income: float) -> str:
        brackets = c.get("personal_brackets", c.get("personal_brackets_monthly", []))
        lines = [f"## Personal Income Tax: {c['name']}"]
        lines.append("Tax Brackets:")
        for low, high, rate in brackets:
            high_str = f"{high:,.0f}" if high != float('inf') else "∞"
            lines.append(f"  {low:>12,.0f} - {high_str:<12,.0f} : {rate*100:.0f}%")
        if income > 0:
            est = self.calculate_estimate(c["name"], income)
            lines.append(f"\n**Estimated tax on {c.get('currency', '')} {income:,.2f}:** {est['estimated_tax']:,.2f} ({est['effective_rate']})")
        return "\n".join(lines)

    def _crypto_tax(self, c: dict[str, Any]) -> str:
        lines = [f"## Cryptocurrency Tax: {c['name']}"]
        if c.get("crypto_taxable"):
            lines.append("✅ Crypto transactions ARE taxable")
            lines.append(f"Classification: {c.get('crypto_classification', 'Taxable asset/income')}")
        else:
            lines.append("⚠️ Crypto tax status unclear or restricted")
        if "crypto_note" in c:
            lines.append(f"Note: {c['crypto_note']}")
        return "\n".join(lines)

    def _all_tax_info(self, c: dict[str, Any]) -> str:
        return f"""## Tax Overview: {c['name']}
- **Corporate Tax:** {c.get('corporate_rate', 'N/A')*100:.1f}%
- **VAT/GST:** {c.get('vat_rate', 'N/A')*100:.1f}%
- **Authority:** {c.get('authority', '')}
- **Website:** {c.get('url', '')}
- **Filing:** {c.get('filing_deadline', 'Check website')}"""

    def _generic_response(self, country: str, query_type: str) -> str:
        return f"## Tax Query: {country}\n\nI don't have detailed data for '{country}'. General guidance:\n\n1. Contact your local tax authority\n2. Check if they have online filing\n3. Crypto is taxable in most jurisdictions\n4. Keep records of all income and expenses\n5. Consider a local tax practitioner"


if __name__ == "__main__":
    te = TaxEngine()
    print(te.tax_query("south africa", "personal_income", 500000))
