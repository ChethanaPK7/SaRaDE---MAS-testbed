"""
Seeds enough data to run the Phase 1 exit-criterion demo from the
architecture doc: 100 applicants apply to one posting, one gets admitted,
the other 99 are auto-rejected, and the admitted application lands in
`documents_required` -- fully inside SRIP, no Anumati involved.

Usage:
    python manage.py seed_demo
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from applications.models import Application
from applications.services import transition
from postings.models import InternshipPosting
from users.models import Institution

User = get_user_model()


class Command(BaseCommand):
    help = "Seed demo data: 1 institution, 1 faculty, 1 posting, 100 applicants, 1 admitted."

    def add_arguments(self, parser):
        parser.add_argument("--applicants", type=int, default=100)

    @transaction.atomic
    def handle(self, *args, **options):
        n = options["applicants"]

        institution, inst_created = Institution.objects.get_or_create(
            name="IIIT Bangalore",
            defaults={
                "description": "International Institute of Information Technology, Bangalore",
                "anumati_username": "iiitb_admissions",
                "anumati_admissions_locker_name": "Admissions",
            },
        )
        if inst_created or not institution.anumati_password_encrypted:
            institution.set_anumati_password("demo-anumati-password")
            institution.anumati_linked_at = timezone.now()
            institution.save()

        faculty, created = User.objects.get_or_create(
            username="faculty_demo",
            defaults=dict(
                email="faculty@iiitb.example",
                role=User.Role.FACULTY,
                institution=institution,
                first_name="Ada",
                last_name="Reviewer",
            ),
        )
        if created:
            faculty.set_password("demo1234")
            faculty.save()

        posting, _ = InternshipPosting.objects.get_or_create(
            title="GNN-based Trust Modeling Internship",
            institution=institution,
            defaults=dict(
                created_by=faculty,
                lab="Web Science Lab",
                description="Work on heterogeneous graph attention trust networks.",
                eligibility="Final-year B.Tech/M.Tech in CS or related field.",
                duration_weeks=12,
                stipend=15000,
                application_deadline=timezone.localdate() + timedelta(days=14),
                start_date=timezone.localdate() + timedelta(days=30),
                end_date=timezone.localdate() + timedelta(days=30 + 84),
                required_documents=["transcript", "recommendation_letter", "id_proof"],
            ),
        )

        applications = []
        for i in range(1, n + 1):
            username = f"student_demo_{i:03d}"
            student, created = User.objects.get_or_create(
                username=username,
                defaults=dict(
                    email=f"{username}@example.edu",
                    role=User.Role.STUDENT,
                    first_name="Student",
                    last_name=f"{i:03d}",
                    anumati_locker_name="Academic",
                    anumati_linked_at=timezone.now(),
                ),
            )
            if created:
                student.set_password("demo1234")
                student.save()

            application, app_created = Application.objects.get_or_create(
                student=student,
                posting=posting,
                defaults={"cover_note": f"Applicant #{i} cover note."},
            )
            if app_created:
                from applications.hooks import on_submitted

                on_submitted(application)
            applications.append(application)

        self.stdout.write(
            self.style.SUCCESS(f"Seeded {len(applications)} applications to '{posting.title}'.")
        )

        # Run the selection: shortlist and admit the first applicant that's
        # still in a selectable state (idempotent across repeated runs).
        selected = next(
            (a for a in applications if a.status == Application.Status.SUBMITTED), None
        )
        if selected:
            transition(application=selected, action="shortlist", actor=faculty)
            transition(application=selected, action="admit", actor=faculty)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Admitted {selected.student.username}; status is now "
                    f"'{Application.objects.get(pk=selected.pk).status}'. "
                    f"Other applicants auto-rejected."
                )
            )
            from anumati_integration.models import AnumatiConnectionRecord

            self.stdout.write(
                f"Anumati (mock) screening connections closed: "
                f"{AnumatiConnectionRecord.objects.filter(purpose='screening', status='closed').count()}, "
                f"admission connection created: "
                f"{AnumatiConnectionRecord.objects.filter(purpose='admission_active').count()}"
            )
        else:
            self.stdout.write("No submitted applicant left to admit (already run?).")

        self.stdout.write(
            self.style.SUCCESS(
                "\nLogin as faculty_demo / demo1234 (reviewer) or "
                "student_demo_001 / demo1234 (the admitted student)."
            )
        )
