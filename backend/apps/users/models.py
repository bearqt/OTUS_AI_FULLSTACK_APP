from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
  full_name = models.CharField(max_length=255, blank=True)
  updated_at = models.DateTimeField(auto_now=True)

  class Meta:
    ordering = ["id"]

  def __str__(self):
    return self.email or self.username
