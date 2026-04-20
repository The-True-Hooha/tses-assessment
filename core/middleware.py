import logging
import time

import uuid6

from core.logging_formatters import clear_request_context, set_request_context

logger = logging.getLogger(__name__)


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

    if x_forwarded_for:
        ips = [ip.strip() for ip in x_forwarded_for.split(",")]
        return ips[0]
    return request.META.get("REMOTE_ADDR") or None


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.META.get("HTTP_X_REQUEST_ID") or str(uuid6.uuid7())
        correlation_id = request.META.get("HTTP_X_CORRELATION_ID") or request_id

        request.request_id = request_id
        request.correlation_id = correlation_id

        response = self.get_response(request)

        response["X-Request-ID"] = request_id
        response["X-Correlation-ID"] = correlation_id
        return response


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = get_client_ip(request)
        request_id = getattr(request, "request_id", str(uuid6.uuid7()))
        correlation_id = getattr(request, "correlation_id", request_id)
        user_id = None
        if hasattr(request, "user") and request.user.is_authenticated:
            user_id = request.user.id

        set_request_context(
            request_id=request_id,
            correlation_id=correlation_id,
            user_id=user_id,
            ip=ip or "::unknown::",
            endpoint=request.path,
        )

        start = time.monotonic()
        logger.info(
            "request_started",
            extra={"method": request.method, "path": request.path},
        )

        response = None
        try:
            response = self.get_response(request)
        except Exception:
            logger.exception("unhandled_exception")
            raise
        finally:
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            status = response.status_code if response is not None else 500
            logger.info(
                "request_finished",
                extra={
                    "method": request.method,
                    "path": request.path,
                    "status_code": status,
                    "latency_ms": latency_ms,
                },
            )
            clear_request_context()

        return response
