from django.contrib import admin

from .models import InternshipPosting


@admin.register(InternshipPosting)
class InternshipPostingAdmin(admin.ModelAdmin):
    list_display = ["title", "institution", "application_deadline", "is_active"]
    list_filter = ["institution", "is_active"]
    search_fields = ["title", "lab"]
