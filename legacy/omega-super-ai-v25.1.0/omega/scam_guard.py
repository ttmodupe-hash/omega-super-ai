"""
Scam Guard Module — Omega Super AI v10

Comprehensive scam and fraud protection system providing pattern-based
analysis, URL safety checks, message inspection, protection tips,
scam reporting, and statistical tracking.

This module analyzes communications and offers for known scam patterns,
providing actionable safety advice and guidance on reporting fraud.

Classes:
    ScamGuard: Multi-layered fraud detection and protection system.

Example:
    guard = ScamGuard(openai_client=client, db=database)
    result = guard.analyze("You've won $1,000,000! Send $500 to claim your prize.")
    url_check = guard.check_url("https://suspicious-bank-login.tk")
    tips = guard.get_protection_tips("online_shopping")
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class ScamGuard:
    """Multi-layered fraud detection and consumer protection system.

    Analyzes descriptions, URLs, and messages against known scam patterns,
    provides actionable safety advice, and supports scam reporting and
    statistics tracking.

    Attributes:
        KNOWN_PATTERNS (dict): Mapping of pattern names to descriptions.
    """

    KNOWN_PATTERNS: dict[str, str] = {
        "too_good_to_be_true": "Promises unrealistic returns or benefits",
        "urgency_pressure": "Creates false time pressure",
        "upfront_payment": "Requires payment before service delivery",
        "unsolicited_contact": "Contacted without request",
        "fake_credentials": "Uses forged or unverifiable credentials",
        "pyramid_structure": "Requires recruiting others to earn",
        "guaranteed_returns": "Promises no-risk high returns",
        "request_personal_info": "Asks for sensitive data unexpectedly",
        "advance_fee": "Requires fee to release promised money",
        "phishing": "Attempts to steal login credentials",
        "romance_scam": "Uses relationship to extract money",
        "tech_support_scam": "Pretends to be tech support",
        "government_impersonation": "Pretends to be government official",
        "job_scam": "Fake job offer requiring payment",
        "lottery_scam": "Claims you've won something you didn't enter",
    }

    # Suspicious TLDs commonly used for scams
    SUSPICIOUS_TLDS: set[str] = {
        ".tk", ".ml", ".ga", ".cf", ".gq",  # Free TLDs
        ".top", ".xyz", ".click", ".link", ".work",
        ".date", ".party", ".racing", ".win", ".bid",
        ".download", ".men", ".stream", ".trade", ".webcam",
        ".accountant", ".zip", ".mov",  # New suspicious TLDs
    }

    # Known brand typosquatting patterns
    TYPO_PATTERNS: dict[str, list[str]] = {
        "paypal": ["paypa1", "paypall", "paypäl", "paypaI"],
        "amazon": ["amaz0n", "arnazon", "amazom", "amazn"],
        "apple": ["app1e", "aple", "applle", "äpple"],
        "google": ["g00gle", "gogle", "googIe", "gooogle"],
        "microsoft": ["micros0ft", "micrsoft", "microsft", "rnicrosoft"],
        "facebook": ["faceb00k", "faceboook", "facbook", "facebok"],
        "netflix": ["netfl1x", "netfllx", "netlix", "nefliix"],
        "chase": ["chas3", "chasse", "cháse", "chas e"],
        "wellsfargo": ["wellsfarg0", "wellsfargoo", "wellsfarg"],
        "bankofamerica": ["bankofamer1ca", "bankofamerika", "bankofamerca"],
    }

    # Pattern detection regexes
    PATTERN_REGEXES: dict[str, list[str]] = {
        "too_good_to_be_true": [
            r"\b(?:won|win)\b.*\$\d{3,}",
            r"\$\d{3,}.*\b(?:won|win|prize|reward)\b",
            r"\b(?:million|billion)\s+(?:dollar|dollars)\b",
            r"\bfree\b.*\b(?:money|cash|gift)\b",
            r"\d{3,}%\s+(?:return|profit|gain)",
        ],
        "urgency_pressure": [
            r"\b(?:urgent|immediately|now|hurry|act fast|limited time|expires?|deadline)\b",
            r"\b(?:today only|last chance|final notice|act now|don't wait)\b",
            r"\b(?:only \d+ (?:left|spots|hours)|limited availability)\b",
            r"\b(?:your account.*(?:expire|suspend|close|disable))\b",
        ],
        "upfront_payment": [
            r"\b(?:send|wire|transfer|pay).*(?:fee|payment|deposit).*(?:first|before|upfront)\b",
            r"\b(?:processing|administration|handling|release)\s+fee\b",
            r"\b(?:pay|send).*\$\d+.*(?:to|for).*(?:receive|get|claim|unlock)\b",
        ],
        "unsolicited_contact": [
            r"\b(?:you were selected|chosen|randomly selected|special offer)\b",
            r"\b(?:we noticed|our records show)\b",
        ],
        "fake_credentials": [
            r"\b(?:certified|licensed|official|authorized|verified)\b.*\b(?:expert|specialist|agent)\b",
            r"\b(?:SEC approved|government backed|FDA certified)\b",
        ],
        "pyramid_structure": [
            r"\b(?:recruit|referral|downline|team building|network)\b.*\b(?:earn|income|commission)\b",
            r"\b(?:mlm|multi[- ]?level marketing|network marketing)\b",
            r"\b(?:passive income|residual income).*\b(?:recruit|refer)\b",
        ],
        "guaranteed_returns": [
            r"\b(?:guaranteed|assured|promised|risk[- ]?free)\s+(?:return|profit|income)\b",
            r"\b(?:no risk|zero risk|can't lose)\b",
            r"\b(?:guaranteed).*(?:\d+%|double|triple)\b",
        ],
        "request_personal_info": [
            r"\b(?:verify|confirm|update).*(?:SSN|social security|password|PIN|account number)\b",
            r"\b(?:provide|enter|submit).*(?:credit card|bank account|routing number)\b",
            r"\b(?:login|sign in).*(?:verify|confirm|secure)\b",
        ],
        "advance_fee": [
            r"\b(?:advance|upfront|initial).*(?:fee|payment|deposit)\b",
            r"\b(?:pay|send).*(?:fee|tax|duty).*(?:release|receive|claim)\b",
        ],
        "phishing": [
            r"\b(?:verify|confirm|update|secure).*(?:account|login|password|billing)\b",
            r"\b(?:click|follow).*(?:link|here).*(?:verify|confirm|update)\b",
            r"\b(?:suspicious activity|unusual login|security alert)\b",
            r"\b(?:your account.*(?:compromised|locked|limited))\b",
        ],
        "romance_scam": [
            r"\b(?:send me money|need money|financial help|loan me)\b",
            r"\b(?:can't meet|stuck abroad|military deployment|need gift cards)\b",
            r"\b(?:wire money|Western Union|MoneyGram)\b.*\b(?:love|relationship)\b",
        ],
        "tech_support_scam": [
            r"\b(?:tech support|Microsoft|Apple|Google).*(?:virus|infected|hacked|problem)\b",
            r"\b(?:your computer|your device).*(?:infected|compromised|at risk|virus)\b",
            r"\b(?:call|contact).*(?:tech support|technical department|help desk)\b",
            r"\b(?:remote access|TeamViewer|AnyDesk|screen share)\b.*\b(?:fix|repair|clean)\b",
        ],
        "government_impersonation": [
            r"\b(?:IRS|Social Security Administration|SSA|FBI|DEA| Treasury)\b.*\b(?:arrest|warrant|sue|suspend)\b",
            r"\b(?:government|federal).*(?:grant|benefit|refund|rebate)\b.*\b(?:fee|payment)\b",
            r"\b(?:owe|debt).*(?:IRS|taxes).*(?:arrest|warrant|jail)\b",
            r"\b(?:social security number|SSN).*(?:suspend|cancel|fraudulent)\b",
        ],
        "job_scam": [
            r"\b(?:work from home|remote job|earn \$\d+/week)\b.*\b(?:fee|training|equipment|deposit)\b",
            r"\b(?:reshipping|package forwarding|mystery shopper)\b.*\b(?:pay|fee)\b",
            r"\b(?:no experience|no resume).*(?:high pay|earn \$\d{2,})\b",
        ],
        "lottery_scam": [
            r"\b(?:lottery|sweepstakes|drawing|raffle)\b.*\b(?:won|winner|prize)\b",
            r"\b(?:claim your prize|collect your winnings)\b.*\b(?:fee|tax|payment)\b",
            r"\b(?:did not enter|didn't enter|never entered)\b.*\b(?:won|winner)\b",
        ],
    }

    # Protection tips by category
    PROTECTION_TIPS: dict[str, str] = {
        "general": """
