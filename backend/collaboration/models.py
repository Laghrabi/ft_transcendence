from django.db import models
from  django.conf import settings
# from .models import Case



# temporary class of case for testing purposes, will be replaced with the real one later :)

# class Case(models.Model):
#     title = models.CharField(max_length=200)
#     members = models.ManyToManyField(
#         settings.AUTH_USER_MODEL,
#         blank=True
#     )


class Comment(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete= models.SET_NULL,
        null=True
    )
    case = models.ForeignKey(
        "workflow.Case",
        on_delete = models.PROTECT
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True) 


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete= models.CASCADE
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    