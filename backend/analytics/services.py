from workflow.models import Case, Task, Blocker


def get_analytics_summary():
    total_cases = Case.objects.count()
    closed_cases = Case.objects.filter(status=Case.Status.CLOSED).count()
    active_tasks = Task.objects.filter(status__in=Task.ACTIVE_STATUSES).count()
    open_blockers = Blocker.objects.filter(status=Blocker.Status.OPEN).count()

    return    {
          "total_cases": total_cases,
          "closed_cases": closed_cases,
          "active_tasks": active_tasks,
          "open_blockers": open_blockers
        }