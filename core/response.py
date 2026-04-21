from typing import Optional

from rest_framework.response import Response


def success_response(message: str, data=None, status: int = 200) -> Response:
    return Response(
        {
            "status_code": status,
            "message": message,
            "data": data,
        },
        status=status,
    )


def error_response(message: str, status: int, error: Optional[dict] = None) -> Response:
    body = {
        "status_code": status,
        "message": message,
        "error": error or {},
    }
    return Response(body, status=status)
