from contextlib import contextmanager
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from applications.models import Application
from applications.services import transition
from postings.models import InternshipPosting
from users.models import Institution

from .models import AnumatiConnectionRecord

User = get_user_model()


@override_settings(ANUMATI_MOCK=True)
class AnumatiIntegrationFlowTests(TestCase):
    """Exercises the full 'N apply, 1 selected' flow through the real
    hooks -> services wiring, using MockAnumatiClient so it needs no
    network access. This is the Phase 2 analogue of the Phase 1
    100-applicant test in applications/tests.py."""

    def setUp(self):
        self.institution = Institution.objects.create(
            name="Test Institute",
            anumati_username="inst_anumati_user",
            anumati_admissions_locker_name="Admissions",
        )
        self.institution.set_anumati_password("dummy-anumati-password")
        self.institution.save()
        self.faculty = User.objects.create_user(
            "faculty1", role=User.Role.FACULTY, institution=self.institution
        )
        self.posting = InternshipPosting.objects.create(
            institution=self.institution,
            created_by=self.faculty,
            title="Test posting",
            description="desc",
            application_deadline=timezone.localdate() + timedelta(days=10),
            end_date=timezone.localdate() + timedelta(days=90),
            required_documents=["transcript"],
        )
        self.students = []
        self.applications = []
        for i in range(5):
            student = User.objects.create_user(
                f"student{i}",
                role=User.Role.STUDENT,
                anumati_locker_name="Academic",
            )
            self.students.append(student)
            app = Application.objects.create(student=student, posting=self.posting)
            self.applications.append(app)

    def test_submission_creates_pending_screening_record_for_every_applicant(self):
        from applications.hooks import on_submitted

        for app in self.applications:
            on_submitted(app)

        self.assertEqual(
            AnumatiConnectionRecord.objects.filter(
                purpose=AnumatiConnectionRecord.Purpose.SCREENING
            ).count(),
            5,
        )
        for app in self.applications:
            record = app.anumati_records.get(purpose=AnumatiConnectionRecord.Purpose.SCREENING)
            self.assertEqual(record.status, AnumatiConnectionRecord.Status.PENDING)
            self.assertTrue(record.anumati_connection_id)

    def test_admit_closes_all_screening_and_opens_one_admission_connection(self):
        from applications.hooks import on_submitted

        for app in self.applications:
            on_submitted(app)

        selected = self.applications[0]
        transition(application=selected, action="shortlist", actor=self.faculty)
        transition(application=selected, action="admit", actor=self.faculty)

        # Every screening record -- selected and rejected alike -- is closed.
        screening_records = AnumatiConnectionRecord.objects.filter(
            purpose=AnumatiConnectionRecord.Purpose.SCREENING
        )
        self.assertEqual(screening_records.count(), 5)
        self.assertTrue(
            all(r.status == AnumatiConnectionRecord.Status.CLOSED for r in screening_records)
        )

        # Exactly one bidirectional admission connection, for the selected applicant.
        admission_records = AnumatiConnectionRecord.objects.filter(
            purpose=AnumatiConnectionRecord.Purpose.ADMISSION_ACTIVE
        )
        self.assertEqual(admission_records.count(), 1)
        admission_record = admission_records.first()
        self.assertEqual(admission_record.application_id, selected.id)
        self.assertEqual(admission_record.status, AnumatiConnectionRecord.Status.PENDING)
        self.assertTrue(admission_record.anumati_connection_id)
        self.assertIsNotNone(admission_record.valid_until)

    def test_unlinked_student_or_institution_skips_gracefully(self):
        """A student who hasn't linked a locker yet shouldn't block
        submission -- the hook should no-op, not raise."""
        from applications.hooks import on_submitted

        unlinked_student = User.objects.create_user("unlinked", role=User.Role.STUDENT)
        app = Application.objects.create(student=unlinked_student, posting=self.posting)

        on_submitted(app)  # should not raise

        self.assertFalse(app.anumati_records.exists())