# General Scam Protection Tips

## The Golden Rules
1. **If it's too good to be true, it IS.** No exceptions.
2. **Never send money to strangers.** Ever.
3. **Don't share personal info** unless YOU initiated contact and verified identity.
4. **Take your time.** Scammers create urgency to bypass your judgment.
5. **Verify independently.** Look up phone numbers, organizations, and offers separately.

## Common Signs of a Scam
- Unsolicited contact (email, call, text, DM)
- Pressure to act immediately
- Requests for payment via wire transfer, gift cards, or cryptocurrency
- Requests for personal/financial information
- Promises of guaranteed returns or prizes
- Threats of legal action or account suspension

## What To Do If Contacted
- Hang up on suspicious calls
- Delete suspicious emails without clicking links
- Block suspicious numbers and accounts
- Report to relevant authorities
""",
        "online_shopping": """
# Online Shopping Protection

1. **Shop only on secure sites** — look for HTTPS and a padlock icon
2. **Use credit cards** — they offer better fraud protection than debit
3. **Research unfamiliar sellers** — search "[company] + scam/review/complaint"
4. **Be wary of social media ads** — many scam shops advertise on Facebook/Instagram
5. **Check return policies** before purchasing
6. **Use payment services** (PayPal, Apple Pay) that offer buyer protection
7. **Don't buy from sites with**:
   - No contact information or physical address
   - Prices way below market value
   - Poor grammar and spelling
   - No customer reviews or only suspicious 5-star reviews
