from rest_framework.permissions import BasePermission
from organizations.models import DepartmentMembership, Department

class IsApprovedUser(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_authenticated is False:
            return False
        if request.user.is_active is False:
            return False
        if request.user.approval_status != "approved":
            return False

        return True

def can_manage_department(user, department_id):

    if not user or not user.is_authenticated:
        return False

    if not user.is_active:
        return False

    if user.approval_status != "approved":
        return False

    return DepartmentMembership.objects.filter(
        user=user,
        department_id=department_id,
        department__is_active=True,
        role__name="Administrator"
    ).exists()

def can_participate_in_tasks(user):
    """
    Check whether a user is eligible to participate
    in the task workflow.

    Nurses, Doctors, and Department Administrators
    can assign and receive tasks.
    """

    if user is None or not user.is_authenticated:
        return False

    if not user.is_active:
        return False

    if user.approval_status != "approved":
        return False

    return DepartmentMembership.objects.filter(
        user=user,
        department__is_active=True,
        role__name__in=["Nurse", "Doctor", "Administrator"]
    ).exists()


def can_receive_new_tasks(department_id):
    """
    Check whether a department can receive new tasks.

    The department must be active and must not
    have paused new task assignments.
    """

    return Department.objects.filter(
        id=department_id,
        is_active=True,
        accepts_new_tasks=True
    ).exists()

TASK_PARTICIPANT_ROLES = ("Nurse", "Doctor", "Administrator")

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


def can_receive_task_in_department(user, department):
    """
    Check whether a specific staff member can receive a new task
    in a specific department.
    """

    department_id = _valid_department_id(department)

    if department_id is None:
        return False

    if not can_participate_in_tasks(user):
        return False

    if not can_receive_new_tasks(department_id):
        return False

    return DepartmentMembership.objects.filter(
        user=user,
        department_id=department_id,
        role__name__in=TASK_PARTICIPANT_ROLES,
    ).exists()


def can_initiate_task_assignment_to_department(user, department):
    """
    Preliminary check for cross-department task assignment.

    Actual assignment must also check case access,
    workflow state, and the selected recipient.
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
    Check whether a user can view department-wide analytics.

    Superusers: any existing department.
    Department Administrators: their own active departments.
    Nurses and Doctors: no department-wide analytics access.
    """

    department_id = _valid_department_id(department)

    if department_id is None:
        return False

    if user is None or not getattr(user, "is_authenticated", False):
        return False

    if not getattr(user, "is_active", False):
        return False

    if getattr(user, "approval_status", None) != "approved":
        return False

    if user.is_superuser:
        return Department.objects.filter(
            id=department_id
        ).exists()

    return can_manage_department(user, department_id)

def can_view_case(user, case):
    """
    Allow authenticated, active, approved users to view any case.

    Case visibility is not restricted by department,
    role, or task assignment.
    """

    if user is None or not getattr(user, "is_authenticated", False):
        return False

    if not user.is_active:
        return False

    if user.approval_status != "approved":
        return False

    return True