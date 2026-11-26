from rest_framework.permissions import BasePermission
from organizations.models import Department, DepartmentMembership
from workflow.models import Task


TASK_PARTICIPANT_ROLES = ("Nurse", "Doctor", "Administrator")


def is_active_approved_user(user):
    """
    Check whether a user is authenticated, active, and approved.
    """

    return (
        user is not None
        and getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", False)
        and getattr(user, "approval_status", None) == "approved"
    )


class IsApprovedUser(BasePermission):
    def has_permission(self, request, view):
        return is_active_approved_user(request.user)


def _valid_department_id(department):
    """
    Accept a saved Department object or a positive integer ID.
    """

    department_id = getattr(department, "pk", department)

    if isinstance(department_id, bool):
        return None

    if not isinstance(department_id, int) or department_id <= 0:
        return None

    return department_id


def can_manage_department(user, department_id):
    """
    Check whether the user is an Administrator
    of the specified active department.
    """

    department_id = _valid_department_id(department_id)

    if department_id is None:
        return False

    if not is_active_approved_user(user):
        return False

    return DepartmentMembership.objects.filter(
        user=user,
        department_id=department_id,
        department__is_active=True,
        role__name="Administrator",
    ).exists()

def can_view_inactive_staff(user):
    """
    Check whether a user can view approved inactive staff.

    Superusers and Administrators of active departments
    can access inactive staff across all departments.
    """

    if not is_active_approved_user(user):
        return False

    if user.is_superuser:
        return True

    return DepartmentMembership.objects.filter(
        user=user,
        role__name="Administrator",
        department__is_active=True,
    ).exists()

def can_be_department_admin(user):
    """
    Check whether a user is eligible to become
    a Department Administrator.
    """

    if not is_active_approved_user(user):
        return False

    if user.is_superuser:
        return True

    return (
        user.requested_role_id is not None
        and user.requested_role.name in ("Nurse", "Doctor")
    )

def can_participate_in_tasks(user):
    """
    Check whether the user can participate in task workflows.
    """

    if not is_active_approved_user(user):
        return False

    return DepartmentMembership.objects.filter(
        user=user,
        department__is_active=True,
        role__name__in=TASK_PARTICIPANT_ROLES,
    ).exists()


def can_receive_new_tasks(department_id):
    """
    Check whether a department can receive new tasks.
    """

    department_id = _valid_department_id(department_id)

    if department_id is None:
        return False

    return Department.objects.filter(
        id=department_id,
        is_active=True,
        accepts_new_tasks=True,
    ).exists()


def can_receive_task_in_department(user, department):
    """
    Check whether a staff member can receive
    a new task in the specified department.
    """

    department_id = _valid_department_id(department)

    if department_id is None:
        return False

    if not is_active_approved_user(user):
        return False

    return DepartmentMembership.objects.filter(
        user=user,
        department_id=department_id,
        department__is_active=True,
        department__accepts_new_tasks=True,
        role__name__in=TASK_PARTICIPANT_ROLES,
    ).exists()


def can_initiate_task_assignment_to_department(user, department):
    """
    Preliminary check for assignment to a department.

    Does not validate the case, task state, or recipient.
    """

    department_id = _valid_department_id(department)

    if department_id is None:
        return False

    return (
        can_participate_in_tasks(user)
        and can_receive_new_tasks(department_id)
    )

def can_view_case(user, case):
    """
    Any authenticated, active, approved user can view cases.
    """

    return (
        case is not None
        and is_active_approved_user(user)
    )

def _can_participate_in_department(user, department):
    """
    Check whether a user can participate in workflows
    within a specific active department.
    """

    department_id = _valid_department_id(department)

    if department_id is None:
        return False

    if not is_active_approved_user(user):
        return False

    return DepartmentMembership.objects.filter(
        user=user,
        department_id=department_id,
        department__is_active=True,
        role__name__in=TASK_PARTICIPANT_ROLES,
    ).exists()