8. **Keep records** of all transactions and confirmations
""",
        "investments": """
# Investment Scam Protection

1. **Verify registration** at SEC.gov, FINRA.org, or your state regulator
2. **Check BrokerCheck** for disciplinary history on any advisor
3. **Beware of 'guaranteed' returns** — all legitimate investments carry risk
4. **Never invest in something you don't understand**
5. **Pressure to invest immediately** is a huge red flag
6. **Unsolicited investment offers** are almost always scams
7. **Offshore/unregulated investments** are extremely risky
8. **Get everything in writing** — verbal promises are meaningless
9. **Consult an independent, fee-only fiduciary advisor**
10. **Report suspicious offers** to SEC.gov/tcr

## Warning Signs
- Promises of high returns with no risk
- Complex strategies you can't understand
- Secret or exclusive methods
- Requires recruiting others
- Unregistered with regulators
""",
        "dating": """
# Dating and Romance Scam Protection

1. **Never send money** to someone you haven't met in person
2. **Be suspicious of fast-moving relationships** online
3. **Google their photos** — scammers use stolen images (reverse image search)
4. **Be wary of excuses** for why they can't video chat or meet
5. **Never share financial information** with online romantic interests
6. **Be especially cautious with**:
   - Military personnel claiming to be deployed
   - Oil rig workers or overseas contractors
   - Models or wealthy individuals who seem too perfect
   - People who fall in love unusually quickly
7. **Gift cards are for gifts, not payments** — anyone asking for gift cards is scamming
8. **Talk to friends/family** about new online relationships

## Red Flags
- Professes love quickly without meeting
- Has a tragic story and needs money
- Claims to be stuck in a foreign country
- Wants to communicate off the dating platform immediately
- Sends photos that look professional or too perfect
""",
        "employment": """
# Job Scam Protection

1. **Legitimate employers never charge fees** to hire you
2. **Never pay for training, equipment, or background checks** upfront
3. **Research the company** — search "[company] + scam/review"
4. **Be wary of 'work from home' offers** with unrealistic pay
5. **Never provide bank info** before being officially hired
6. **Reshipping and package forwarding jobs** are often money laundering
7. **Verify the email domain** matches the company's real website
8. **Be cautious of jobs that**:
   - Require no experience but pay very well
   - Use personal email addresses (Gmail, Yahoo) instead of company domains
   - Conduct interviews only via text or chat
   - Ask you to purchase equipment from a specific vendor
