# Security Policy

## The model in one paragraph
Every secret lives in `.env` only; the engine refuses to boot in production
with template defaults; every payload is PII-scrubbed before leaving the VPC;
every sensitive action halts at the 30% Human Gate (payments, filings, infra);
every admin surface is behind `X-Luqi-Admin-Auth`; automation endpoints pass
an SSRF guard; webhooks are HMAC-verified; the database enforces FORCE RLS by
country. There is no simulated-success path anywhere in the engine.

## Layers
- Boot guards (`core/security_guards.py`): production refuses default secrets/test keys.
- Auth: fail-closed JWT (`core/auth.py`), pbkdf2 passwords, Redis revocation, rate limits.
- Gate: 30% human intervention with audit trail (hashed operator identity, size-capped).
- Egress: PII scrub on every external call; fixed-host allowlists; SSRF guard.
- Data: AES-256-GCM backups, FORCE RLS, unique wallet references (idempotency).
- Edge: nginx TLS 1.3, rate zones, hardened headers.

## Reporting a vulnerability
Do NOT open a public issue for security bugs. Email the maintainers via the
contact in the repository profile. We commit to acknowledgment within 72 hours.
Rotate any secret you believe exposed - never paste secrets into issues or chats.
