import logging

from django.conf import settings
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts import services
from accounts.serializers import OTPRequestSerializer, OTPVerifySerializer
from accounts.tasks import send_otp_email, write_audit_log
from core.middleware import get_client_ip
from core.response import error_response, success_response

logger = logging.getLogger(__name__)


class OTPRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["auth"],
        summary="Request OTP",
        description=(
            "Sends a 6-digit OTP to the given email address. "
            "Rate limited: max 3 per email per 10 min, max 10 per IP per hour. "
            "OTP expires in 5 minutes."
        ),
        request=OTPRequestSerializer,
        responses={
            202: OpenApiResponse(
                description="OTP enqueued for delivery.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "status_code": 202,
                            "message": "OTP sent to email.",
                            "data": {"otp": "482910", "expires_in": 300},
                        },
                    )
                ],
            ),
            429: OpenApiResponse(
                description="Rate limit exceeded.",
                examples=[
                    OpenApiExample(
                        "Email Rate Limited",
                        value={
                            "status_code": 429,
                            "message": "Too many OTP requests for this email. Try again later.",
                            "error": {"retry_after": 120},
                        },
                    ),
                    OpenApiExample(
                        "IP Rate Limited",
                        value={
                            "status_code": 429,
                            "message": "Too many OTP requests from this IP. Try again later.",
                            "error": {"retry_after": 300},
                        },
                    ),
                ],
            ),
            503: OpenApiResponse(
                description="Redis unavailable.",
                examples=[
                    OpenApiExample(
                        "Service Unavailable",
                        value={
                            "status_code": 503,
                            "message": "Service temporarily unavailable.",
                            "error": {},
                        },
                    )
                ],
            ),
        },
    )
    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        ip = get_client_ip(request)
        correlation_id = getattr(request, "correlation_id", None)

        # Global IP rate limit
        try:
            allowed, retry_after = services.check_global_ip_rate_limit(ip)
            if not allowed:
                return error_response(
                    message="Too many requests. Slow down.",
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                    error={"retry_after": retry_after},
                ).headers.update({"Retry-After": str(retry_after)}) or error_response(
                    message="Too many requests. Slow down.",
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                    error={"retry_after": retry_after},
                )
        except Exception:
            logger.warning("redis_unavailable_global_rl", extra={"ip": ip})
            return error_response("Service temporarily unavailable.", status=503)

        # Email rate limit
        try:
            allowed, retry_after = services.check_email_rate_limit(email)
            if not allowed:
                logger.warning("email_rate_limit_exceeded", extra={"email": email})
                resp = error_response(
                    message="Too many OTP requests for this email. Try again later.",
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                    error={"retry_after": retry_after},
                )
                resp["Retry-After"] = str(retry_after)
                return resp
        except Exception:
            logger.warning("redis_unavailable_email_rl", extra={"email": email})
            return error_response("Service temporarily unavailable.", status=503)

        # IP OTP rate limit
        try:
            allowed, retry_after = services.check_ip_rate_limit(ip)
            if not allowed:
                logger.warning("ip_rate_limit_exceeded", extra={"ip": ip})
                resp = error_response(
                    message="Too many OTP requests from this IP. Try again later.",
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                    error={"retry_after": retry_after},
                )
                resp["Retry-After"] = str(retry_after)
                return resp
        except Exception:
            logger.warning("redis_unavailable_ip_rl", extra={"ip": ip})
            return error_response("Service temporarily unavailable.", status=503)

        # Generate + store OTP
        try:
            otp = services.generate_otp()
            services.store_otp(email, otp)
        except Exception:
            logger.error("redis_unavailable_store_otp", extra={"email": email})
            return error_response("Service temporarily unavailable.", status=503)

        # Enqueue async tasks — non-blocking
        logger.info("otp_task_enqueuing", extra={"email": email})
        send_otp_email.delay(email, otp, correlation_id=correlation_id)
        logger.info("otp_email_task_enqueued", extra={"email": email})
        write_audit_log.delay(
            event="OTP_REQUESTED",
            email=email,
            ip=ip,
            meta={"correlation_id": correlation_id},
            correlation_id=correlation_id,
        )
        logger.info("audit_log_task_enqueued", extra={"email": email, "event": "OTP_REQUESTED"})

        logger.info("otp_requested", extra={"email": email})
        return success_response(
            message="OTP sent to email.",
            data={"otp": otp, "expires_in": settings.OTP_TTL_SECONDS},
            status=status.HTTP_202_ACCEPTED,
        )


