"""
Sprint 8 (original): locker linking via direct credential entry, kept as
a documented fallback -- see LinkStudentLockerView/LinkInstitutionLockerView
below and docs/sprint-8-locker-linking.md.

This update: locker linking via a real OAuth-style authorization-code
flow (oauth_start / oauth_callback below), now the PRIMARY path. See
docs/oauth-locker-linking.md for the full design and the matching
Anumati-side changes (api.oauth_apps, in the Anumati repo).

Design notes (direct-entry fallback, unchanged from Sprint 8):
  - Student passwords are NEVER persisted. The submitted password is used
    for exactly one call to Anumati (create_locker) and then discarded --
    only `anumati_username` and `anumati_locker_name` are saved on User.
  - An institution's password IS persisted (encrypted -- see
    anumati_integration/crypto.py) ONLY when linked via the fallback path.
    OAuth-linked institutions store a refresh_token instead (also
    encrypted) -- see Institution.set_anumati_refresh_token.
  - A locker-name conflict (Anumati rejecting create-locker because a
    locker with that name already exists for the user) is treated as a
    soft success: we assume the person is relinking an existing locker,
    not creating a new one, and save the reference anyway. An
    authentication failure (401/403) is treated as a hard failure -- wrong
    credentials should not silently "link" nothing.
"""
from django.conf import settings
from django.core import signing
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .client import AnumatiAPIError
from .mock_client import get_anumati_client
from .serializers import (
    AnumatiStatusSerializer,
    LinkInstitutionLockerSerializer,
    LinkStudentLockerSerializer,
)

AUTH_FAILURE_CODES = {401, 403}
OAUTH_STATE_SALT = "anumati-oauth-state"
OAUTH_STATE_MAX_AGE = 600  # 10 minutes -- covers a slow login+consent, not much more


