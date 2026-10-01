"""
Thin wrapper around Anumati's HTTP API. One method per endpoint SRIP needs.

Request/response shapes were verified live against two separate running
Anumati instances:
  - 2026-07-31, against the repo originally shared (root-mounted endpoints,
    HTTP Basic auth per request).
  - 2026-08-06, against a substantially rewritten repo
    (DPI-Primitive-Jenkins-dev) -- this is what's now live at
    https://anumati.iiitb.ac.in. THIS FILE TARGETS THE 2026-08-06 VERSION.

What changed between the two, confirmed live (not inferred from source):
  1. Auth is now JWT bearer tokens (rest_framework_simplejwt), not HTTP
     Basic. A client must POST username+password to `/auth/login/` once
     to get an access token, then send `Authorization: Bearer <token>` on
     every subsequent call. This directly closes part of the "Phase 0:
     protocol hardening" gap the architecture doc originally flagged
     (SRIP no longer has to send a literal password on every single
     request -- only once per login).
  2. Every endpoint moved under a namespaced path: `/auth/`, `/locker/`,
     `/connectionType/`, `/connection/` -- no longer mounted at the site
     root. Also partially closes the "unversioned, unnamespaced endpoints"
     gap (namespaced now; still not version-prefixed, e.g. no `/v1/`).
  3. `create-connection-type-and-terms` STILL does not return the new
     connection_type_id in its response -- this gotcha survived the
     rewrite. `create_connection_type()` below still does the follow-up
     lookup internally.

Because the public methods on this class kept the same names and
signatures across both versions, nothing in `services.py` or `views.py`
had to change when this file was updated -- that isolation is the entire
point of having an adapter class instead of calling Anumati directly from
business logic (see the architecture doc, "one adapter, not scattered
calls").
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger("srip.anumati_integration.client")


class AnumatiAPIError(Exception):
    def __init__(self, message, status_code=None, payload=None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class AnumatiClient:
    def __init__(self, base_url=None, host_username=None, host_password=None, timeout=10):
        self.base_url = (base_url or settings.ANUMATI_BASE_URL).rstrip("/")
        self.host_username = host_username or settings.ANUMATI_HOST_USERNAME
        self.host_password = host_password or settings.ANUMATI_HOST_PASSWORD
        self.timeout = timeout
        # Access tokens are cheap to fetch and short-lived; cache per
        # (username) for the lifetime of this client instance so a service
        # function making 2-3 calls in a row (e.g. create_connection_type
        # then create_connection) doesn't log in again for each one. No
        # refresh-token handling -- a fresh AnumatiClient is created per
        # service call (see mock_client.get_anumati_client), so tokens
        # never live long enough to need refreshing.
        self._tokens = {}
        self._refresh_tokens = {}

    def _url(self, path):
        return f"{self.base_url}/{path.strip('/')}/"

    def _login(self, username, password):
        try:
            resp = requests.post(
                self._url("auth/login"),
                json={"username": username, "password": password},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise AnumatiAPIError(f"Network error logging in to Anumati: {exc}") from exc

        try:
            data = resp.json()
        except ValueError:
            data = {"raw": resp.text}

        if resp.status_code >= 400 or data.get("success") is False:
            raise AnumatiAPIError(
                data.get("error") or "Anumati login failed",
                status_code=resp.status_code,
                payload=data,
            )
        return data["access"]

    def _refresh_access_token(self, refresh_token):
        """The OAuth-linked path (see oauth_start/oauth_callback in
        views.py): no password involved at all, just exchanging a
        long-lived refresh token (obtained once via the authorization-code
        flow) for a short-lived access token. Confirmed live against
        POST /auth/token/refresh/ -- plain SimpleJWT, returns {"access":
        ...} with no "success" wrapper, unlike this app's own endpoints."""
        try:
            resp = requests.post(
                self._url("auth/token/refresh"),
                json={"refresh": refresh_token},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise AnumatiAPIError(f"Network error refreshing Anumati token: {exc}") from exc

        try:
            data = resp.json()
        except ValueError:
            data = {"raw": resp.text}

        if resp.status_code >= 400 or "access" not in data:
            raise AnumatiAPIError(
                data.get("detail") or "Anumati token refresh failed",
                status_code=resp.status_code,
                payload=data,
            )
        return data["access"]

    def _get_token(self, username=None, password=None, refresh_token=None, force_refresh=False):
        """Two independent auth modes, dispatched on which arguments are
        given: refresh_token (preferred -- issued once via the OAuth
        authorization-code flow, no password ever stored) or
        username+password (the older, still-supported fallback for
        accounts that haven't relinked via OAuth yet)."""
        if refresh_token:
            key = ("refresh", refresh_token)
            if force_refresh or key not in self._tokens:
                self._tokens[key] = self._refresh_access_token(refresh_token)
            return self._tokens[key]

        key = ("password", username)
        if force_refresh or key not in self._tokens:
            self._tokens[key] = self._login(username, password)
        return self._tokens[key]

    def _request(self, method, path, username=None, password=None, refresh_token=None, **kwargs):
        headers = kwargs.pop("headers", {})
        token = self._get_token(username, password, refresh_token)
        headers["Authorization"] = f"Bearer {token}"

        try:
            resp = requests.request(
                method, self._url(path), headers=headers, timeout=self.timeout, **kwargs
            )
            if resp.status_code == 401:
                # token may have expired mid-session; retry once with a
                # fresh login/refresh before giving up.
                token = self._get_token(
                    username, password, refresh_token, force_refresh=True
                )
                headers["Authorization"] = f"Bearer {token}"
                resp = requests.request(
                    method, self._url(path), headers=headers, timeout=self.timeout, **kwargs
                )
        except requests.RequestException as exc:
            raise AnumatiAPIError(f"Network error calling {path}: {exc}") from exc

        try:
            data = resp.json()
        except ValueError:
            data = {"raw": resp.text}

        if resp.status_code >= 400 or data.get("success") is False:
            raise AnumatiAPIError(
                data.get("error") or data.get("message") or "Anumati call failed",
                status_code=resp.status_code,
                payload=data,
            )
        return data

    # -- host-side calls (SRIP acts as the institution) ------------------

    def create_locker(self, name, description="", username=None, password=None, refresh_token=None):
        username = username or self.host_username
        password = password or self.host_password
        return self._request(
            "POST",
            "locker/create",
            username,
            password,
            refresh_token=refresh_token,
            data={"name": name, "description": description},
        )

    def create_connection_type(
        self,
        *,
        connection_name,
        connection_description,
        locker_name,
        validity_iso,
        directions,
        post_conditions=None,
        username=None,
        password=None,
        refresh_token=None,
    ):
        """Creates the ConnectionType + ConnectionTerms, then looks up and
        returns its id (see module docstring -- the create call still
        doesn't return one).

        Idempotent by design: SRIP is meant to register a connection type
        ONCE per purpose and reuse it across every application (the
        architecture doc's "pre-registered template" pattern) -- so the
        second and every subsequent call here is *expected* to hit
        Anumati's own uniqueness constraint (name + locker + direction),
        confirmed live to return 400 with an "already exists" message. That
        specific conflict is treated as success-via-lookup, not an error;
        any other failure still raises.
        """
        username = username or self.host_username
        password = password or self.host_password
        payload = {
            "connectionName": connection_name,
            "connectionDescription": connection_description,
            "lockerName": locker_name,
            "validity": validity_iso,
            "postConditions": post_conditions or {},
            "directions": directions,
        }
        try:
            self._request(
                "POST", "connectionType/create-connection-type-and-terms", username, password,
                refresh_token=refresh_token, json=payload,
            )
        except AnumatiAPIError as exc:
            already_exists = (
                exc.status_code == 400
                and exc.payload
                and "already exists" in str(exc.payload.get("error", ""))
            )
            if not already_exists:
                raise
            logger.info(
                "Connection type '%s' already registered in '%s' -- reusing it.",
                connection_name,
                locker_name,
            )
        return self._lookup_connection_type_id(
            connection_name, locker_name, username, password, refresh_token
        )

    def _lookup_connection_type_id(
        self, connection_name, locker_name, username, password, refresh_token=None
    ):
        data = self._request(
            "GET",
            "connectionType/get_connection_types_by_locker",
            username,
            password,
            refresh_token=refresh_token,
            params={"locker_name": locker_name, "username": username},
        )
        for ct in data.get("connection_types", []):
            if ct["connection_type_name"] == connection_name:
                return ct["connection_type_id"]
        raise AnumatiAPIError(
            f"Created connection type '{connection_name}' but couldn't find it on lookup."
        )

    def create_connection(
        self,
        *,
        connection_type_id,
        connection_name,
        host_locker_name,
        guest_locker_name,
        host_username,
        guest_username,
        connection_description="",
        password=None,
        refresh_token=None,
    ):
        """Called as the host (institution). `password` defaults to the
        institution service account's password; pass `refresh_token`
        instead once the institution has linked via OAuth (see
        oauth_callback in views.py) -- no password needed at all then."""
        password = password or self.host_password
        data = self._request(
            "POST",
            "connection/create",
            host_username,
            password,
            refresh_token=refresh_token,
            data={
                "connection_type_id": connection_type_id,
                "connection_name": connection_name,
                "connection_description": connection_description,
                "host_locker_name": host_locker_name,
                "guest_locker_name": guest_locker_name,
                "host_user_username": host_username,
                "guest_user_username": guest_username,
            },
        )
        return data["id"]

    def close_connection_host(
        self, connection_id, username=None, password=None, refresh_token=None
    ):
        username = username or self.host_username
        password = password or self.host_password
        return self._request(
            "POST",
            "connection/close-host",
            username,
            password,
            refresh_token=refresh_token,
            data={"connection_id": connection_id},
        )

    # -- OAuth-style locker linking (SRIP acts as itself, via its own
    # registered client_id/client_secret -- never a user's credentials).
    # See docs/oauth-locker-linking.md for the full design and
    # anumati_integration/views.py's oauth_start/oauth_callback for how
    # these two methods get used. ---------------------------------------

    def build_authorize_url(self, *, redirect_uri, state, client_id=None):
        from urllib.parse import urlencode

        client_id = client_id or settings.ANUMATI_OAUTH_CLIENT_ID
        qs = urlencode(
            {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "state": state,
                "scope": "locker_link",
            }
        )
        return f"{self.base_url}/oauth/authorize/?{qs}"

    def exchange_code(self, *, code, redirect_uri, client_id=None, client_secret=None):
        """Server-to-server only -- the browser never sees client_secret.
        Returns {username, locker_id, locker_name, access_token,
        refresh_token} on success. The refresh_token is what gets stored
        (encrypted) for an institution instead of a raw password; students
        don't need one persisted at all, just the confirmed locker
        identity."""
        client_id = client_id or settings.ANUMATI_OAUTH_CLIENT_ID
        client_secret = client_secret or settings.ANUMATI_OAUTH_CLIENT_SECRET
        try:
            resp = requests.post(
                self._url("oauth/token"),
                json={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise AnumatiAPIError(f"Network error exchanging code: {exc}") from exc

        try:
            data = resp.json()
        except ValueError:
            data = {"raw": resp.text}

        if resp.status_code >= 400 or data.get("success") is False:
            raise AnumatiAPIError(
                data.get("error") or "Code exchange failed",
                status_code=resp.status_code,
                payload=data,
            )
        return data

    # -- guest-side call, included for demo/test scripts only ------------

    def give_consent(
        self,
        *,
        connection_name,
        connection_type_id,
        guest_username,
        guest_password,
        guest_lockername,
        host_username,
        host_lockername,
        consent=True,
    ):
        """In production this is called from inside Anumati's own consent
        screen under the student's session -- SRIP's backend does not hold
        student passwords. Present here only for driving demo/test flows
        end-to-end without a human in the loop."""
        return self._request(
            "POST",
            "connection/give-consent",
            guest_username,
            guest_password,
            data={
                "connection_name": connection_name,
                "connection_type_id": connection_type_id,
                "guest_username": guest_username,
                "guest_lockername": guest_lockername,
                "host_username": host_username,
                "host_lockername": host_lockername,
                "consent": consent,
            },
        )
