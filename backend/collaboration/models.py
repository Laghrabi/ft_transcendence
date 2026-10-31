from django.db import models
from  django.conf import settings


class Comments(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete= models.SET_NULL
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True) 
    