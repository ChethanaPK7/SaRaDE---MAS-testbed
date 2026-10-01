from django.contrib import admin

from .models import Application, ApplicationStatusEvent


class EventInline(admin.TabularInline):
    model = ApplicationStatusEvent
    extra = 0
    readonly_fields = ["from_status", "to_status", "action", "actor", "note", "created_at"]
    can_delete = False


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ["student", "posting", "status", "submitted_at"]
    list_filter = ["status", "posting__institution"]
    search_fields = ["student__username", "posting__title"]
    inlines = [EventInline]