def _is_active_task(task):
    """
    Check whether a task is in a non-terminal status.
    """

    return (
        task is not None
        and task.status in task.ACTIVE_STATUSES
    )

def _is_eligible_original_assigner(user, task):
    """
    Check whether the user is the original assigner
    and is eligible to act in the case's lead department.
    """

    return (
        task is not None
        and is_active_approved_user(user)
        and user.pk == task.original_assigner_id
        and _can_participate_in_department(
            user,
            task.case.lead_department_id
        )
    )

def _is_eligible_current_assignee(user, task):
    """
    Check whether the user is the current assignee
    and is eligible to work in the assigned department.
    """

    return (
        task is not None
        and is_active_approved_user(user)
        and user.pk == task.current_assignee_id
        and _can_participate_in_department(
            user,
            task.assigned_department_id
        )
    )

def can_create_case(user, department):
    """
    Check whether a user can create a case
    in the specified department.
    """

    return _can_participate_in_department(
        user,
        department
    )

def can_update_case(user, case):
    """
    Check whether a user can update an open case.
    """

    return (
        case is not None
        and case.status == case.Status.OPEN
        and _can_participate_in_department(
            user,
            case.lead_department_id
        )
    )

def can_close_case(user, case):
    """
    Check whether a user can close an open case
    that has no unfinished tasks.
    """

    return (
        case is not None
        and case.status == case.Status.OPEN
        and _can_participate_in_department(
            user,
            case.lead_department_id
        )
        and not case.tasks.filter(
            status__in=Task.ACTIVE_STATUSES
        ).exists()
    )

def can_reopen_case(user, case):
    """
    Check whether a user can reopen a closed case.
    """

    return (
        case is not None
        and case.status == case.Status.CLOSED
        and _can_participate_in_department(
            user,
            case.lead_department_id
        )
    )

def can_create_task(user, case, assignee, department):
    """
    Check whether a user can create and assign a task
    within the specified case.
    """

    return (
        case is not None
        and case.status == case.Status.OPEN
        and _can_participate_in_department(
            user,
            case.lead_department_id
        )
        and can_receive_task_in_department(
            assignee,
            department
        )
    )

def can_view_task(user, task):
    """
    Any user who can view the case
    can also view its tasks.
    """

    return (
        task is not None
        and can_view_case(user, task.case)
    )

def can_update_task(user, task):
    """
    Only the eligible current assignee can update
    an unfinished task.
    """

    return (
        _is_active_task(task)
        and _is_eligible_current_assignee(
            user,
            task
        )
    )

def can_start_task(user, task):
    """
    Only the eligible current assignee can move
    an Assigned task to In Progress.
    """

    return (
        task is not None
        and task.status == task.Status.ASSIGNED
        and _is_eligible_current_assignee(
            user,
            task
        )
    )

def can_complete_task(user, task):
    """
    Only the eligible current assignee can complete
    an Assigned or In Progress task without open blockers.
    """

    return (
        task is not None
        and task.status in (
            task.Status.ASSIGNED,
            task.Status.IN_PROGRESS
        )
        and _is_eligible_current_assignee(
            user,
            task
        )
        and not task.blockers.filter(
            status="open"
        ).exists()
    )

def can_reassign_task(
    user,
    task,
    new_assignee,
    new_department
):
    """
    The eligible original assigner or current assignee
    can reassign an unfinished task to an eligible
    new assignee.
    """

    if not _is_active_task(task):
        return False

    if not (
        _is_eligible_original_assigner(user, task)
        or _is_eligible_current_assignee(user, task)
    ):
        return False

    if not can_receive_task_in_department(
        new_assignee,
        new_department
    ):
        return False

    return new_assignee.pk != task.current_assignee_id

def can_cancel_task(user, task):
    """
    Only the eligible original assigner
    can cancel an unfinished task.
    """

    return (
        _is_active_task(task)
        and _is_eligible_original_assigner(
            user,
            task
        )
    )

def can_view_blocker(user, blocker):
    """
    A user who can view a task
    can also view its blockers.
    """

    return (
        blocker is not None
        and can_view_task(user, blocker.task)
    )

