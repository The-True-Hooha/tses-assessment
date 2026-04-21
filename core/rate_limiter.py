import logging
import time
from functools import wraps
from typing import Callable, cast

from core.middleware import get_client_ip  # noqa: F401
from core.redis_client import get_redis
from core.response import error_response

logger = logging.getLogger(__name__)


_TRACK_REQUESTS_IN_ROLLING_WINDOW = """
local key          = KEYS[1]
local now          = tonumber(ARGV[1])
local window       = tonumber(ARGV[2])
local limit        = tonumber(ARGV[3])
local window_start = now - window

redis.call('ZREMRANGEBYSCORE', key, 0, window_start)

local count = redis.call('ZCARD', key)

if count >= limit then
    local oldest      = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry_after = window
    if #oldest > 0 then
        retry_after = math.ceil(window - (now - tonumber(oldest[2])))
    end
    if retry_after < 1 then retry_after = 1 end
    return {0, retry_after}
end

redis.call('ZADD', key, now, tostring(now))
redis.call('EXPIRE', key, window)
return {1, 0}
"""

_COUNT_REQUESTS_IN_FIXED_BUCKET = """
local key    = KEYS[1]
local limit  = tonumber(ARGV[1])
local window = tonumber(ARGV[2])

local count = redis.call('INCR', key)
if count == 1 then
    redis.call('EXPIRE', key, window)
end

if count > limit then
    local ttl = redis.call('TTL', key)
    if ttl < 1 then ttl = 1 end
    return {0, ttl}
end
return {1, 0}
"""



def check_rate_limit_rolling(key: str, window: int, limit: int) -> tuple[bool, int]:
    r = get_redis()
    result = cast(list, r.eval(_TRACK_REQUESTS_IN_ROLLING_WINDOW, 1, key, time.time(), window, limit))
    return bool(result[0]), int(result[1])


def check_rate_limit_fixed(key: str, limit: int, window: int) -> tuple[bool, int]:
    r = get_redis()
    result = cast(list, r.eval(_COUNT_REQUESTS_IN_FIXED_BUCKET, 1, key, limit, window))
    return bool(result[0]), int(result[1])


def throttle(
    key_func: Callable,
    limit: int,
    window: int,
    strategy: str = "rolling",
    scope: str = "route",
):
    """
    Per-route rate limit decorator for DRF class-based views.

    Usage:
        @throttle(key_func=lambda r: get_client_ip(r), limit=10, window=60, scope="otp_request")
        def post(self, request): ...

    Args:
        key_func: callable(request) → str, builds the unique identifier
        limit:    max requests allowed within the window
        window:   window duration in seconds
        strategy: "rolling" (sorted set, precise) or "fixed" (counter, lightweight)
        scope:    label used in the Redis key — keep it unique per route
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(view_or_self, request, *args, **kwargs):
            req = request if hasattr(request, "META") else view_or_self
            try:
                identifier = key_func(req)
                key = f"tses:rl:{scope}:{identifier}"

                if strategy == "rolling":
                    allowed, retry_after = check_rate_limit_rolling(key, window, limit)
                else:
                    allowed, retry_after = check_rate_limit_fixed(key, limit, window)

                if not allowed:
                    logger.warning(
                        "route_rate_limit_exceeded",
                        extra={"scope": scope, "identifier": identifier, "retry_after": retry_after},
                    )
                    resp = error_response(
                        message="Too many requests. Try again later.",
                        status=429,
                        error={"retry_after": retry_after},
                    )
                    resp["Retry-After"] = str(retry_after)
                    return resp

            except Exception:
                logger.warning("rate_limiter_redis_unavailable", extra={"scope": scope})

            return view_func(view_or_self, request, *args, **kwargs)
        return wrapper
    return decorator
