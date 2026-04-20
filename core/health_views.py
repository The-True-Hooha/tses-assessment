import logging

import redis
from django.conf import settings
from django.db import connection
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def health_check(request):
    checks = {}

    try:
        connection.ensure_connection()
        checks["database"] = "ok"
    except Exception as e:
        logger.error("health_db_check_failed", extra={"error": str(e)})
        checks["database"] = "error"

    try:
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        logger.error("health_redis_check_failed", extra={"error": str(e)})
        checks["redis"] = "error"

    all_ok = all(v == "ok" for v in checks.values())
    http_status = 200 if all_ok else 503

    return JsonResponse(
        {
            "status_code": http_status,
            "message": "ok" if all_ok else "degraded",
            "data": {"checks": checks},
        },
        status=http_status,
    )
