from django.db import models


class AuditEvent(models.TextChoices):
    OTP_REQUESTED = "OTP_REQUESTED", "OTP Requested"
    OTP_VERIFIED = "OTP_VERIFIED", "OTP Verified"
    OTP_FAILED = "OTP_FAILED", "OTP Failed"
    OTP_LOCKED = "OTP_LOCKED", "OTP Locked"


class AuditLog(models.Model):
    event = models.CharField(
        max_length=50,
        choices=AuditEvent.choices,
        db_index=True,
    )
    email = models.EmailField(db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "event"], name="audit_email_event_idx"),
            models.Index(fields=["created_at"], name="audit_created_at_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.event} | {self.email} | {self.created_at}"
