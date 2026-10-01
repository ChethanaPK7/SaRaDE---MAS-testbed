from django.contrib import admin

from .models import AnumatiConnectionRecord


@admin.register(AnumatiConnectionRecord)
class AnumatiConnectionRecordAdmin(admin.ModelAdmin):
    list_display = [
        "application",
        "purpose",
        "status",
        "anumati_connection_id",
        "valid_until",
    ]
    list_filter = ["purpose", "status"]
