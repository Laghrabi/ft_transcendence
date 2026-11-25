from django.conf import settings
from django.db import models
from django.utils import timezone


class Priority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    URGENT = "urgent", "Urgent"


class Case(models.Model):

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    title = models.CharField(max_length=200)

    description = models.TextField(
        blank=True,
        default=""
    )

    case_type = models.CharField(
        max_length=100,
        db_index=True
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        db_index=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True
    )

    lead_department = models.ForeignKey(
        "organizations.Department",
        on_delete=models.PROTECT,
        related_name="lead_cases"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_cases"
    )

    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="closed_cases"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"Case #{self.pk}: {self.title}"


class Task(models.Model):

    class Status(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In Progress"
        BLOCKED = "blocked", "Blocked"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    ACTIVE_STATUSES = (
        Status.ASSIGNED,
        Status.IN_PROGRESS,
        Status.BLOCKED
    )

    case = models.ForeignKey(
        Case,
        on_delete=models.PROTECT,
        related_name="tasks"
    )

    title = models.CharField(max_length=200)

    description = models.TextField(
        blank=True,
        default=""
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ASSIGNED,
        db_index=True
    )

    previous_status = models.CharField(
        max_length=20,
        choices=Status.choices,
        null=True,
        blank=True
    )

    assigned_department = models.ForeignKey(
        "organizations.Department",
        on_delete=models.PROTECT,
        related_name="assigned_tasks"
    )

    original_assigner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="originally_assigned_tasks"
    )

    current_assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="current_tasks"
    )

    due_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["created_at", "id"]

        indexes = [
            models.Index(
                fields=["case", "status"]
            ),
            models.Index(
                fields=["current_assignee", "status"]
            )
        ]

    @property
    def is_overdue(self):
        if self.due_at is None:
            return False

        if self.status in (
            self.Status.COMPLETED,
            self.Status.CANCELLED
        ):
            return False

        return timezone.now() > self.due_at

    def __str__(self):
        return f"Task #{self.pk} ({self.status}): {self.title}"


class Blocker(models.Model):

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"

    task = models.ForeignKey(
        Task,
        on_delete=models.PROTECT,
        related_name="blockers"
    )

    reason = models.CharField(max_length=200)

    description = models.TextField(
        blank=True,
        default=""
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True
    )

    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reported_blockers"
    )

    resolver_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assigned_blockers"
    )

    resolver_department = models.ForeignKey(
        "organizations.Department",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assigned_blockers"
    )

    due_at = models.DateTimeField(
        null=True,
        blank=True
    )

    reported_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="resolved_blockers"
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["-reported_at", "-id"]

        indexes = [
            models.Index(
                fields=["task", "status"]
            )
        ]

    def __str__(self):
        return (
            f"Blocker #{self.pk} "
            f"({self.status}) on Task #{self.task_id}"
        )