"""
OMEGA-LUQI Boot-Time Production Security Guards

In production mode (LUQI_ENV=production) the engine REFUSES TO START when:
  - LUQI_ADMIN_SECRET is unset or still the template default
  - JWT_SECRET_SIGNING_KEY is unset or still the template default
  - PAYSTACK_SECRET_KEY is a test key (sk_test_) - live settlements must not
    run against mock verification

Silent insecurity is how breaches happen; a hard refusal is the only
honest default. Development mode is unaffected.
"""
import os

DEFAULT_ADMIN_SECRET = "SuperSecretAdminKey123"
DEFAULT_JWT_SECRET = "SovereignAfricaCoreAuthSecretKey2026_ChangeMe!"


def production_guard_violations() -> list:
    if os.getenv("LUQI_ENV", "development").lower() != "production":
        return []

    violations = []
    admin = os.getenv("LUQI_ADMIN_SECRET", "")
    if not admin or admin == DEFAULT_ADMIN_SECRET:
        violations.append("LUQI_ADMIN_SECRET is unset or still the template default")

    jwt_secret = os.getenv("JWT_SECRET_SIGNING_KEY", "")
    if not jwt_secret or jwt_secret == DEFAULT_JWT_SECRET:
        violations.append("JWT_SECRET_SIGNING_KEY is unset or still the template default")

    paystack = os.getenv("PAYSTACK_SECRET_KEY", "")
    if paystack.startswith("sk_test_"):
        violations.append("PAYSTACK_SECRET_KEY is a test key (sk_test_) - live settlement refused")

    return violations


def enforce_production_guards() -> None:
    violations = production_guard_violations()
    if violations:
        raise RuntimeError(
            "PRODUCTION BOOT REFUSED - resolve before starting:\n  - " + "\n  - ".join(violations)
        )
