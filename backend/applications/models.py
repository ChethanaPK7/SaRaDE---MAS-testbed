from django.conf import settings
from django.db import models

from postings.models import InternshipPosting


class Application(models.Model):
    """One student's application to one posting, and its position in the
    admission workflow. See applications/services.py for the guarded state
    machine that governs how `status` may change.

    Note: `documents_required` / `consent_pending` / `documents_shared` are
    included now so Phase 2 (Anumati integration) doesn't need a schema
    migration -- Phase 1 only drives the workflow as far as
    `documents_required`, then stops (see hooks.py).
    """

    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under review"
        SHORTLISTED = "shortlisted", "Shortlisted"
        ADMITTED = "admitted", "Admitted"
        DOCUMENTS_REQUIRED = "documents_required", "Documents required"
        CONSENT_PENDING = "consent_pending", "Consent pending"  # Phase 2
        DOCUMENTS_SHARED = "documents_shared", "Documents shared"  # Phase 2
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="applications",
        limit_choices_to={"role": "student"},
    )
    posting = models.ForeignKey(
        InternshipPosting, on_delete=models.CASCADE, related_name="applications"
    )
    status = models.CharField(
        max_length=25, choices=Status.choices, default=Status.SUBMITTED
    )
    cover_note = models.TextField(blank=True, default="")

    reviewer_note = models.TextField(blank=True, default="")
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications_decided",
    )
    decided_at = models.DateTimeField(null=True, blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "posting"], name="one_application_per_student_per_posting"
            )
        ]

    def __str__(self):
        return f"{self.student.username} -> {self.posting.title} [{self.status}]"


class ApplicationStatusEvent(models.Model):
    """Audit trail: every state transition, who caused it, and why. This is
    what lets an institution answer "why was this rejected" months later,
    and is also the natural place to later log the paired Anumati
    connection_id once Phase 2 lands."""

    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="events"
    )
    from_status = models.CharField(max_length=25, blank=True, default="")
    to_status = models.CharField(max_length=25)
    action = models.CharField(max_length=50)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.application_id}: {self.from_status} -> {self.to_status}"
