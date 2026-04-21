import logging

from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView

from audit.models import AuditLog
from audit.serializers import AuditLogSerializer

logger = logging.getLogger(__name__)


class AuditLogPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AuditLogListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AuditLogSerializer
    pagination_class = AuditLogPagination

    @extend_schema(
        tags=["audit"],
        summary="List audit logs",
        description=(
            "Returns a paginated list of audit log entries, newest first. "
            "Requires JWT authentication. Supports filtering by email, event type, and date range."
        ),
        parameters=[
            OpenApiParameter(
                "email",
                description="Filter by email address (case-insensitive).",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                "event",
                description="Filter by event type. One of: OTP_REQUESTED, OTP_VERIFIED, OTP_FAILED, OTP_LOCKED.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                "from_date",
                description="Return entries created on or after this datetime. Example: 2026-04-21T00:00:00Z",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                "to_date",
                description="Return entries created on or before this datetime. Example: 2026-04-21T23:59:59Z",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                "page",
                description="Page number.",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                "page_size",
                description="Number of results per page (max 100).",
                required=False,
                type=int,
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Paginated list of audit logs, newest first.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "count": 2,
                            "next": None,
                            "previous": None,
                            "results": [
                                {
                                    "id": "019daf48-b53f-7808-8d4e-fcd579da62d2",
                                    "event": "OTP_VERIFIED",
                                    "email": "user@example.com",
                                    "ip_address": "127.0.0.1",
                                    "metadata": {"user_id": "019daf48-0001-7000-0000-000000000001"},
                                    "created_at": "2026-04-21T10:04:41Z",
                                },
                                {
                                    "id": "019daf48-b53f-7808-8d4e-fcd579da62d1",
                                    "event": "OTP_REQUESTED",
                                    "email": "user@example.com",
                                    "ip_address": "127.0.0.1",
                                    "metadata": {},
                                    "created_at": "2026-04-21T10:04:38Z",
                                },
                            ],
                        },
                    )
                ],
            ),
            401: OpenApiResponse(
                description="Authentication required.",
                examples=[
                    OpenApiExample(
                        "Unauthorized",
                        value={
                            "status_code": 401,
                            "message": "Authentication credentials were not provided.",
                            "error": {},
                        },
                    )
                ],
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        qs = AuditLog.objects.all()

        email = self.request.query_params.get("email")
        event = self.request.query_params.get("event")
        from_date = self.request.query_params.get("from_date")
        to_date = self.request.query_params.get("to_date")

        if email:
            qs = qs.filter(email__iexact=email)
        if event:
            qs = qs.filter(event__iexact=event)
        if from_date:
            qs = qs.filter(created_at__gte=from_date)
        if to_date:
            qs = qs.filter(created_at__lte=to_date)

        return qs.order_by("-created_at")
