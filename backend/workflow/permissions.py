#permissions its gatekeeper to save our data before any change or any request
from django.db.models import Q

from accounts.permissions import (
    IsApprovedUser,
    TASK_PARTICIPANT_ROLES,
    can_initiate_task_assignment_to_department,
    can_participate_in_tasks,
    can_receive_task_in_department,
)
from organizations.models import DepartmentMembership


def _is_active_approved_user(user):
    """Verify the user is authenticated, active, and approved."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if not getattr(user, "is_active", False):
        return False
    if getattr(user, "approval_status", None) != "approved":
        return False
    return True


def is_active_department_participant(user, department):
    """
    Verify that `user` is an active, approved Doctor, Nurse, or Administrator
    in the given active department (regardless of `accepts_new_tasks`).
    """
    if not _is_active_approved_user(user):
        return False

    department_id = getattr(department, "pk", department)
    if isinstance(department_id, bool) or not isinstance(department_id, int) or department_id <= 0:
        return False

    return DepartmentMembership.objects.filter(
        user=user,
        department_id=department_id,
        department__is_active=True,
        role__name__in=TASK_PARTICIPANT_ROLES,
    ).exists()


def can_create_case(user, lead_department):
    """Only active, approved staff belonging to the active lead department may create a case."""
    return is_active_department_participant(user, lead_department)


def can_access_case(user, case):
    """Restrict case access to its creator and authorized case members."""
    if not _is_active_approved_user(user):
        return False
    if case.created_by_id == user.id:
        return True
    return case.members.filter(pk=user.pk).exists()


def filter_accessible_cases(queryset, user):
    """Filter a Case QuerySet down to cases the user created or is a member of."""
    if not _is_active_approved_user(user):
        return queryset.none()
    return queryset.filter(
        Q(created_by=user) | Q(members=user)
    ).distinct()


def can_update_case(user, case):
    """Only eligible task participants who have access to the case may update it."""
    return can_participate_in_tasks(user) and can_access_case(user, case)


def can_close_case(user, case):
    """Only the case creator or an active member of the lead department may close a case."""
    if not _is_active_approved_user(user):
        return False
    if case.created_by_id == user.id:
        return True
    return is_active_department_participant(user, case.lead_department_id)


def can_assign_task_on_case(user, case, target_department, recipient):
    """
    Verify task creation/assignment authorization:
    1. Actor has access to the case.
    2. Actor is eligible and target department is active & accepts new tasks.
    3. Recipient is active, approved, and holds a task role in target department.
    """
    if not can_access_case(user, case):
        return False
    if not can_initiate_task_assignment_to_department(user, target_department):
        return False
    if not can_receive_task_in_department(recipient, target_department):
        return False
    return True


def can_view_task(user, task):
    """Staff can view a task if they have access to its parent case."""
    return can_access_case(user, task.case)


def can_update_or_complete_task(user, task):
    """Only the current task assignee may update, start, or complete the task."""
    if not _is_active_approved_user(user):
        return False
    return task.current_assignee_id == user.id


def can_reassign_task(user, task):
    """Only the original assigner or the current assignee may reassign the task."""
    if not can_participate_in_tasks(user):
        return False
    return user.id in (task.original_assigner_id, task.current_assignee_id)


def can_cancel_task(user, task):
    """Only the original assigner may cancel the task."""
    if not _is_active_approved_user(user):
        return False
    return task.original_assigner_id == user.id


def can_report_blocker(user, task):
    """Only the current task assignee may report a blocker on the task."""
    if not _is_active_approved_user(user):
        return False
    return task.current_assignee_id == user.id


def can_resolve_blocker(user, blocker):
    """
    Enforce blocker resolution authorization:
    - If `resolver_user` is set: only that user may resolve it.
    - Else if `resolver_department` is set: any active eligible member of that department.
    - Else (no designated resolver): any eligible staff member with access to the case.
    """
    if not _is_active_approved_user(user):
        return False

    if blocker.resolver_user_id is not None:
        return blocker.resolver_user_id == user.id

    if blocker.resolver_department_id is not None:
        return is_active_department_participant(user, blocker.resolver_department_id)

    return can_participate_in_tasks(user) and can_access_case(user, blocker.task.case)