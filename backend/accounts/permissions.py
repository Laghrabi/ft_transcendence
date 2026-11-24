from rest_framework.permissions import BasePermission
from organizations.models import Department, DepartmentMembership


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

    if not is_active_approved_user(user):
        return False

    return DepartmentMembership.objects.filter(
        user=user,
        department_id=department_id,
        department__is_active=True,
        role__name="Administrator",
    ).exists()


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


def can_view_department_analytics(user, department):
    """
    Superusers can view analytics for any existing department.
    Department Administrators can view their active departments.
    """

    department_id = _valid_department_id(department)

    if department_id is None:
        return False

    if not is_active_approved_user(user):
        return False

    if user.is_superuser:
        return Department.objects.filter(
            id=department_id
        ).exists()

    return can_manage_department(user, department_id)


def can_view_case(user, case):
    """
    Any authenticated, active, approved user can view cases.
    """

    return is_active_approved_user(user)