class OTPVerifyView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["auth"],
        summary="Verify OTP",
        description=(
            "Verifies the OTP against Redis. On success issues JWT access and refresh tokens. "
            "Max 5 failed attempts per 15 minutes before lockout."
        ),
        request=OTPVerifySerializer,
        responses={
            200: OpenApiResponse(
                description="OTP verified. JWT tokens returned.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "status_code": 200,
                            "message": "OTP verified.",
                            "data": {
                                "access": "eyJ...",
                                "refresh": "eyJ...",
                                "token_type": "Bearer",
                            },
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Invalid or expired OTP.",
                examples=[
                    OpenApiExample(
                        "Invalid OTP",
                        value={
                            "status_code": 400,
                            "message": "Invalid or expired OTP.",
                            "error": {},
                        },
                    )
                ],
            ),
            423: OpenApiResponse(
                description="Account locked due to too many failed attempts.",
                examples=[
                    OpenApiExample(
                        "Locked Out",
                        value={
                            "status_code": 423,
                            "message": "Too many failed attempts. Try again in 900 seconds.",
                            "error": {"retry_after": 900},
                        },
                    )
                ],
            ),
            503: OpenApiResponse(
                description="Redis unavailable.",
                examples=[
                    OpenApiExample(
                        "Service Unavailable",
                        value={
                            "status_code": 503,
                            "message": "Service temporarily unavailable.",
                            "error": {},
                        },
                    )
                ],
            ),
        },
    )
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]
        ip = get_client_ip(request)
        correlation_id = getattr(request, "correlation_id", None)

        # Lockout check — fail closed if Redis down
        try:
            locked, unlock_eta = services.is_locked_out(email)
            if locked:
                logger.warning("otp_verify_blocked_lockout", extra={"email": email})
                write_audit_log.delay(
                    event="OTP_LOCKED",
                    email=email,
                    ip=ip,
                    meta={"unlock_eta": unlock_eta, "correlation_id": correlation_id},
                    correlation_id=correlation_id,
                )
                resp = error_response(
                    message=f"Too many failed attempts. Try again in {unlock_eta} seconds.",
                    status=status.HTTP_423_LOCKED,
                    error={"retry_after": unlock_eta},
                )
                resp["Retry-After"] = str(unlock_eta)
                return resp
        except Exception:
            logger.error("redis_unavailable_lockout_check", extra={"email": email})
            return error_response("Service temporarily unavailable.", status=503)

        # Verify OTP — fail closed if Redis down
        try:
            valid = services.verify_otp(email, otp)
        except Exception:
            logger.error("redis_unavailable_otp_verify", extra={"email": email})
            return error_response("Service temporarily unavailable.", status=503)

        if not valid:
            try:
                is_now_locked, unlock_eta = services.record_failed_attempt(email)
            except Exception:
                is_now_locked, unlock_eta = False, 0

            write_audit_log.delay(
                event="OTP_FAILED",
                email=email,
                ip=ip,
                meta={"locked": is_now_locked, "correlation_id": correlation_id},
                correlation_id=correlation_id,
            )

            if is_now_locked:
                logger.warning("otp_verify_lockout_triggered", extra={"email": email})
                resp = error_response(
                    message=f"Too many failed attempts. Try again in {unlock_eta} seconds.",
                    status=status.HTTP_423_LOCKED,
                    error={"retry_after": unlock_eta},
                )
                resp["Retry-After"] = str(unlock_eta)
                return resp

            logger.info("otp_verify_failed", extra={"email": email})
            return error_response(
                message="Invalid or expired OTP.",
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Success
        try:
            services.clear_failed_attempts(email)
            user, _ = services.get_or_create_user(email)
        except Exception as exc:
            logger.error("otp_verify_user_create_failed", extra={"email": email, "error": str(exc)})
            return error_response("Failed to complete authentication.", status=500)

        refresh = RefreshToken.for_user(user)
        write_audit_log.delay(
            event="OTP_VERIFIED",
            email=email,
            ip=ip,
            meta={"user_id": user.id, "correlation_id": correlation_id},
            correlation_id=correlation_id,
        )

        logger.info("otp_verify_success", extra={"email": email, "user_id": user.id})
        return success_response(
            message="OTP verified.",
            data={
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "token_type": "Bearer",
            },
        )