@override_settings(ANUMATI_MOCK=True)
class AnumatiLinkingEndpointTests(TestCase):
    """Sprint 8: locker linking endpoints. Uses the mock client, so these
    never touch the network -- they verify SRIP's own persistence and
    permission logic, not Anumati's behavior."""

    def setUp(self):
        self.institution = Institution.objects.create(name="Link Test Institute")
        self.student = User.objects.create_user("link_student", role=User.Role.STUDENT)
        self.admin = User.objects.create_user(
            "link_admin", role=User.Role.INSTITUTION_ADMIN, institution=self.institution
        )
        self.faculty = User.objects.create_user(
            "link_faculty", role=User.Role.FACULTY, institution=self.institution
        )
        self.client = APIClient()

    def test_student_can_link_locker(self):
        self.client.force_authenticate(self.student)
        resp = self.client.post(
            "/api/anumati/link-student-locker/",
            {
                "anumati_username": "student_anumati_handle",
                "anumati_password": "whatever",
                "locker_name": "Academic",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["verified"])
        self.student.refresh_from_db()
        self.assertTrue(self.student.anumati_linked)
        self.assertTrue(self.student.anumati_verified)
        self.assertEqual(self.student.anumati_locker_name, "Academic")
        self.assertEqual(self.student.anumati_username, "student_anumati_handle")
        # password must never be persisted anywhere on User
        self.assertNotIn("whatever", str(self.student.__dict__))

    def test_student_can_link_without_password_self_attested(self):
        """The redirect-out path: no password submitted at all. SRIP saves
        the link but marks it unverified, and never calls Anumati."""
        self.client.force_authenticate(self.student)
        resp = self.client.post(
            "/api/anumati/link-student-locker/",
            {"anumati_username": "student_anumati_handle", "locker_name": "Academic"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["verified"])
        self.assertIsNotNone(resp.data["warning"])
        self.student.refresh_from_db()
        self.assertTrue(self.student.anumati_linked)
        self.assertFalse(self.student.anumati_verified)

    def test_faculty_cannot_link_a_student_locker(self):
        self.client.force_authenticate(self.faculty)
        resp = self.client.post(
            "/api/anumati/link-student-locker/",
            {"anumati_username": "x", "anumati_password": "y", "locker_name": "Academic"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_only_institution_admin_can_link_institution_locker(self):
        self.client.force_authenticate(self.faculty)
        resp = self.client.post(
            "/api/anumati/link-institution-locker/",
            {"anumati_username": "inst_x", "anumati_password": "y", "locker_name": "Admissions"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_institution_admin_can_link_institution_locker_and_password_is_encrypted(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            "/api/anumati/link-institution-locker/",
            {
                "anumati_username": "inst_anumati_handle",
                "anumati_password": "super-secret-password",
                "locker_name": "Admissions",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.institution.refresh_from_db()
        self.assertTrue(self.institution.anumati_linked)
        self.assertEqual(self.institution.anumati_admissions_locker_name, "Admissions")
        # stored ciphertext must not contain the raw password
        self.assertNotIn(
            b"super-secret-password", bytes(self.institution.anumati_password_encrypted)
        )
        # but it must decrypt back to exactly what was submitted
        self.assertEqual(self.institution.get_anumati_password(), "super-secret-password")

    def test_status_endpoint_reflects_link_state(self):
        self.client.force_authenticate(self.student)
        resp = self.client.get("/api/anumati/status/")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["user_linked"])

        self.client.post(
            "/api/anumati/link-student-locker/",
            {"anumati_username": "x", "anumati_password": "y", "locker_name": "Academic"},
        )
        resp = self.client.get("/api/anumati/status/")
        self.assertTrue(resp.data["user_linked"])

    def test_unlink_clears_student_locker(self):
        self.client.force_authenticate(self.student)
        self.client.post(
            "/api/anumati/link-student-locker/",
            {"anumati_username": "x", "anumati_password": "y", "locker_name": "Academic"},
        )
        self.student.refresh_from_db()
        self.assertTrue(self.student.anumati_linked)

        self.client.post("/api/anumati/unlink-student-locker/")
        self.student.refresh_from_db()
        self.assertFalse(self.student.anumati_linked)


class _FakeResponse:
    def __init__(self, json_data, status_code):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json


class AnumatiClientAgainstNewBackendTests(TestCase):
    """Unit tests for AnumatiClient itself (mocked HTTP), covering the two
    things confirmed live against DPI-Primitive-Jenkins-dev on 2026-08-06:
    JWT bearer auth (login-then-Bearer, not Basic), and the idempotent
    create_connection_type fix for Anumati's now-enforced name+direction
    uniqueness constraint. See client.py's module docstring."""

    def _client(self):
        from .client import AnumatiClient

        return AnumatiClient(base_url="http://fake-anumati", host_username="h", host_password="p")

    def test_request_logs_in_once_and_sends_bearer_token(self):
        from unittest.mock import patch

        client = self._client()
        with patch("anumati_integration.client.requests.post") as mock_post, patch(
            "anumati_integration.client.requests.request"
        ) as mock_request:
            mock_post.return_value = _FakeResponse({"success": True, "access": "tok123"}, 200)
            mock_request.return_value = _FakeResponse(
                {"success": True, "id": 5, "name": "Academic"}, 201
            )

            client.create_locker("Academic", username="stu", password="pw")

            mock_post.assert_called_once()  # exactly one login call
            self.assertIn("Bearer tok123", mock_request.call_args.kwargs["headers"]["Authorization"])

    def test_create_connection_type_is_idempotent_on_name_conflict(self):
        from unittest.mock import patch

        client = self._client()
        with patch("anumati_integration.client.requests.post") as mock_post, patch(
            "anumati_integration.client.requests.request"
        ) as mock_request:
            mock_post.return_value = _FakeResponse({"success": True, "access": "tok"}, 200)

            def fake_request(method, url, **kwargs):
                if "create-connection-type-and-terms" in url:
                    return _FakeResponse(
                        {
                            "success": False,
                            "error": "Connection type 'X' with the same direction already exists in 'Admissions'.",
                        },
                        400,
                    )
                if "get_connection_types_by_locker" in url:
                    return _FakeResponse(
                        {
                            "connection_types": [
                                {"connection_type_id": 42, "connection_type_name": "X"}
                            ]
                        },
                        200,
                    )
                raise AssertionError(f"unexpected URL: {url}")

            mock_request.side_effect = fake_request

            ct_id = client.create_connection_type(
                connection_name="X",
                connection_description="d",
                locker_name="Admissions",
                validity_iso="2026-12-31T00:00:00Z",
                directions=[],
                username="inst",
                password="pw",
            )
            self.assertEqual(ct_id, 42)  # recovered via lookup, no exception raised

    def test_create_connection_type_still_raises_on_unrelated_error(self):
        from unittest.mock import patch

        from .client import AnumatiAPIError

        client = self._client()
        with patch("anumati_integration.client.requests.post") as mock_post, patch(
            "anumati_integration.client.requests.request"
        ) as mock_request:
            mock_post.return_value = _FakeResponse({"success": True, "access": "tok"}, 200)
            mock_request.return_value = _FakeResponse(
                {"success": False, "error": "lockerName is required"}, 400
            )

            with self.assertRaises(AnumatiAPIError):
                client.create_connection_type(
                    connection_name="X",
                    connection_description="d",
                    locker_name="",
                    validity_iso="2026-12-31T00:00:00Z",
                    directions=[],
                    username="inst",
                    password="pw",
                )


@override_settings(ANUMATI_MOCK=True)
class OAuthLockerLinkingTests(TestCase):
    """The oauth_start / oauth_callback flow, using MockAnumatiClient's
    exchange_code so this needs no network. What's actually being tested
    here is SRIP's own state signing/verification and what it does with
    the exchange result -- the real code-exchange semantics (single-use,
    client_secret checked, redirect_uri matched) are Anumati's job and
    are covered live in docs/oauth-locker-linking.md's verification log,
    not re-tested here."""

    def setUp(self):
        self.institution = Institution.objects.create(name="OAuth Test Institute")
        self.student = User.objects.create_user("oauth_student", role=User.Role.STUDENT)
        self.admin = User.objects.create_user(
            "oauth_admin", role=User.Role.INSTITUTION_ADMIN, institution=self.institution
        )
        self.client = APIClient()

    def test_start_returns_authorize_url_with_signed_state(self):
        self.client.force_authenticate(self.student)
        resp = self.client.get("/api/anumati/oauth/start/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("oauth/authorize", resp.data["authorize_url"])
        self.assertIn("state=", resp.data["authorize_url"])

    def test_institution_admin_without_institution_cannot_start(self):
        orphan_admin = User.objects.create_user(
            "orphan_admin", role=User.Role.INSTITUTION_ADMIN
        )
        self.client.force_authenticate(orphan_admin)
        resp = self.client.get("/api/anumati/oauth/start/")
        self.assertEqual(resp.status_code, 400)

    def test_callback_links_student_and_marks_verified(self):
        from django.core import signing

        from anumati_integration.views import OAUTH_STATE_SALT

        state = signing.dumps(
            {"user_id": self.student.id, "role": "student"}, salt=OAUTH_STATE_SALT
        )
        resp = self.client.get(
            f"/api/anumati/oauth/callback/?code=fakecode123&state={state}"
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("linked=success", resp.url)

        self.student.refresh_from_db()
        self.assertTrue(self.student.anumati_linked)
        self.assertTrue(self.student.anumati_verified)  # OAuth is always verified
        self.assertEqual(self.student.anumati_locker_name, "Academic")

    def test_callback_links_institution_with_refresh_token_not_password(self):
        from django.core import signing

        from anumati_integration.views import OAUTH_STATE_SALT

        state = signing.dumps(
            {"user_id": self.admin.id, "role": "institution"}, salt=OAUTH_STATE_SALT
        )
        resp = self.client.get(
            f"/api/anumati/oauth/callback/?code=fakecode456&state={state}"
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("linked=success", resp.url)

        self.institution.refresh_from_db()
        self.assertTrue(self.institution.anumati_linked)
        self.assertTrue(self.institution.anumati_linked_via_oauth)
        self.assertIsNotNone(self.institution.anumati_refresh_token_encrypted)
        self.assertIsNone(self.institution.anumati_password_encrypted)  # never set

    def test_callback_denied_redirects_with_denied_status(self):
        resp = self.client.get("/api/anumati/oauth/callback/?error=access_denied&state=x")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("linked=denied", resp.url)

    def test_callback_rejects_tampered_state(self):
        resp = self.client.get(
            "/api/anumati/oauth/callback/?code=fakecode&state=not-a-real-signed-value"
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("linked=error", resp.url)
        self.assertIn("invalid_state", resp.url)

    def test_callback_rejects_expired_state(self):
        from django.core import signing

        from anumati_integration.views import OAUTH_STATE_MAX_AGE, OAUTH_STATE_SALT

        with patch_time_ago(OAUTH_STATE_MAX_AGE + 10):
            state = signing.dumps(
                {"user_id": self.student.id, "role": "student"}, salt=OAUTH_STATE_SALT
            )
        resp = self.client.get(f"/api/anumati/oauth/callback/?code=x&state={state}")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("expired_state", resp.url)


@contextmanager
def patch_time_ago(seconds):
    """django.core.signing timestamps itself using time.time() internally
    via TimestampSigner -- freeze it into the past so max_age rejects on
    verification, without needing a real 10-minute sleep in a test."""
    import time

    real_time = time.time
    with mock.patch("django.core.signing.time.time", return_value=real_time() - seconds):
        yield