def can_report_blocker(user, task):
    """
    Only the eligible current assignee can report
    a blocker on an unfinished task.
    """

    return (
        _is_active_task(task)
        and _is_eligible_current_assignee(
            user,
            task
        )
    )

def can_resolve_blocker(user, blocker):
    """
    Only the eligible current task assignee
    can resolve an open blocker on a blocked task.
    """

    if blocker is None:
        return False

    task = blocker.task

    return (
        blocker.status == blocker.Status.OPEN
        and task.status == task.Status.BLOCKED
        and _is_eligible_current_assignee(
            user,
            task
        )
    )

def _can_perform_task_recovery(user, department):
    """
    Check whether the user is authorized to perform
    exceptional task recovery in the specified department.
    """

    return can_manage_department(user, department)

def can_exceptionally_reassign_task(
    user,
    task,
    new_assignee,
    new_department,
    reason
):
    """
    Check whether an administrator can exceptionally
    reassign a task whose current assignee is deactivated.
    """

    if not _is_active_task(task):
        return False

    if not _can_perform_task_recovery(
        user,
        task.assigned_department_id
    ):
        return False

    if task.current_assignee.is_active:
        return False

    if not isinstance(reason, str) or not reason.strip():
        return False

    if not can_receive_task_in_department(
        new_assignee,
        new_department
    ):
        return False

    return new_assignee.pk != task.current_assignee_id

def can_exceptionally_cancel_task(user, task, reason):
    """
    Check whether an administrator can exceptionally
    cancel a task whose original assigner is deactivated.
    """

    if not _is_active_task(task):
        return False

    if not _can_perform_task_recovery(
        user,
        task.case.lead_department_id
    ):
        return False

    if task.original_assigner.is_active:
        return False

    if not isinstance(reason, str) or not reason.strip():
        return False

    return True

def can_view_case_comments(user, case):
    """
    Check whether a user can view comments
    associated with a case.
    """

    return (
        case is not None
        and can_view_case(user, case)
    )

def can_create_comment(user, case):
    """
    Check whether a user can comment on an open case.
    """

    return (
        can_view_case_comments(user, case)
        and case.status == case.Status.OPEN
    )

def can_view_notifications(user):
    """
    Check whether a user can access their
    personal notification list.
    """

    return is_active_approved_user(user)

def can_view_notification(user, notification):
    """
    Only the eligible recipient can view
    a notification.
    """

    return (
        notification is not None
        and is_active_approved_user(user)
        and user.pk == notification.recipient_id
    )

def can_update_notification_state(user, notification):
    """
    Only the eligible recipient can modify
    the notification's read state.
    """

    return can_view_notification(user, notification)

def _has_global_analytics_access(user):
    """
    Check whether a user has access to analytics
    across the entire hospital.
    """

    if not is_active_approved_user(user):
        return False

    if user.is_superuser:
        return True

    return DepartmentMembership.objects.filter(
        user=user,
        department__is_active=True,
        role__name="Administrator",
    ).exists()

def can_view_personal_analytics(user, target_user):
    """
    Staff can view their own personal analytics.
    Administrators and superusers can view
    any staff member's personal analytics.
    """

    if target_user is None or target_user.pk is None:
        return False

    if not is_active_approved_user(user):
        return False

    if user.pk == target_user.pk:
        return True

    return _has_global_analytics_access(user)

def can_view_department_analytics(user, department):
    """
    Doctors and Nurses can view analytics of their
    own active departments.

    Administrators and superusers can view analytics
    of any existing department.
    """

    department_id = _valid_department_id(department)

    if department_id is None:
        return False

    if not is_active_approved_user(user):
        return False

    if _has_global_analytics_access(user):
        return Department.objects.filter(
            id=department_id
        ).exists()

    return _can_participate_in_department(
        user,
        department_id
    )

def can_view_hospital_analytics(user):
    """
    Only Department Administrators and superusers
    can view hospital-wide analytics.
    """

    return _has_global_analytics_access(user)
