from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    """
    Record important actions performed in CareFlow.

    Stores who performed an action, what happened,
    which object was affected, and when it happened.
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events"
    )

    action = models.CharField(
        max_length=100,
        db_index=True
    )

    target_type = models.CharField(
        max_length=100
    )

    target_id = models.PositiveBigIntegerField(
        null=True,
        blank=True
    )

    metadata = models.JSONField(
        default=dict,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return (
            f"{self.action} - "
            f"{self.target_type} #{self.target_id}"
        )