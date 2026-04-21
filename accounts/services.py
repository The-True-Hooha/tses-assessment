import hashlib
import hmac
import logging
import secrets
import string
import time
from typing import cast

from django.conf import settings
from django.contrib.auth import get_user_model

from core.rate_limiter import check_rate_limit_fixed, check_rate_limit_rolling
from core.redis_client import get_redis

logger = logging.getLogger(__name__)

User = get_user_model()


def _key(namespace: str, identifier: str) -> str:
    return f"tses:{namespace}:{identifier}"


def generate_otp() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(6))


def hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()


def store_otp(email: str, otp: str) -> None:
    r = get_redis()
    pipe = r.pipeline()
    pipe.setex(_key("otp", email), settings.OTP_TTL_SECONDS, hash_otp(otp))
    pipe.delete(_key("fails", email))
    pipe.execute()
    logger.info("otp_stored", extra={"email": email})


def verify_otp(email: str, otp: str) -> bool:
    r = get_redis()
    stored = cast(str | None, r.get(_key("otp", email)))
    if stored is None:
        return False
    valid = hmac.compare_digest(stored, hash_otp(otp))
    if valid:
        r.delete(_key("otp", email))
    return valid


def check_email_rate_limit(email: str) -> tuple[bool, int]:
    return check_rate_limit_rolling(
        key=_key("rl:email", email),
        window=settings.OTP_EMAIL_WINDOW_SECONDS,
        limit=settings.OTP_MAX_REQUESTS_PER_EMAIL,
    )


def check_ip_rate_limit(ip: str) -> tuple[bool, int]:
    """Sliding window — max OTP_MAX_REQUESTS_PER_IP per OTP_IP_WINDOW_SECONDS."""
    return check_rate_limit_rolling(
        key=_key("rl:ip_otp", ip),
        window=settings.OTP_IP_WINDOW_SECONDS,
        limit=settings.OTP_MAX_REQUESTS_PER_IP,
    )


def check_global_ip_rate_limit(ip: str) -> tuple[bool, int]:
    """Fixed window — GLOBAL_RATE_LIMIT_PER_IP req per GLOBAL_RATE_LIMIT_WINDOW_SECONDS."""
    window = settings.GLOBAL_RATE_LIMIT_WINDOW_SECONDS
    bucket = int(time.time() // window)
    return check_rate_limit_fixed(
        key=_key(f"rl:global:{bucket}", ip),
        limit=settings.GLOBAL_RATE_LIMIT_PER_IP,
        window=window,
    )

def is_locked_out(email: str) -> tuple[bool, int]:
    r = get_redis()
    ttl = cast(int, r.ttl(_key("lockout", email)))
    if ttl > 0:
        return True, ttl
    return False, 0


def record_failed_attempt(email: str) -> tuple[bool, int]:
    """
    Atomic INCR + EXPIRE. Triggers lockout when max attempts reached.
    Returns (is_now_locked, unlock_eta_seconds).
    """
    r = get_redis()
    fail_key = _key("fails", email)
    lockout_key = _key("lockout", email)

    pipe = r.pipeline()
    pipe.incr(fail_key)
    pipe.expire(fail_key, settings.OTP_LOCKOUT_WINDOW_SECONDS)
    count = cast(int, pipe.execute()[0])

    if count >= settings.OTP_MAX_FAILED_ATTEMPTS:
        r.setex(lockout_key, settings.OTP_LOCKOUT_WINDOW_SECONDS, "1")
        r.delete(fail_key)
        return True, settings.OTP_LOCKOUT_WINDOW_SECONDS

    return False, 0


def clear_failed_attempts(email: str) -> None:
    r = get_redis()
    r.delete(_key("fails", email))
    r.delete(_key("lockout", email))

def get_or_create_user(email: str):
    user, created = User.objects.get_or_create(
        email=email,
        defaults={"username": email, "is_active": True},
    )
    return user, created
