import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="accounts.send_otp_email",
    max_retries=3,
    default_retry_delay=5,
)
def send_otp_email(self, email: str, otp: str, correlation_id: str = None):
    try:
        logger.info(
            "send_otp_email_task_received",
            extra={"email": email, "correlation_id": correlation_id, "task_id": self.request.id},
        )
        print(f"\n{'='*52}")
        print(f"  OTP EMAIL")
        print(f"  To:            {email}")
        print(f"  Code:          {otp}")
        print(f"  Expires in:    5 minutes")
        print(f"  Correlation:   {correlation_id}")
        print(f"{'='*52}\n")
        logger.info(
            "send_otp_email_delivered",
            extra={"email": email, "correlation_id": correlation_id, "task_id": self.request.id},
        )
    except Exception as exc:
        logger.error(
            "send_otp_email_failed",
            extra={"email": email, "error": str(exc), "attempt": self.request.retries + 1},
        )
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    name="accounts.write_audit_log",
    max_retries=5,
)
def write_audit_log(
    self,
    event: str,
    email: str,
    ip: str,
    meta: dict = None,
    correlation_id: str = None,
):
    try:
        from audit.models import AuditLog

        logger.info(
            "write_audit_log_task_received",
            extra={"event": event, "email": email, "correlation_id": correlation_id, "task_id": self.request.id},
        )
        AuditLog.objects.create(
            event=event,
            email=email,
            ip_address=ip,
            metadata=meta or {},
        )
        logger.info(
            "audit_log_written",
            extra={"event": event, "email": email, "correlation_id": correlation_id},
        )
    except Exception as exc:
        logger.error(
            "write_audit_log_failed",
            extra={"event": event, "email": email, "error": str(exc), "attempt": self.request.retries + 1},
        )
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 10)
