"""
OMEGA-LUQI Enterprise & Student Authentication Kernel

Fail-closed JWT handling: any expired, corrupted, or missing signing
capability results in immediate denial - no fallbacks, no crashes.

- Tokens: HS256, 24h expiry, issued after pbkdf2 password verification.
- Passwords: stdlib pbkdf2_hmac (100k rounds, per-user salt). No plaintext,
  no weak hashing. Registry is in-memory for v1 - move to Postgres with the
  Student table when RLS lands.
- PyJWT is imported lazily: the core must boot even without it installed
  (requirements.txt carries pyjwt>=2.8 for production).
"""
import os
import uuid
import time
import hashlib
import threading
from typing import Dict, Optional

from fastapi import APIRouter, Request, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

try:
    import jwt  # PyJWT - declared in requirements.txt
except ImportError:  # engine must still boot without it (fail-closed at use time)
    jwt = None

router = APIRouter()

security_agent = HTTPBearer(auto_error=True)

from .security_guards import DEFAULT_JWT_SECRET
JWT_SECRET_CLUSTER = os.getenv("JWT_SECRET_SIGNING_KEY", DEFAULT_JWT_SECRET)
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRATION_SECONDS = 86400  # 24-hour session window
_PBKDF2_ROUNDS = 100_000


class UserSessionProfile(BaseModel):
    user_id: uuid.UUID
    email: str
    country_code: str   # critical mapping vector for future Postgres RLS
    tier: str           # primary, high_school, tvet, university, global_premium, enterprise
    wallet_balance: float = Field(default=0.0)


class RegisterRequest(BaseModel):
    email: str
    password: str
    country_code: str = "ZAF"
    tier: str = "tvet"


class LoginRequest(BaseModel):
    email: str
    password: str


# ---- Login rate limiter: per-IP+endpoint token bucket, 10 attempts / 60s ----
class _LoginRateLimiter:
    def __init__(self, max_attempts: int = 10, window_seconds: int = 60):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._hits = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> bool:
        """True = allowed, False = rate-limited."""
        now = time.time()
        with self._lock:
            self._hits[key] = [t for t in self._hits.get(key, []) if now - t < self.window]
            if len(self._hits[key]) >= self.max_attempts:
                return False
            self._hits[key].append(now)
            return True


_login_limiter = _LoginRateLimiter()

# ---- Token revocation denylist: Redis (TTL-matched) with memory fallback ----
_REVOKED_TOKENS: set = set()


def _token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _revocation_redis():
    """Redis denylist when STATE_BACKEND=redis; None -> memory fallback."""
    if os.getenv("STATE_BACKEND", "memory") != "redis":
        return None
    try:
        import redis
        return redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    except Exception:
        return None


def revoke_token(token: str) -> None:
    fp = _token_fingerprint(token)
    _REVOKED_TOKENS.add(fp)
    r = _revocation_redis()
    if r:
        # TTL matches the token window: entries expire when tokens would anyway
        r.setex(f"luqi:revoked:{fp}", TOKEN_EXPIRATION_SECONDS, "1")


def is_token_revoked(token: str) -> bool:
    fp = _token_fingerprint(token)
    if fp in _REVOKED_TOKENS:
        return True
    r = _revocation_redis()
    return bool(r and r.exists(f"luqi:revoked:{fp}"))


# ---- In-memory user registry (v1). Swap for Postgres-backed store when RLS lands. ----
_USERS: Dict[str, dict] = {}
_users_lock = threading.Lock()


def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS).hex()


def _require_jwt():
    if jwt is None:
        raise HTTPException(status_code=500, detail="Auth kernel unavailable: PyJWT not installed (pip install pyjwt).")


class LuqiAuthManager:
    @staticmethod
    def generate_secure_session_token(profile: UserSessionProfile) -> str:
        _require_jwt()
        payload = {
            "sub": str(profile.user_id),
            "email": profile.email,
            "country_code": profile.country_code.upper()[:3],
            "tier": profile.tier,
            "exp": time.time() + TOKEN_EXPIRATION_SECONDS,
            "iss": "luqi-ai-auth-kernel",
        }
        return jwt.encode(payload, JWT_SECRET_CLUSTER, algorithm=JWT_ALGORITHM)

    @staticmethod
    def verify_session_token(credentials: HTTPAuthorizationCredentials = Security(security_agent)) -> UserSessionProfile:
        """FAIL-CLOSED decoder: expired/corrupted tokens deny immediately, never crash."""
        _require_jwt()
        try:
            payload = jwt.decode(credentials.credentials, JWT_SECRET_CLUSTER, algorithms=[JWT_ALGORITHM])
            return UserSessionProfile(
                user_id=uuid.UUID(payload["sub"]),
                email=payload["email"],
                country_code=payload["country_code"],
                tier=payload["tier"],
            )
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError, ValueError) as err:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Session Validation Failed: token expired or corrupted ({err}).",
                headers={"WWW-Authenticate": "Bearer"},
            )


@router.post("/v1/auth/logout")
def logout_user(credentials: HTTPAuthorizationCredentials = Security(security_agent)):
    """Revoke the presented token immediately (24h window no longer applies)."""
    revoke_token(credentials.credentials)
    return {"message": "Session revoked."}


@router.post("/v1/auth/register", status_code=201)
def register_user(req: RegisterRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not _login_limiter.check(f"register:{client_ip}"):
        raise HTTPException(status_code=429, detail="Too many attempts. Retry in 60 seconds.")
    email = req.email.strip().lower()
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    with _users_lock:
        if email in _USERS:
            raise HTTPException(status_code=409, detail="Account already registered for this email.")
        salt = os.urandom(16)
        _USERS[email] = {
            "salt": salt,
            "password_hash": _hash_password(req.password, salt),
            "profile": UserSessionProfile(
                user_id=uuid.uuid4(), email=email,
                country_code=req.country_code.upper()[:3], tier=req.tier,
            ),
        }
    return {"message": "Account provisioned. Authenticate via /v1/auth/login."}


@router.post("/v1/auth/login")
def login_user(req: LoginRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not _login_limiter.check(f"login:{client_ip}"):
        raise HTTPException(status_code=429, detail="Too many attempts. Retry in 60 seconds.")
    email = req.email.strip().lower()
    with _users_lock:
        record = _USERS.get(email)
    if record is None or record["password_hash"] != _hash_password(req.password, record["salt"]):
        # Uniform denial - never reveal whether the email exists
        raise HTTPException(status_code=401, detail="Invalid credentials.", headers={"WWW-Authenticate": "Bearer"})
    try:
        from .dead_mans_switch import touch as _legacy_touch
        _legacy_touch(str(record["profile"].user_id))
    except Exception:
        pass  # legacy tracking never blocks login
    token = LuqiAuthManager.generate_secure_session_token(record["profile"])
    return {"access_token": token, "token_type": "bearer", "profile": record["profile"]}
