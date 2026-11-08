from .notifications import create_notification

EVENT_MESSAGES = {
    "task.assigned": "Task {task_id} was assigned to you.",
    "task.reassigned": "Task {task_id} was reassigned to you.",
    "case.completed": "Case {case_id} has been completed.",
}

def handle_event(*,event_type ,recipient, task_id=None, case_id=None):

    template = EVENT_MESSAGES.get(event_type)
    if template is None:
        raise ValueError("event not found")
    message = template.format(task_id=task_id, case_id=case_id)
    return  create_notification(recipient=recipient, message=message)
        