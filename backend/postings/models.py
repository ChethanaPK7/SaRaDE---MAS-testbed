from django.conf import settings
from django.db import models

from users.models import Institution


class InternshipPosting(models.Model):
    institution = models.ForeignKey(
        Institution, on_delete=models.CASCADE, related_name="postings"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="postings_created",
        limit_choices_to={"role__in": ["faculty", "institution_admin"]},
    )
    title = models.CharField(max_length=150)
    lab = models.CharField(max_length=150, blank=True, default="")
    description = models.TextField()
    eligibility = models.TextField(blank=True, default="")
    duration_weeks = models.PositiveIntegerField(default=8)
    stipend = models.PositiveIntegerField(default=0, help_text="Monthly stipend in INR.")
    application_deadline = models.DateField()
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    # Names only, not a schema for the documents themselves -- Phase 2 maps
    # each of these to an Anumati ConnectionTerms entry.
    required_documents = models.JSONField(default=list, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} @ {self.institution.name}"

    @property
    def is_open(self):
        from django.utils import timezone

        return self.is_active and self.application_deadline >= timezone.localdate()
