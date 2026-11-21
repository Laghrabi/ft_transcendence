from ..models import Notification


def create_notification(*, recipient, message):
    notification = Notification.objects.create(recipient=recipient, message=message)
    return notification