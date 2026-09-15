# Luqi-AI Official System Launch Checklist

Verify every item before cutting traffic over to live public student accounts.

## 1. Identity & Secret Encryption
- [ ] No passwords, database strings, or API keys anywhere in the repository (grep the repo to prove it)
- [ ] All secrets live only in `/opt/luqi-core/.env` on the production host
- [ ] `.env` listed in `.gitignore`; rotate any key that ever appeared in git history

## 2. Biometric Voice Buffer Validation (POPIA / Kenya DPA)
- [ ] Student voice audio is processed only in volatile CPU memory
- [ ] Buffers are explicitly overwritten/released immediately after translation
- [ ] No raw voice audio is written to disk or persistent logs
- [ ] Consent notice shown to students on first voice interaction

## 3. Docker Ceiling Enforcement
- [ ] `MAX_SANDBOX_CONTAINERS` matches host RAM/CPU headroom (500 x 512MB = 256GB minimum RAM plan)
- [ ] Enforcement code actually reads the ceiling before spawning a sandbox (currently a config value only - implement the check in LabSandboxManager before launch)
- [ ] Per-container limits (0.5 CPU / 512MB) verified with a stress spawn test

## 4. Payment Route Handshakes
- [ ] Micro-transaction test passed on M-Pesa sandbox (Kenya/Tanzania routing)
- [ ] Micro-transaction test passed on PayFast and Ozow sandboxes (South Africa EFT)
- [ ] Micro-transaction test passed on Flutterwave/Paystack sandboxes (Nigeria/Ghana)
- [ ] Geo-detection routes each transaction to the correct regional gateway
- [ ] Every payment action still halts at the 30% gate in production mode

## 5. 30% Safety Valve Testing
- [ ] Forced unauthorized override (no admin header) returns 403 and the task stays locked
- [ ] 50-concurrent-payment stress result: zero completions without human release
- [ ] Rejected transactions cannot be re-approved (run `pytest -v test_orchestrator.py` on the production host)

## 6. Final Go/No-Go
- [ ] `/v1/health` returns operational from the public domain over HTTPS
- [ ] PWA installs on a low-end Android device and runs a lab offline after first load
- [ ] Journal/log retention configured; disk alarms set
- [ ] Rollback plan documented (previous systemd unit + git tag ready)