class OAuthStartView(APIView):
    """Returns the URL to navigate to, rather than redirecting directly --
    this is a normal JWT-authenticated API call (fetch/XHR), so the
    frontend can attach its Authorization header. A raw <a href> can't do
    that for a top-level navigation, which is why this is two steps
    (fetch the URL, then navigate) instead of one."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.is_institution_admin:
            role = "institution"
            if not user.institution:
                return Response(
                    {"detail": "Your account has no institution set."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        elif user.is_student:
            role = "student"
        else:
            return Response(
                {"detail": "Only students and institution admins can link an Anumati locker."},
                status=status.HTTP_403_FORBIDDEN,
            )

        state = signing.dumps({"user_id": user.id, "role": role}, salt=OAUTH_STATE_SALT)

        client = get_anumati_client()
        authorize_url = client.build_authorize_url(
            redirect_uri=settings.ANUMATI_OAUTH_REDIRECT_URI, state=state
        )
        return Response({"authorize_url": authorize_url})


def oauth_callback(request):
    """Public, plain Django view (no DRF, no JWT) -- the browser lands
    here via a top-level GET redirect FROM Anumati, which has no way to
    attach a SRIP Authorization header. Identity is recovered entirely
    from the signed `state` value this same backend issued in
    OAuthStartView -- nothing here trusts anything from the query string
    except by verifying that signature first."""
    return_url = settings.ANUMATI_OAUTH_FRONTEND_RETURN_URL

    if request.GET.get("error"):
        return redirect(f"{return_url}?linked=denied")

    code = request.GET.get("code")
    state = request.GET.get("state")
    if not code or not state:
        return redirect(f"{return_url}?linked=error&reason=missing_code_or_state")

    try:
        payload = signing.loads(state, salt=OAUTH_STATE_SALT, max_age=OAUTH_STATE_MAX_AGE)
    except signing.SignatureExpired:
        return redirect(f"{return_url}?linked=error&reason=expired_state")
    except signing.BadSignature:
        return redirect(f"{return_url}?linked=error&reason=invalid_state")

    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        user = User.objects.get(id=payload["user_id"])
    except User.DoesNotExist:
        return redirect(f"{return_url}?linked=error&reason=unknown_user")

    client = get_anumati_client()
    try:
        result = client.exchange_code(
            code=code, redirect_uri=settings.ANUMATI_OAUTH_REDIRECT_URI
        )
    except AnumatiAPIError as exc:
        return redirect(f"{return_url}?linked=error&reason={exc}")

    if payload["role"] == "student":
        user.anumati_username = result["username"]
        user.anumati_locker_name = result["locker_name"]
        user.anumati_locker_id = str(result["locker_id"])
        user.anumati_verified = True
        user.anumati_linked_at = timezone.now()
        user.save(
            update_fields=[
                "anumati_username",
                "anumati_locker_name",
                "anumati_locker_id",
                "anumati_verified",
                "anumati_linked_at",
            ]
        )
    else:  # institution
        institution = user.institution
        if not institution:
            return redirect(f"{return_url}?linked=error&reason=no_institution")
        institution.anumati_username = result["username"]
        institution.anumati_admissions_locker_name = result["locker_name"]
        institution.anumati_admissions_locker_id = str(result["locker_id"])
        institution.set_anumati_refresh_token(result["refresh_token"])
        institution.anumati_linked_via_oauth = True
        institution.anumati_linked_at = timezone.now()
        institution.save(
            update_fields=[
                "anumati_username",
                "anumati_admissions_locker_name",
                "anumati_admissions_locker_id",
                "anumati_refresh_token_encrypted",
                "anumati_linked_via_oauth",
                "anumati_linked_at",
            ]
        )

    return redirect(f"{return_url}?linked=success")


class LinkStudentLockerView(APIView):
    """Two paths into the same endpoint, matching how a UPI handler is
    actually used:

    1. Redirect-based (primary): the student opens the real Anumati portal
       in a new tab, logs in / creates a locker there, and comes back and
       types the locker name (and their Anumati username) into this form
       with no password. SRIP never sees a password. Saved as
       anumati_verified=False -- self-attested, not confirmed.
    2. Direct-verify (optional, secondary): the student also pastes their
       password. SRIP makes one call to Anumati's create-locker to confirm
       the locker exists, then discards the password. Saved as
       anumati_verified=True.

    Path 1 exists because Anumati's real portal (a React SPA) has no
    OAuth-style redirect_uri/callback support today -- SRIP genuinely
    cannot verify a redirect-based link server-side without asking for the
    password again, so it doesn't pretend to. See
    docs/sprint-8-locker-linking.md.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not request.user.is_student:
            return Response(
                {"detail": "Only students can link a personal Anumati locker."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = LinkStudentLockerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        password = data.get("anumati_password")

        user = request.user
        warning = None
        verified = False

        if password:
            client = get_anumati_client()
            try:
                client.create_locker(
                    data["locker_name"],
                    description=f"SRIP locker for {user.username}",
                    username=data["anumati_username"],
                    password=password,
                )
                verified = True
            except AnumatiAPIError as exc:
                if exc.status_code in AUTH_FAILURE_CODES:
                    return Response(
                        {"detail": f"Could not authenticate with Anumati: {exc}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                warning = (
                    f"Anumati did not confirm a new locker was created ({exc}); "
                    f"assuming '{data['locker_name']}' already exists for this account "
                    f"and linking to it."
                )
                verified = True  # a name conflict still means the account+creds are real
        else:
            warning = (
                "Linked without verification -- SRIP could not confirm this locker "
                "exists without your password. It will still be used for future "
                "connections; if it turns out to be wrong, relink or use the "
                "optional password field to verify immediately."
            )

        user.anumati_username = data["anumati_username"]
        user.anumati_locker_name = data["locker_name"]
        user.anumati_linked_at = timezone.now()
        user.anumati_verified = verified
        user.save(
            update_fields=[
                "anumati_username",
                "anumati_locker_name",
                "anumati_linked_at",
                "anumati_verified",
            ]
        )

        return Response(
            {
                "linked": True,
                "verified": verified,
                "locker_name": user.anumati_locker_name,
                "linked_at": user.anumati_linked_at,
                "warning": warning,
            },
            status=status.HTTP_200_OK,
        )


class UnlinkStudentLockerView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        user.anumati_username = ""
        user.anumati_locker_name = ""
        user.anumati_linked_at = None
        user.anumati_verified = False
        user.save(
            update_fields=[
                "anumati_username",
                "anumati_locker_name",
                "anumati_linked_at",
                "anumati_verified",
            ]
        )
        return Response({"linked": False})


class LinkInstitutionLockerView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not request.user.is_institution_admin:
            return Response(
                {"detail": "Only an institution admin can link the institution's Anumati account."},
                status=status.HTTP_403_FORBIDDEN,
            )
        institution = request.user.institution
        if not institution:
            return Response(
                {"detail": "Your account has no institution set."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = LinkInstitutionLockerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        client = get_anumati_client()
        warning = None
        try:
            client.create_locker(
                data["locker_name"],
                description=f"SRIP admissions locker for {institution.name}",
                username=data["anumati_username"],
                password=data["anumati_password"],
            )
        except AnumatiAPIError as exc:
            if exc.status_code in AUTH_FAILURE_CODES:
                return Response(
                    {"detail": f"Could not authenticate with Anumati: {exc}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            warning = (
                f"Anumati did not confirm a new locker was created ({exc}); "
                f"assuming '{data['locker_name']}' already exists for this account "
                f"and linking to it."
            )

        institution.anumati_username = data["anumati_username"]
        institution.set_anumati_password(data["anumati_password"])
        institution.anumati_admissions_locker_name = data["locker_name"]
        institution.anumati_linked_at = timezone.now()
        institution.save(
            update_fields=[
                "anumati_username",
                "anumati_password_encrypted",
                "anumati_admissions_locker_name",
                "anumati_linked_at",
            ]
        )

        return Response(
            {
                "linked": True,
                "locker_name": institution.anumati_admissions_locker_name,
                "linked_at": institution.anumati_linked_at,
                "warning": warning,
            },
            status=status.HTTP_200_OK,
        )


class AnumatiStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        institution = user.institution

        payload = {
            "user_linked": user.anumati_linked,
            "user_verified": user.anumati_verified,
            "user_locker_name": user.anumati_locker_name,
            "user_linked_at": user.anumati_linked_at,
            "institution_linked": institution.anumati_linked if institution else None,
            "institution_locker_name": (
                institution.anumati_admissions_locker_name if institution else None
            ),
            "institution_linked_at": institution.anumati_linked_at if institution else None,
            "institution_linked_via_oauth": (
                institution.anumati_linked_via_oauth if institution else None
            ),
            "portal_url": settings.ANUMATI_PORTAL_URL,
        }
        return Response(AnumatiStatusSerializer(payload).data)
