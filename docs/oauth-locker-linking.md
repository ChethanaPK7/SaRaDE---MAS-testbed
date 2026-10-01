# OAuth-style locker linking: design, both-sides implementation, and verification

**Status:** Designed, implemented on both sides, verified end-to-end against
a live (locally run) instance of the actual Anumati backend
(`DPI-Primitive-Jenkins-dev`, 2026-08-06 version). Not yet deployed to
the real `anumati.iiitb.ac.in` — that requires the Anumati team to accept
and deploy the `api/oauth_apps` changes described here.

## 1. The problem

Sprint 8's original locker linking had two paths, both compromises:
- **Direct entry**: the student/admin types their Anumati password into a
  SRIP form. Verified, but SRIP sees the password.
- **Self-attested redirect**: the student opens Anumati's site, links a
  locker there, comes back and *types the locker name back in by hand*.
  SRIP never sees a password, but has no way to confirm any of it —
  Anumati's real portal has no `redirect_uri`/callback support, so there
  was no way to close that loop.

Neither is what a real integration looks like. This document designs and
implements the third option: a proper OAuth-style authorization-code
flow, the same shape DigiLocker itself uses, so linking is both
**verified** and **never exposes a password to SRIP**.

## 2. Design

Three actors: **Anumati** (authorization server + locker owner),
**SRIP backend** (the "relying app" / OAuth client), and the
**student or institution admin** (resource owner, in a browser).

```
1. Browser: click "Link with Anumati" in SRIP
2. SRIP backend: GET /api/anumati/oauth/start/ (JWT-authed)
   -> returns {authorize_url} built with SRIP's client_id + a signed state
3. Browser navigates to authorize_url on Anumati
4. Anumati: login (if needed) + consent screen
   -> user picks or creates a locker, approves
5. Anumati redirects browser to SRIP's redirect_uri
   ?code=<one-time code>&state=<echoed back>
6. SRIP backend (oauth_callback): verifies state's signature, then
   server-to-server POST to Anumati /oauth/token/ with
   {code, client_id, client_secret, redirect_uri}
   -> {username, locker_id, locker_name, access_token, refresh_token}
7. SRIP stores the result (student: locker identity only, marked
   verified; institution: also the refresh_token, encrypted) and
   redirects the browser to SRIP's frontend
```

Key design choices and why:

- **`state` is signed, not stored server-side.** `django.core.signing.dumps({"user_id":..., "role":...})` on the SRIP side. No session, no database row for "pending OAuth attempts" -- the signature itself is the proof of authenticity, and a `max_age` on `loads()` handles expiry. One less thing to clean up or leak.
- **The browser never gets a client_secret.** Only `oauth_callback` (server-to-server) sends it. This is standard OAuth authorization-code-flow practice, not something specific to this design.
- **Students and institutions use the *same* flow**, differentiated only by what SRIP stores afterward. A student doesn't need a persisted token (they don't act as a "host" later); an institution does, because `services.py` needs to keep creating/closing connections on the institution's behalf indefinitely.
- **The refresh token replaces the stored password, not the encryption.** Institutions still get `anumati_refresh_token_encrypted` (Fernet, same as the old password field) — the win isn't "nothing is stored," it's that what's stored is a **scoped, revocable token**, not the institution's actual login password. If Anumati ever builds a "connected apps" revocation UI (a natural next step, and arguably required for real DPDP Consent-Manager compliance — see the architecture doc/paper), an institution can kill SRIP's access without changing their own password.
- **The consent screen is server-rendered Django templates, not the React frontend.** This was a pragmatic choice, not an aesthetic one — it's fully self-contained in the same Django app that already runs the API, needs no separate frontend build/deploy, and is the minimum needed to demonstrate and verify the flow. A production version would likely want this folded into Anumati's actual React app for visual consistency; the `/oauth/token/` API contract wouldn't need to change either way.