9. **Check the company exists** via state business registration
10. **Report job scams** to the FTC at ReportFraud.FTC.gov
""",
        "tech_support": """
# Tech Support Scam Protection

1. **Legitimate tech companies never call you unsolicited**
2. **Never give remote access** to someone who called YOU
3. **Pop-up warnings** saying you have a virus are ALWAYS fake
4. **Real security software** doesn't display phone numbers in warnings
5. **Don't call numbers** from pop-ups or unexpected emails
6. **If concerned**, contact the company directly through their official website
7. **Never provide passwords or payment info** to unsolicited callers
8. **Microsoft, Apple, and Google** do NOT make unsolicited support calls

## If You Fell For a Tech Support Scam
- Disconnect from the internet immediately
- Run a full antivirus scan
- Change all passwords from a clean device
- Contact your bank if you shared payment info
- Report to FTC at ReportFraud.FTC.gov
""",
        "lottery": """
# Lottery and Prize Scam Protection

1. **You can't win a lottery you didn't enter**
2. **Legitimate lotteries never require payment** to collect winnings
3. **Foreign lottery solicitations by mail/email are illegal** in the US
4. **No government agency** holds unclaimed prize money you need to pay to release
5. **Never pay 'taxes' or 'fees'** to claim a prize — taxes are deducted from winnings
6. **Beware of checks** sent as 'advance' — they'll bounce after you send 'fees'
7. **Verify through official channels** — contact the lottery organization directly

## Common Lottery Scam Formats
- Email saying you won an international lottery
- Social media message claiming you're a winner
- Phone call about a sweepstakes prize
- Letter with a check asking you to send back a portion
""",
        "real_estate": """
# Real Estate Scam Protection

1. **Never rent a property you haven't seen** in person or via verified video
2. **Be wary of below-market prices** — they're bait for scams
3. **Never wire deposit money** before signing a lease and getting keys
4. **Verify the landlord owns the property** — check county records
5. **Rental scams often use**:
   - Copied listings from legitimate sites with lower prices
   - Excuses for why the owner can't show the property
   - Pressure to decide immediately
   - Requests for wire transfer or cryptocurrency
6. **For purchases**: Work with a licensed real estate agent
7. **Verify licenses** at your state's real estate commission
8. **Beware of 'foreclosure rescue' scams** that require upfront fees
9. **Get everything in writing** and have a lawyer review contracts
""",
        "cryptocurrency": """
# Cryptocurrency Scam Protection

1. **No one can 'guarantee' returns** in crypto — extreme volatility is the norm
2. **Never share your private keys or seed phrase** — anyone with these controls your funds
3. **Beware of 'recovery services'** that charge upfront fees to recover lost crypto
4. **Fake exchanges and wallets** — only use well-known, verified platforms
5. **Pig butchering scams** — romance + investment scam combo, very common
6. **Rug pulls** — developers abandon a project after taking investor money
7. **Pump and dump schemes** — coordinated price manipulation
8. **Celebrity endorsements** are often fake or paid — verify independently
9. **Smart contract audits** matter — un-audited projects are high risk
10. **If someone asks you to send crypto** to 'verify' something, it's a scam

