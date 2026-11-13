from ..models import Notification
from django.db import transaction
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def create_notification(*, recipient, message):
    notification = Notification.objects.create(recipient=recipient, message=message)
    def broadcast():
        layer = get_channel_layer()
        async_to_sync(layer.group_send)(f"user.{notification.recipient_id}",{"type": "notification.message","message": notification.message})
    transaction.on_commit(broadcast,  robust=True)
    return notification