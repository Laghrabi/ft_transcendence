from workflow.models import Case, Task, Blocker
from accounts.models import User
from organizations.models import Department, DepartmentMembership
from django.utils import timezone
from django.db.models import Q


def get_analytics_summary(department_id=None, start_date=None, end_date=None):

    if department_id is not None:
        cases = Case.objects.filter(lead_department_id=department_id)
        tasks = Task.objects.filter(assigned_department_id=department_id)
        blockers = Blocker.objects.filter(
            task__assigned_department_id=department_id
        )
    else:
        cases = Case.objects.all()
        tasks = Task.objects.all()
        blockers = Blocker.objects.all()

    if start_date is not None:
        cases = cases.filter(created_at__date__gte=start_date)
        tasks = tasks.filter(created_at__date__gte=start_date)
        blockers = blockers.filter(reported_at__date__gte=start_date)

    if end_date is not None:
        cases = cases.filter(created_at__date__lte=end_date)
        tasks = tasks.filter(created_at__date__lte=end_date)
        blockers = blockers.filter(reported_at__date__lte=end_date)

    total_cases = cases.count()
    closed_cases = cases.filter(status=Case.Status.CLOSED).count()

    active_tasks = tasks.filter(
        status__in=Task.ACTIVE_STATUSES
    ).count()

    open_blockers = blockers.filter(
        status=Blocker.Status.OPEN
    ).count()

    if total_cases > 0:
        closure_rate = round((closed_cases / total_cases) * 100, 2)
    else:
        closure_rate = 0.0

    summary = {
        "total_cases": total_cases,
        "closed_cases": closed_cases,
        "active_tasks": active_tasks,
        "open_blockers": open_blockers,
        "closure_rate": closure_rate
    }

    summary.update(get_waiting_time_metrics(department_id=department_id, tasks=tasks))
    summary.update(get_department_bottlenecks(department_id=department_id, tasks=tasks))

    return summary


def get_staff_summary():
    active_approved_staff = User.objects.filter(
        is_active=True,
        approval_status="approved"
    ).count()

    return {
        "active_approved_staff": active_approved_staff
    }


def get_departments_summary():
    total_departments = Department.objects.count()
    active_departments = Department.objects.filter(
        is_active=True
    ).count()

    if total_departments > 0:
        active_percentage = round(
            (active_departments / total_departments) * 100, 2
        )
    else:
        active_percentage = 0.0

    unassigned_staff = User.objects.filter(
        is_active=True,
        approval_status="approved",
        departmentmembership__isnull=True
    ).count()

    return {
        "total_departments": total_departments,
        "active_departments": active_departments,
        "active_percentage": active_percentage,
        "unassigned_staff": unassigned_staff
    }


def get_department_metrics(department_id):
    assigned_staff = DepartmentMembership.objects.filter(
        department_id=department_id,
        user__approval_status="approved"
    ).count()

    active_tasks = Task.objects.filter(
        assigned_department_id=department_id,
        status__in=Task.ACTIVE_STATUSES
    ).count()

    open_cases = Case.objects.filter(
        lead_department_id=department_id,
        status=Case.Status.OPEN
    ).count()

    return {
        "department_id": department_id,
        "assigned_staff": assigned_staff,
        "active_tasks": active_tasks,
        "open_cases": open_cases
    }


def get_dashboard_summary():
    active_cases = Case.objects.filter(
        status=Case.Status.OPEN
    ).count()

    pending_tasks = Task.objects.filter(
        status__in=[
            Task.Status.ASSIGNED,
            Task.Status.IN_PROGRESS
        ]
    ).count()

    today = timezone.localdate()

    completed_tasks_today = Task.objects.filter(
        completed_at__date=today,
        status=Task.Status.COMPLETED
    ).count()

    blocked_or_overdue = Task.objects.filter(
        Q(status=Task.Status.BLOCKED)
        |
        (
            Q(status__in=[
                Task.Status.ASSIGNED,
                Task.Status.IN_PROGRESS
            ])
            &
            Q(due_at__lt=timezone.now())
        )
    ).count()

    return {
        "active_cases": active_cases,
        "pending_tasks": pending_tasks,
        "completed_today": completed_tasks_today,
        "blocked_or_overdue": blocked_or_overdue
    }


def get_waiting_time_metrics(department_id=None, tasks=None):

    # When called from get_analytics_summary(), tasks already
    # contains the selected department and date filters.
    if tasks is None:
        tasks = Task.objects.all()

        if department_id is not None:
            tasks = tasks.filter(assigned_department_id=department_id)

    tasks = tasks.filter(started_at__isnull=False)

    total_waiting_hours = 0.0
    total_started_tasks = 0

    for task in tasks:
        waiting = task.started_at - task.created_at
        total_waiting_hours += waiting.total_seconds() / 3600
        total_started_tasks += 1

    if total_started_tasks > 0:
        average_waiting_hours = round(total_waiting_hours / total_started_tasks, 2)
    else:
        average_waiting_hours = 0.0

    return {
        "average_waiting_hours": average_waiting_hours
    }


def get_department_bottlenecks(department_id=None, tasks=None):

    if tasks is None:
        tasks = Task.objects.all()

        if department_id is not None:
            tasks = tasks.filter(assigned_department_id=department_id)

    now = timezone.now()

    blocked_tasks = tasks.filter(
        status=Task.Status.BLOCKED
    ).count()

    blocked_or_overdue = tasks.filter(
        Q(status=Task.Status.BLOCKED)
        |
        (
            Q(status__in=[
                Task.Status.ASSIGNED,
                Task.Status.IN_PROGRESS
            ])
            &
            Q(due_at__lt=now)
        )
    ).count()

    overdue_tasks = tasks.filter(status__in=Task.ACTIVE_STATUSES,due_at__lt=now).count()

    return {
        "department_id": department_id,
        "blocked_tasks": blocked_tasks,
        "overdue_tasks": overdue_tasks,
        "blocked_or_overdue": blocked_or_overdue
    }