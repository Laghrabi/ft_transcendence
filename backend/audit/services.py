from .models import AuditEvent


def record_audit_event(*, actor, action, target, metadata=None):
    """
    Record an important action performed in CareFlow.

    This function should be called inside the same database
    transaction as the operation being audited.
    """

    if not isinstance(action, str) or not action.strip():
        raise ValueError("A valid audit action is required.")

    if target.pk is None:
        raise ValueError(
            "Cannot record an audit event for an unsaved object."
        )

    if metadata is None:
        metadata = {}

    if not isinstance(metadata, dict):
        raise ValueError(
            "Audit metadata must be a dictionary."
        )

    if actor is not None and not actor.is_authenticated:
        actor = None

    return AuditEvent.objects.create(
        actor=actor,
        action=action,
        target_type=target._meta.label,
        target_id=target.pk,
        metadata=metadata,
    )