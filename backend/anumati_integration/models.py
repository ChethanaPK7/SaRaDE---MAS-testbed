from django.db import models

from applications.models import Application


class AnumatiConnectionRecord(models.Model):
    """Tracks one Anumati Connection against one Application, by stage.

    An Application can accumulate multiple records over its lifecycle
    (screening, then admission_active) -- see architecture doc S11. This is
    deliberately NOT a field on Application itself, so adding a future
    stage (e.g. a mid-internship progress-report exchange) is a new row,
    not a schema change.
    """

    class Purpose(models.TextChoices):
        SCREENING = "screening", "Screening"
        ADMISSION_ACTIVE = "admission_active", "Admission (active, bidirectional)"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending (created in SRIP, not yet confirmed live)"
        LIVE = "live", "Live"
        CLOSED = "closed", "Closed"
        FAILED = "failed", "Failed (Anumati call errored)"

    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="anumati_records"
    )
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)

    anumati_connection_id = models.CharField(max_length=64, blank=True, default="")
    anumati_connection_type_id = models.CharField(max_length=64, blank=True, default="")

    valid_until = models.DateTimeField(null=True, blank=True)
    error_detail = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.application_id} [{self.purpose}] -> connection {self.anumati_connection_id or '(none)'}"
