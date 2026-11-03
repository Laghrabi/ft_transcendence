from django.db import models
from  django.conf import settings



# temporary class of case 
class Case(models.Model):
    title = models.CharField(max_length=200)


class Comment(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete= models.SET_NULL,
        null=True
    )
    case = models.ForeignKey(
        Case,
        on_delete = models.PROTECT
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True) 
    