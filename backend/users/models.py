from django.contrib.auth.models import AbstractUser
from django.db import models


class Institution(models.Model):
    """A participating institution (e.g. IIIT Bangalore). Faculty and
    institution admins belong to one; students don't need to."""

    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    # Phase 2: the institution's Anumati identity and admissions locker
    # (architecture doc S3/S11). Two ways this gets populated:
    #
    #  1. OAuth (preferred, see anumati_integration/views.py:
    #     oauth_start/oauth_callback): an admin approves a consent screen
    #     on Anumati's own site and SRIP receives a refresh_token via a
    #     server-to-server code exchange -- the institution's actual
    #     Anumati password never touches SRIP at all.
    #  2. Direct entry (legacy fallback, Sprint 8's original design): the
    #     admin types their password into SRIP's link form and it's
    #     stored encrypted, because at the time there was no OAuth mode.
    #     Kept for institutions that haven't relinked yet -- see
    #     docs/oauth-locker-linking.md for the migration story.
    #
    # anumati_linked is True if EITHER path succeeded.
    anumati_username = models.CharField(max_length=150, blank=True, default="")
    anumati_password_encrypted = models.BinaryField(blank=True, null=True)
    anumati_refresh_token_encrypted = models.BinaryField(blank=True, null=True)
    anumati_admissions_locker_name = models.CharField(max_length=100, blank=True, default="")
    anumati_admissions_locker_id = models.CharField(max_length=64, blank=True, default="")
    anumati_linked_at = models.DateTimeField(null=True, blank=True)
    anumati_linked_via_oauth = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    @property
    def anumati_linked(self):
        return bool(
            self.anumati_username
            and (self.anumati_password_encrypted or self.anumati_refresh_token_encrypted)
        )

    def set_anumati_password(self, raw_password):
        from anumati_integration.crypto import encrypt_secret

        self.anumati_password_encrypted = encrypt_secret(raw_password)

    def get_anumati_password(self):
        from anumati_integration.crypto import decrypt_secret

        if not self.anumati_password_encrypted:
            return None
        return decrypt_secret(self.anumati_password_encrypted)

    def set_anumati_refresh_token(self, raw_token):
        from anumati_integration.crypto import encrypt_secret

        self.anumati_refresh_token_encrypted = encrypt_secret(raw_token)

    def get_anumati_refresh_token(self):
        from anumati_integration.crypto import decrypt_secret

        if not self.anumati_refresh_token_encrypted:
            return None
        return decrypt_secret(self.anumati_refresh_token_encrypted)


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        FACULTY = "faculty", "Faculty"
        INSTITUTION_ADMIN = "institution_admin", "Institution admin"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    institution = models.ForeignKey(
        Institution,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
        help_text="Required for faculty and institution_admin roles.",
    )

    # Phase 2 seam: populated once the student links an Anumati locker.
    # Left here (nullable, unused in Phase 1) so the schema doesn't change
    # shape when Anumati integration is added -- see architecture doc S2.
    # Anumati's own API keys most calls off locker NAME + username, not a
    # numeric id (confirmed against a live instance, see anumati_integration
    # /client.py) -- hence both fields, not just an id.
    anumati_locker_id = models.CharField(max_length=64, blank=True, default="")
    anumati_locker_name = models.CharField(max_length=100, blank=True, default="")
    # The student's Anumati account username -- may differ from their SRIP
    # username. services.py falls back to the SRIP username if this is
    # blank (pre-Sprint-8 linked accounts, or same-username convention).
    anumati_username = models.CharField(max_length=150, blank=True, default="")
    anumati_linked_at = models.DateTimeField(null=True, blank=True)
    # True only if SRIP actually confirmed this locker with Anumati (the
    # student pasted their password back for a one-time verify call).
    # False means self-attested: the student redirected out to Anumati,
    # created/confirmed a locker there, and typed the name back into SRIP
    # without SRIP ever seeing a password. See docs/sprint-8-locker-linking.md
    # for why this distinction exists -- Anumati has no OAuth callback, so
    # SRIP cannot verify a redirect-based link server-side without asking
    # for the password again.
    anumati_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} ({self.role})"

    @property
    def anumati_linked(self):
        return bool(self.anumati_locker_name)

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_faculty(self):
        return self.role == self.Role.FACULTY

    @property
    def is_institution_admin(self):
        return self.role == self.Role.INSTITUTION_ADMIN