## 3. Anumati-side implementation

New Django app: `api/oauth_apps/` (in the `DPI-Primitive-Jenkins-dev` repo).

| File | Purpose |
|---|---|
| `models.py` | `RelyingApp` (registered client_id/hashed secret/redirect_uris) and `LinkGrant` (single-use authorization code, 5-minute expiry) |
| `views.py` | `authorize_view` (GET/POST, session-based login+consent) and `token_view` (POST, server-to-server code exchange) |
| `urls.py` | `oauth/authorize/`, `oauth/token/` |
| `templates/oauth_apps/*.html` | Minimal login, consent, and error pages |
| `admin.py` | Read-only `RelyingApp`/`LinkGrant` browsing |
| `management/commands/create_oauth_client.py` | Registers a new relying app, prints the raw secret once |

Two-line integration into the existing project:
```python
# config/settings.py, INSTALLED_APPS
'api.oauth_apps',

# api/urls.py
path("oauth/", include("api.oauth_apps.urls")),
```
Plus `python manage.py makemigrations oauth_apps && python manage.py migrate`.

### Why `authorize_view` needs a session (everything else in Anumati doesn't)

Every other endpoint in this backend is JWT-bearer, stateless, called by
scripts. This is the one place a human is looking at a browser — exactly
like Google's or GitHub's own consent screens, which also use cookies for
this step and tokens for everything after. `authorize_view` calls
Django's own `authenticate()` + `login()` to establish that session; it's
orthogonal to the JWT auth used everywhere else and doesn't change it.

## 4. SRIP-side implementation

| File | Change |
|---|---|
| `anumati_integration/client.py` | Added `build_authorize_url()`, `exchange_code()`; added `refresh_token=` as an alternative to `username`/`password` on every host-side method, plus `_refresh_access_token()` (confirmed live against `POST /auth/token/refresh/`) |
| `anumati_integration/mock_client.py` | Matching mock methods, `refresh_token=` accepted everywhere for signature compatibility |
| `anumati_integration/views.py` | `OAuthStartView` (JWT-authed, returns `{authorize_url}`), `oauth_callback` (public, verifies signed state, does the exchange, stores the result, redirects to the frontend) |
| `anumati_integration/services.py` | Every host-side call now passes `institution.get_anumati_refresh_token()` alongside the legacy password, so an OAuth-linked institution's connections work with zero password anywhere |
| `users/models.py` | `Institution` gained `anumati_refresh_token_encrypted`, `anumati_admissions_locker_id`, `anumati_linked_via_oauth` |
| `srip/settings.py` | `ANUMATI_OAUTH_CLIENT_ID`, `ANUMATI_OAUTH_CLIENT_SECRET`, `ANUMATI_OAUTH_REDIRECT_URI`, `ANUMATI_OAUTH_FRONTEND_RETURN_URL` |
| `frontend/src/pages/LinkAnumatiPage.jsx` | OAuth button is now the primary path for both roles; the old direct-entry/self-attested flow is kept as a collapsed `<details>` fallback, not removed |

### Why `oauth_start` returns JSON instead of redirecting directly

A plain `<a href>` navigation can't carry a `Authorization: Bearer` header
— and SRIP's API is JWT-only. So the frontend does a normal authenticated
`fetch`/axios call to `oauth_start`, gets `{authorize_url}` back as JSON,
and *then* does `window.location.href = authorize_url` itself. Two steps,
but the JWT-protected call and the top-level navigation never have to be
the same request.

## 5. Live verification log (2026-08-10)

Everything below was run against a real, locally-hosted instance of the
actual `DPI-Primitive-Jenkins-dev` backend — not simulated.

