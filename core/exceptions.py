import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        detail = response.data
        if isinstance(detail, dict) and "detail" in detail:
            message = str(detail["detail"])
        elif isinstance(detail, list):
            message = str(detail[0]) if detail else "Error"
        else:
            message = str(detail)

        logger.warning(
            "api_exception",
            extra={"exc_type": type(exc).__name__, "status_code": response.status_code, "detail": message},
        )

        response.data = {
            "status_code": response.status_code,
            "message": message,
            "error": {},
        }
        return response

    logger.exception("unhandled_drf_exception", exc_info=exc)
    return Response(
        {
            "status_code": 500,
            "message": "An unexpected error occurred.",
            "error": {},
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
