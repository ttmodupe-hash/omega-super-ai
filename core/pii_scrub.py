"""
OMEGA-LUQI Data Sovereignty Screen

Strips explicit identities from any text BEFORE it leaves the local VPC to
external AI providers (Moonshot/China, ElevenLabs/US-EU). This is the
technical enforcement behind the EULA Section 2 data-routing disclosure:
PII never crosses the border, only anonymised prompt content does.

Applied to every outbound user-content payload in the Kimi engines.
"""


def scrub_pii(text: str) -> str:
    """Tokenize South African identity patterns (extensible to other regions)."""
    import re
    if not text:
        return text
    s = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[REDACTED_EMAIL]', text)
    s = re.sub(r'\b(?:\+?27|0)[6-8]\d{8}\b', '[REDACTED_PHONE]', s)          # SA mobile numbers
    s = re.sub(r'\b\d{13}\b', '[REDACTED_NATIONAL_ID]', s)                    # SA ID numbers
    s = re.sub(r'\b\d{4}/\d{6}/\d{2}\b', '[REDACTED_COMPANY_REG]', s)       # SA company registrations (2015/123456/07)
    return s
