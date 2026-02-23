from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
  fieldsets = DjangoUserAdmin.fieldsets + (("Profile", {"fields": ("full_name", "updated_at")}),)
  readonly_fields = ("updated_at",)
