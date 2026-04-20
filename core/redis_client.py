import logging

import redis
from django.conf import settings

logger = logging.getLogger(__name__)

_pool = None


def get_redis_pool():
    global _pool
    if _pool is None:
        _pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=20,
            decode_responses=True,
        )
    return _pool


def get_redis():
    return redis.Redis(connection_pool=get_redis_pool())
