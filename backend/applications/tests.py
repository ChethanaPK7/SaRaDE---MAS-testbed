from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from postings.models import InternshipPosting
from users.models import Institution

from .models import Application
from .services import TransitionForbidden, TransitionNotAllowed, transition

User = get_user_model()


class ApplicationStateMachineTests(TestCase):
    def setUp(self):
        self.institution = Institution.objects.create(name="Test Institute")
        self.other_institution = Institution.objects.create(name="Other Institute")
        self.faculty = User.objects.create_user(
            "faculty1", role=User.Role.FACULTY, institution=self.institution
        )
        self.outside_faculty = User.objects.create_user(
            "faculty2", role=User.Role.FACULTY, institution=self.other_institution
        )
        self.posting = InternshipPosting.objects.create(
            institution=self.institution,
            created_by=self.faculty,
            title="Test posting",
            description="desc",
            application_deadline=timezone.localdate() + timedelta(days=10),
        )
        self.students = [
            User.objects.create_user(f"student{i}", role=User.Role.STUDENT)
            for i in range(3)
        ]
        self.applications = [
            Application.objects.create(student=s, posting=self.posting)
            for s in self.students
        ]

    def test_illegal_transition_is_rejected(self):
        app = self.applications[0]
        with self.assertRaises(TransitionNotAllowed):
            transition(application=app, action="admit", actor=self.faculty)
        app.refresh_from_db()
        self.assertEqual(app.status, Application.Status.SUBMITTED)

    def test_wrong_institution_reviewer_is_forbidden(self):
        app = self.applications[0]
        with self.assertRaises(TransitionForbidden):
            transition(application=app, action="shortlist", actor=self.outside_faculty)

    def test_student_cannot_admit_own_application(self):
        app = self.applications[0]
        transition(application=app, action="shortlist", actor=self.faculty)
        with self.assertRaises(TransitionForbidden):
            transition(application=app, action="admit", actor=app.student)

    def test_admit_auto_rejects_other_applicants_and_advances_status(self):
        selected = self.applications[0]
        transition(application=selected, action="shortlist", actor=self.faculty)
        transition(application=selected, action="admit", actor=self.faculty)

        selected.refresh_from_db()
        self.assertEqual(selected.status, Application.Status.DOCUMENTS_REQUIRED)

        for app in self.applications[1:]:
            app.refresh_from_db()
            self.assertEqual(app.status, Application.Status.REJECTED)

    def test_withdraw_only_by_owner(self):
        app = self.applications[0]
        other_student = self.applications[1].student
        with self.assertRaises(TransitionForbidden):
            transition(application=app, action="withdraw", actor=other_student)

        transition(application=app, action="withdraw", actor=app.student)
        app.refresh_from_db()
        self.assertEqual(app.status, Application.Status.WITHDRAWN)

    def test_event_audit_trail_recorded(self):
        app = self.applications[0]
        transition(application=app, action="shortlist", actor=self.faculty)
        events = list(app.events.all())
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].action, "shortlist")
        self.assertEqual(events[0].from_status, Application.Status.SUBMITTED)
        self.assertEqual(events[0].to_status, Application.Status.SHORTLISTED)