## Red Flags
- Guaranteed returns in any crypto investment
- Requirements to recruit others
- Unaudited smart contracts
- Anonymous teams with no track record
- Promises of 'exclusive' early access
""",
    }

    def __init__(self, openai_client: Any, db: Any = None) -> None:
        """Initialize ScamGuard with an AI client and optional database.

        Args:
            openai_client: An initialized OpenAI-compatible API client.
            db: Optional database connection for scam reporting and statistics.
        """
        self.openai_client = openai_client
        self.db = db
        logger.info("ScamGuard initialized (db=%s)", "connected" if db else "none")

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _chat(self, system: str, user: str, temperature: float = 0.3) -> str:
        """Call the OpenAI-compatible chat endpoint safely."""
        try:
            resp = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
                max_tokens=4096,
            )
            return resp.choices[0].message.content.strip()
        except Exception as exc:
            logger.error("OpenAI API error: %s", exc)
            return f"[Error contacting AI service: {exc}]"

    def _safe_json(self, text: str) -> Any:
        """Parse JSON from model output, stripping markdown fences."""
        cleaned = text
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("\n", 1)[0]
        cleaned = cleaned.strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                logger.error("JSON parse error: %s", exc)
                return {"error": "Failed to parse JSON", "raw": text}

    def _match_patterns(self, text: str) -> list[dict[str, Any]]:
        """Match text against known scam pattern regexes.

        Args:
            text: The text to analyze.

        Returns:
            A list of matched pattern dictionaries.
        """
        text_lower = text.lower()
        matches: list[dict[str, Any]] = []

        for pattern_name, regexes in self.PATTERN_REGEXES.items():
            for regex in regexes:
                if re.search(regex, text_lower):
                    matches.append({
                        "pattern": pattern_name,
                        "description": self.KNOWN_PATTERNS.get(
                            pattern_name, "Unknown pattern"
                        ),
                        "confidence": "HIGH",
                        "evidence": f"Matched pattern: {regex}",
                    })
                    break  # Only count each pattern once

        return matches

    def _calculate_likelihood(self, pattern_matches: list[dict[str, Any]]) -> int:
        """Calculate scam likelihood score from pattern matches.

        Args:
            pattern_matches: List of matched patterns.

        Returns:
            Integer score from 0 to 100.
        """
        base = len(pattern_matches) * 12

        # Boost for critical patterns
        critical_patterns = {"phishing", "request_personal_info", "government_impersonation",
                             "advance_fee", "pyramid_structure"}
        for match in pattern_matches:
            if match["pattern"] in critical_patterns:
                base += 15

        return min(100, base)

    def _risk_level(self, likelihood: int) -> str:
        """Convert likelihood score to risk level string."""
        if likelihood >= 80:
            return "CRITICAL"
        elif likelihood >= 60:
            return "HIGH"
        elif likelihood >= 40:
            return "MEDIUM"
        elif likelihood >= 20:
            return "LOW"
        return "MINIMAL"

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def analyze(self, description: str) -> dict[str, Any]:
        """Comprehensive scam analysis of a description or offer.

        Performs pattern matching, AI-powered analysis, and generates
        actionable safety advice and reporting guidance.

        Args:
            description: The text describing the offer, message, or situation.

        Returns:
            A comprehensive analysis with likelihood, patterns, flags,
            safety advice, and reporting information.
        """
        pattern_matches = self._match_patterns(description)
        likelihood = self._calculate_likelihood(pattern_matches)
        risk_level = self._risk_level(likelihood)

        # Build red flags
        red_flags: list[str] = []
        yellow_flags: list[str] = []

        for match in pattern_matches:
            if match["confidence"] == "HIGH":
                red_flags.append(match["description"])
            else:
                yellow_flags.append(match["description"])

        # AI-powered deep analysis for complex cases
        if likelihood >= 30:
            system = (
                "You are a fraud detection expert. Analyze the provided description "
                "for scam indicators and provide structured output."
            )
            user_prompt = (
                f"Analyze this for scam indicators:\n{description}\n\n"
                f"Already detected patterns: {[m['pattern'] for m in pattern_matches]}\n\n"
                "Respond ONLY with JSON in this structure:\n"
                "{\n"
                '  "additional_red_flags": ["string"],\n'
                '  "safety_advice": ["string"],\n'
                '  "what_to_do": ["string"],\n'
                '  "similar_known_scams": ["string"]\n'
                "}\n"
            )
            raw = self._chat(system, user_prompt, temperature=0.3)
            ai_data = self._safe_json(raw)
        else:
            ai_data = {}

        if isinstance(ai_data, dict) and "error" not in ai_data:
            additional_red = ai_data.get("additional_red_flags", [])
            red_flags.extend(rf for rf in additional_red if rf not in red_flags)
            safety_advice = ai_data.get("safety_advice", [])
            what_to_do = ai_data.get("what_to_do", [])
            similar_known = ai_data.get("similar_known_scams", [])
        else:
            safety_advice = []
            what_to_do = []
            similar_known = []

        # Ensure we always have content
        if not safety_advice:
            safety_advice = [
                "Do not respond to or engage with the sender",
                "Do not click any links or download attachments",
                "Do not provide personal or financial information",
                "Block the sender and report the communication",
                "If you shared any information, contact your bank immediately",
            ]

        if not what_to_do:
            if likelihood >= 60:
                what_to_do = [
                    "STOP all communication immediately",
                    "Do NOT send any money or personal information",
                    "Report to the FTC at ReportFraud.FTC.gov",
                    "If financial info was shared, contact your bank and freeze accounts",
                    "File a report at IC3.gov (FBI Internet Crime Complaint Center)",
                    "Warn friends and family about this scam",
                ]
            elif likelihood >= 40:
                what_to_do = [
                    "Be cautious and do not act on the offer",
                    "Research independently before proceeding",
                    "Verify the company/individual through official channels",
                    "Consult with a trusted advisor or authority",
                ]
            else:
                what_to_do = [
                    "Remain cautious but this appears relatively low risk",
                    "Still verify claims independently",
                    "Don't share personal information unnecessarily",
                ]

        if not similar_known:
            similar_known = [
                "Variations of advance-fee fraud",
                "Phishing and identity theft schemes",
                "Prize and lottery scams",
            ]

        # Reporting authorities
        report_to = [
            "FTC — ReportFraud.FTC.gov (for all types of fraud)",
            "FBI IC3 — IC3.gov (for internet crime)",
            "Your state Attorney General's office",
            "Local law enforcement",
        ]

        if any(m["pattern"] == "phishing" for m in pattern_matches):
            report_to.append("Anti-Phishing Working Group — reportphishing@apwg.org")
        if any(m["pattern"] in ("romance_scam",) for m in pattern_matches):
            report_to.append("FBI Romance Scam Reporting — IC3.gov")
        if any(m["pattern"] in ("investment", "pyramid_structure", "guaranteed_returns") for m in pattern_matches):
            report_to.append("SEC — SEC.gov/tcr (for securities fraud)")

        return {
            "scam_likelihood": likelihood,
            "risk_level": risk_level,
            "identified_patterns": pattern_matches,
            "red_flags": red_flags,
            "yellow_flags": yellow_flags,
            "safety_advice": safety_advice,
            "what_to_do": what_to_do,
            "report_to": report_to,
            "similar_known_scams": similar_known,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def check_url(self, url: str) -> dict[str, Any]:
        """Analyze a URL for scam indicators.

        Checks for suspicious TLDs, typosquatting, IP-based hosting,
        and other URL-based risk factors.

        Args:
            url: The URL to analyze.

        Returns:
            A dictionary with URL safety assessment.
        """
        url_lower = url.lower().strip()
        risk_score = 0
        indicators: list[str] = []
        warnings: list[str] = []

        # Check for suspicious TLDs
        for tld in self.SUSPICIOUS_TLDS:
            if tld in url_lower:
                risk_score += 25
                indicators.append(f"Uses suspicious TLD: {tld}")
                warnings.append(f"The domain ending '{tld}' is commonly used in scams")

        # Check for typosquatting
        for brand, typos in self.TYPO_PATTERNS.items():
            for typo in typos:
                if typo in url_lower:
                    risk_score += 30
                    indicators.append(f"Possible typosquatting of '{brand}': contains '{typo}'")
                    warnings.append(f"This URL may be impersonating {brand}")

        # Check for IP-based URLs
        if re.search(r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", url_lower):
            risk_score += 20
            indicators.append("Uses IP address instead of domain name")
            warnings.append("Legitimate sites use domain names, not raw IP addresses")

        # Check for excessive subdomains
        domain_part = url_lower.replace("https://", "").replace("http://", "").split("/")[0]
        subdomain_count = domain_part.count(".") - 1
        if subdomain_count > 2:
            risk_score += 15
            indicators.append(f"Excessive subdomains: {subdomain_count}")
            warnings.append("Many subdomains can indicate a malicious site")

        # Check for URL shorteners
        shorteners = {"bit.ly", "tinyurl", "t.co", "goo.gl", "ow.ly", "short.link"}
        for short in shorteners:
            if short in url_lower:
                risk_score += 10
                indicators.append(f"Uses URL shortener: {short}")
                warnings.append("URL shorteners hide the true destination — be cautious")

        # Check for @ symbol in URL (phishing trick)
        if "@" in url_lower.split("/")[2] if len(url_lower.split("/")) > 2 else "@" in url_lower:
            risk_score += 35
            indicators.append("Contains @ symbol — classic phishing technique")
            warnings.append("The @ symbol in URLs redirects to a different site than it appears")

        # Check for mixed scripts (homograph attack)
        if any(ord(c) > 127 for c in url):
            risk_score += 25
            indicators.append("Contains non-ASCII characters — possible homograph attack")
            warnings.append("Special characters may make this URL look like a legitimate site")

        # Check for excessive length
        if len(url) > 200:
            risk_score += 5
            indicators.append(f"Unusually long URL: {len(url)} characters")

        # Check for http (not https)
        if url_lower.startswith("http://") and not url_lower.startswith("https://"):
            risk_score += 10
            indicators.append("Uses unencrypted HTTP connection")
            warnings.append("Data transmitted to this site is not encrypted")

        # Determine risk level
        risk_score = min(100, risk_score)
        if risk_score >= 70:
            risk_level = "CRITICAL"
        elif risk_score >= 50:
            risk_level = "HIGH"
        elif risk_score >= 30:
            risk_level = "MEDIUM"
        elif risk_score >= 10:
            risk_level = "LOW"
        else:
            risk_level = "MINIMAL"

        return {
            "url": url,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "indicators": indicators,
            "warnings": warnings,
            "is_safe": risk_score < 30,
            "recommendations": [
                "Do not visit this URL" if risk_score >= 50 else "Exercise caution if visiting",
                "Check the domain carefully for typosquatting",
                "Use VirusTotal.com to scan the URL",
                "Never enter passwords or personal info on suspicious sites",
                "Keep your browser and antivirus up to date",
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def check_message(self, message: str, context: str = "general") -> dict[str, Any]:
        """Analyze a message (email, SMS, DM) for scam indicators.

        Args:
            message: The message text to analyze.
            context: Context type — ``"general"``, ``"email"``, ``"sms"``,
                ``"social_media"``, ``"phone"``.

        Returns:
            A message safety analysis with pattern matches and advice.
        """
        pattern_matches = self._match_patterns(message)
        likelihood = self._calculate_likelihood(pattern_matches)
        risk_level = self._risk_level(likelihood)

        # Context-specific checks
        context_indicators: list[str] = []

        if context == "email":
            # Check for spoofing indicators
            if re.search(r"from:\s*[^<]*<[^@]+@[^>]+>", message.lower()):
                context_indicators.append("Check sender email domain carefully")
            if "reply-to:" in message.lower() and "from:" in message.lower():
                context_indicators.append("Reply-to address may differ from sender")

        elif context == "sms":
            # SMS-specific patterns
            if re.search(r"https?://\S{20,}", message):
                context_indicators.append("Contains long link — common in SMS phishing")
            if re.search(r"\b\d{5,6}\b", message):
                context_indicators.append("Contains verification code request — possible scam")

        elif context == "social_media":
            if re.search(r"\b(?:dm|message)\b.*\b(?:won|selected|prize)\b", message.lower()):
                context_indicators.append("Social media prize scams are very common")

        # Build flags
        red_flags = [
            m["description"] for m in pattern_matches if m["confidence"] == "HIGH"
        ]
        yellow_flags = [
            m["description"] for m in pattern_matches if m["confidence"] != "HIGH"
        ]

        # Add context-specific advice
        safety_advice = [
            "Do not click any links in the message",
            "Do not reply to the message",
            "Do not download any attachments",
            "Do not provide personal information",
            "Block the sender",
        ]

        if context == "email":
            safety_advice.extend([
                "Check the sender's full email address (not just display name)",
                "Hover over links to see the true destination",
                "Forward phishing emails to reportphishing@apwg.org",
            ])
        elif context == "sms":
            safety_advice.extend([
                "Forward spam texts to SPAM (7726)",
                "Delete the message without responding",
            ])

        what_to_do = []
        if likelihood >= 60:
            what_to_do = [
                "DELETE the message immediately",
                "BLOCK the sender",
                "REPORT to platform/provider",
                "If you clicked a link, change passwords immediately",
                "If you shared info, contact your bank",
            ]
        elif likelihood >= 30:
            what_to_do = [
                "Do not engage with the message",
                "Verify through official channels if it claims to be from a known entity",
                "Report if it seems suspicious",
            ]
        else:
            what_to_do = [
                "Exercise normal caution",
                "Verify independently if the message requests action",
            ]

        return {
            "message_snippet": message[:200] + "..." if len(message) > 200 else message,
            "context": context,
            "scam_likelihood": likelihood,
            "risk_level": risk_level,
            "identified_patterns": pattern_matches,
            "red_flags": red_flags,
            "yellow_flags": yellow_flags,
            "context_indicators": context_indicators,
            "safety_advice": safety_advice,
            "what_to_do": what_to_do,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_protection_tips(self, category: str = "general") -> str:
        """Return scam protection advice by category.

        Args:
            category: One of ``"general"``, ``"online_shopping"``,
                ``"investments"``, ``"dating"``, ``"employment"``,
                ``"tech_support"``, ``"lottery"``, ``"real_estate"``,
                ``"cryptocurrency"``.

        Returns:
            Markdown-formatted protection tips string.
        """
        category = category.lower().strip()
        return self.PROTECTION_TIPS.get(
            category,
            self.PROTECTION_TIPS["general"],
        )

    def report_scam(self, description: str, scam_type: str = "unknown") -> None:
        """Save a scam report to the database for pattern learning.

        Args:
            description: The scam description.
            scam_type: Categorization of the scam type.
        """
        if self.db is None:
            logger.warning("Cannot report scam: no database connection")
            return

        try:
            # Analyze first to extract patterns
            analysis = self.analyze(description)
            patterns_json = json.dumps([m["pattern"] for m in analysis["identified_patterns"]])

            self.db.execute(
                """
                INSERT INTO scam_reports
                    (description, scam_type, likelihood, risk_level,
                     patterns_detected, reported_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    description,
                    scam_type,
                    analysis["scam_likelihood"],
                    analysis["risk_level"],
                    patterns_json,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            self.db.commit()
            logger.info("Scam report saved: type=%s, likelihood=%d",
                        scam_type, analysis["scam_likelihood"])
        except Exception as exc:
            logger.error("Failed to save scam report: %s", exc)

    def get_statistics(self) -> dict[str, Any]:
        """Return scam statistics from the database.

        Returns:
            A dictionary with aggregate statistics, or empty stats if
            no database is connected.
        """
        if self.db is None:
            return {
                "status": "no_database",
                "message": "No database connection available for statistics.",
                "total_reports": 0,
                "by_risk_level": {},
                "by_scam_type": {},
                "average_likelihood": 0,
                "recent_trends": [],
            }

        try:
            total = self.db.execute(
                "SELECT COUNT(*) FROM scam_reports"
            ).fetchone()[0]

            risk_levels = self.db.execute(
                "SELECT risk_level, COUNT(*) FROM scam_reports GROUP BY risk_level"
            ).fetchall()

            scam_types = self.db.execute(
                "SELECT scam_type, COUNT(*) FROM scam_reports GROUP BY scam_type"
            ).fetchall()

            avg_likelihood = self.db.execute(
                "SELECT AVG(likelihood) FROM scam_reports"
            ).fetchone()[0] or 0

            recent = self.db.execute(
                """
                SELECT scam_type, COUNT(*) as count,
                       AVG(likelihood) as avg_likelihood
                FROM scam_reports
                WHERE reported_at >= datetime('now', '-30 days')
                GROUP BY scam_type
                ORDER BY count DESC
                LIMIT 10
                """
            ).fetchall()

            return {
                "status": "ok",
                "total_reports": total,
                "by_risk_level": {row[0]: row[1] for row in risk_levels},
                "by_scam_type": {row[0]: row[1] for row in scam_types},
                "average_likelihood": round(avg_likelihood, 1),
                "recent_trends": [
                    {
                        "scam_type": row[0],
                        "count": row[1],
                        "avg_likelihood": round(row[2], 1),
                    }
                    for row in recent
                ],
            }
        except Exception as exc:
            logger.error("Failed to retrieve statistics: %s", exc)
            return {
                "status": "error",
                "message": str(exc),
                "total_reports": 0,
                "by_risk_level": {},
                "by_scam_type": {},
                "average_likelihood": 0,
                "recent_trends": [],
            }
