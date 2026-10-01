from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Institution, User


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at"]
    search_fields = ["name"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["username", "email", "role", "institution", "is_staff"]
    list_filter = ["role", "institution"]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("SRIP profile", {"fields": ("role", "institution", "anumati_locker_id")}),
    )