1. **Anumati side, in isolation**: registered a relying app
   (`create_oauth_client --name SRIP --client-id srip --redirect-uri
   http://localhost:8000/api/anumati/oauth/callback/`), then drove the
   full browser flow with `curl` + a cookie jar: fetched the authorize
   page (200, correctly showed a login form), logged in via POST
   (session established), got the consent screen back listing the real
   locker, approved with a chosen `locker_id`, and confirmed a real `302`
   redirect containing a genuine authorization code. Exchanged that code
   server-to-server and got back `{success, username, locker_id,
   locker_name, access_token, refresh_token}`. **Reused the same code a
   second time and confirmed it was rejected** (`400`, "code expired or
   already used") — single-use enforcement works.

2. **SRIP side, against the real instance, not mocked**: with
   `ANUMATI_MOCK=False` and the real `client_id`/`client_secret` from
   step 1, called SRIP's actual `OAuthStartView` (via DRF's test client
   with a real JWT), got a real `authorize_url` with a real signed
   `state`. Used `requests.Session()` to play the browser's part against
   the live Anumati instance (login, consent, approve) and captured the
   real redirect. Fed that `code`+`state` into SRIP's actual
   `oauth_callback` view (Django's test client, unauthenticated — exactly
   how a real browser lands there). Confirmed:
   - `institution.anumati_linked` → `True`
   - `institution.anumati_linked_via_oauth` → `True`
   - `institution.anumati_refresh_token_encrypted` → set
   - `institution.anumati_password_encrypted` → **`None`** — never touched
   - Redirected to `http://localhost:5173/anumati?linked=success`

3. **Closed the loop**: using that same OAuth-linked institution, called
   `applications.hooks.on_submitted()` for a real `Application` — the
   exact function the admission workflow calls on every submission. It
   used the stored refresh token (never a password) to authenticate,
   created a real screening `Connection` against the live instance, and
   `AnumatiConnectionRecord.status` came back `pending` with a real
   `connection_id`. This is the same code path Sprint 9/10 already use —
   nothing downstream had to change to support OAuth-linked institutions.

## 6. Bugs this caught

- **`SignatureExpired` is a subclass of `BadSignature`** in Django's
  `core.signing` module. The `except` clauses in `oauth_callback` were
  originally ordered `BadSignature` before `SignatureExpired`, which
  silently swallowed every expired-state case into the wrong error
  reason (`invalid_state` instead of `expired_state`). Caught by a test
  that specifically froze time past the max-age window — fixed by
  reordering the `except` clauses (subclass first).
- **`MockAnumatiClient`'s method signatures didn't accept the new
  `refresh_token=` kwarg** after `client.py` was updated — caught
  immediately by the existing (unrelated) mock-backed test suite failing
  with a `TypeError`, not by anything OAuth-specific. A reminder that the
  mock and real client need to be updated together, not just the one
  being actively worked on.

## 7. What's still open

- **Not deployed to the real `anumati.iiitb.ac.in`.** Everything here was
  verified against a locally-run copy of the same codebase. Getting this
  live requires the Anumati team to accept `api/oauth_apps`, register
  SRIP's real `client_id`, and deploy.
- **No token revocation UI on the Anumati side.** `RelyingApp` and
  `LinkGrant` exist and are admin-browsable, but there's no self-serve
  "connected apps, revoke access" page for a user yet — the natural next
  step, and the piece that would make this closer to a real DPDP Consent
  Manager (see the architecture doc's Phase 1/§15 discussion).
- **Access token refresh isn't automatic on the SRIP side beyond a single
  401 retry.** `AnumatiClient._request` retries once on a 401 by forcing
  a fresh token; there's no background renewal or expiry tracking beyond
  that. Fine for SRIP's current call pattern (a handful of calls per
  admission decision, not sustained traffic), worth revisiting if that
  changes.
- **Legacy direct-entry linking is still fully functional**, not removed
  — both for institutions that haven't relinked yet and as a fallback if
  Anumati's OAuth endpoints are ever unreachable. `anumati_linked` is
  `True` under either path; `anumati_linked_via_oauth` distinguishes
  which one produced the current link.
