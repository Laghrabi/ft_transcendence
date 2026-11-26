from workflow.models import Case, Task, Blocker
from accounts.models import User
from organizations.models import Department, DepartmentMembership
from django.utils import timezone
from django.db.models import Q

def get_analytics_summary():
    total_cases = Case.objects.count()
    closed_cases = Case.objects.filter(status=Case.Status.CLOSED).count()
    active_tasks = Task.objects.filter(status__in=Task.ACTIVE_STATUSES).count()
    open_blockers = Blocker.objects.filter(status=Blocker.Status.OPEN).count()
    if total_cases > 0:
      closure_rate = round((closed_cases / total_cases) * 100, 2)
    else:
        closure_rate = 0.0
    return    {
          "total_cases": total_cases,
          "closed_cases": closed_cases,
          "active_tasks": active_tasks,
          "open_blockers": open_blockers,
          "closure_rate": closure_rate
        }
    
    
def get_staff_summary():
    active_approved_staff = User.objects.filter(is_active=True,approval_status="approved").count()
    return{
      "active_approved_staff": active_approved_staff
    }
    
def get_departments_summary():
    total_departments	= Department.objects.count()  
    active_departments = Department.objects.filter(is_active=True).count() 
    if total_departments > 0:
      active_percentage	= round((active_departments / total_departments) * 100, 2)
    else:
      active_percentage = 0.0
    unassigned_staff =  User.objects.filter(is_active=True,approval_status="approved", departmentmembership__isnull=True).count()

    return{
      "total_departments": total_departments,
      "active_departments": active_departments,
      "active_percentage": active_percentage,
      "unassigned_staff": unassigned_staff
    }
    
def get_department_metrics(department_id):
  assigned_staff = DepartmentMembership.objects.filter(department_id=department_id, user__approval_status="approved").count()
  active_tasks = Task.objects.filter(assigned_department_id=department_id, status__in=Task.ACTIVE_STATUSES).count()
  open_cases = Case.objects.filter(lead_department_id=department_id, status=Case.Status.OPEN).count()
  return {
    "department_id" :department_id,
    "assigned_staff" : assigned_staff,
    "active_tasks" : active_tasks,
    "open_cases" : open_cases
  }
  
def get_dashboard_summary():
  active_cases = Case.objects.filter(status=Case.Status.OPEN).count()
  pending_tasks =  Task.objects.filter(status__in=[Task.Status.ASSIGNED,Task.Status.IN_PROGRESS]).count()
  today = timezone.localdate()
  completed_tasks_today = Task.objects.filter(completed_at__date =today,status=Task.Status.COMPLETED).count()
  blocked_or_overdue = Task.objects.filter(
    Q(status=Task.Status.BLOCKED) |
    (
        Q(status__in=[
            Task.Status.ASSIGNED,
            Task.Status.IN_PROGRESS
        ]) &
        Q(due_at__lt=timezone.now())
    )
  ).count()
  return {
  "active_cases": active_cases,
  "pending_tasks": pending_tasks,
  "completed_today": completed_tasks_today,
  "blocked_or_overdue" : blocked_or_overdue
}