# SRIP — Student Research Internship Portal

Phase 1 (standalone internship search/apply/admission workflow) **and** a
working Phase 2 slice (Anumati integration, currently running against a
mock client by default — see below).

```
srip/
├── backend/    Django + DRF API
│   ├── users/                 accounts, roles, institutions
│   ├── postings/               internship postings + search
│   ├── applications/           the guarded admission state machine
│   ├── notifications/          in-app notifications
│   └── anumati_integration/    Phase 2: screening + admission connections
├── frontend/   React (Vite) SPA
└── docker-compose.yml
```

## Why the code is organized this way

- `applications/services.py` is the **only** place `Application.status`
  changes. Every transition is checked against `ACTIONS` (who can do it,
  from which states) before it's applied — illegal transitions are
  impossible from the API, not just hidden in the UI.
- `applications/hooks.py` bridges to `anumati_integration` at exactly three
  points (`on_submitted`, `on_admitted`, `on_rejected`). Nothing else in
  `applications` imports anything Anumati-related.
- Admitting one applicant automatically rejects every other open applicant
  to the same posting and advances the admitted one to
  `documents_required` — this is the SRIP-side half of the "100 apply, 1
  selected" scenario from the architecture doc, and it's what drives
  `anumati_integration` to close 99 screening connections and open 1
  bidirectional admission connection.

## Phase 2: real client, mocked by default

`anumati_integration/client.py` is a real HTTP client whose request/response
shapes were verified live against a running Anumati instance (not guessed
from serializer code — see the architecture doc §15 for the full findings).
`anumati_integration/mock_client.py` provides `MockAnumatiClient` with an
identical interface, so tests and local dev need no network access.

```bash
# .env (backend)
ANUMATI_MOCK=True            # default -- MockAnumatiClient, no network
# ANUMATI_MOCK=False
# ANUMATI_BASE_URL=http://localhost:9000
# ANUMATI_HOST_USERNAME=your_institution_anumati_username
# ANUMATI_HOST_PASSWORD=your_institution_anumati_password
```

To actually point this at a real Anumati instance, an institution also
needs `Institution.anumati_username` and
`Institution.anumati_admissions_locker_name` set (currently only done by
`seed_demo`, for the demo institution) — real per-institution setup UI is
still a Phase 2 sprint-8 item (locker linking), not built yet.

## Quick start (local, no Docker)

### Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py seed_demo          # 1 posting, 100 applicants, 1 admitted,
                                     # + mocked Anumati screening/admission
                                     # connections for all of them
python manage.py runserver
```
API is now at `http://localhost:8000/api/`. Health check: `GET /api/health/`.

Demo logins created by `seed_demo` (password `demo1234` for all):
- `faculty_demo` — reviewer, can shortlist/admit/reject
- `student_demo_001` — the applicant who ends up admitted (`documents_required`,
  with a mock Anumati admission connection open in `/admin/`)
- `student_demo_002` … `student_demo_100` — auto-rejected applicants
  (mock screening connections closed)

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # points at http://localhost:8000/api by default
npm run dev
```
App is now at `http://localhost:5173/`.

## Quick start (Docker)

```bash
docker compose up --build
```
Frontend on `http://localhost/`, backend on `http://localhost:8000/`. Run
migrations/seed once the backend container is up:

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_demo
```

## Running tests

```bash
cd backend && source venv/bin/activate
python manage.py test applications anumati_integration -v 2
```
`applications`: illegal transitions, cross-institution reviewer permissions,
student self-admit prevention, the auto-reject-99 behavior, audit trail.
`anumati_integration`: submission creates a pending screening record for
every applicant, admitting one closes all screening records and opens
exactly one bidirectional admission record, an unlinked
student/institution is skipped gracefully (never blocks the SRIP workflow),
and the Sprint 8 linking endpoints (permission checks, password-never-
persisted for students, password-encrypted-at-rest for institutions,
status reflects link state correctly).

## Locker linking

`/anumati` in the frontend nav. **Primary path (OAuth-style, verified,
no password ever reaches SRIP):** click "Link with Anumati" — SRIP
redirects to Anumati's own login+consent page, the user approves there,
and SRIP receives a one-time code it exchanges server-to-server for the
locker's identity (and, for institutions, a revocable refresh token
instead of a password). Full design, both-sides implementation, and a
live verification log against the real Anumati backend:
[`docs/oauth-locker-linking.md`](docs/oauth-locker-linking.md).

**Fallback path (Sprint 8's original design, still functional):**
direct credential entry, collapsed under "link manually" on the same
page — a student's password is used once and discarded; an institution's
is stored encrypted (`ANUMATI_CREDENTIAL_KEY`). Kept for institutions
that haven't relinked via OAuth yet, or if Anumati's OAuth endpoints are
unreachable. Full documentation:
[`docs/sprint-8-locker-linking.md`](docs/sprint-8-locker-linking.md).

Note: the OAuth flow requires the matching `api/oauth_apps` addition on
the Anumati side (not yet deployed to the real `anumati.iiitb.ac.in` —
see the doc above). Set `ANUMATI_MOCK=True` (the default) to exercise the
whole flow locally with no real Anumati instance at all.

## What's deliberately not here yet

- **Status sync job** (sprint 11) — polling Anumati for consent-given /
  connection-live status and reflecting it back into `Application.status`
  (`documents_required` → `documents_shared`). Right now a connection is
  created and left `pending`; nothing advances it further yet.
- **Reviewer document view** (sprint 11) — calling `access-resource-v2`
  server-side so a reviewer can view a shared document without SRIP ever
  touching the raw bytes.
- **Reverse-direction certificate delivery** (sprint 12) — the admission
  connection's `HOST→GUEST` terms exist and were included when the
  connection type was created, but nothing yet calls
  `share_confer_resource_reverse_v2` to actually issue a certificate
  through them.

## API surface (Phase 1)

| Method | Path | Notes |
|---|---|---|
| POST | `/api/auth/register/` | role: student / faculty / institution_admin |
| POST | `/api/auth/login/` | returns JWT access + refresh |
| POST | `/api/auth/login/refresh/` | |
| GET | `/api/auth/me/` | |
| GET | `/api/auth/institutions/` | for sign-up dropdown |
| GET/POST | `/api/postings/` | filter: `search`, `open_only`, `institution`, `min_stipend`, `max_duration`, `lab` |
| GET/PATCH | `/api/postings/{id}/` | |
| GET/POST | `/api/applications/` | filter: `posting`, `status` |
| GET | `/api/applications/{id}/` | includes audit trail (`events`) |
| POST | `/api/applications/{id}/transition/` | `{"action": "shortlist"\|"admit"\|"reject"\|"withdraw"\|"start_review", "note": "..."}` |
| GET | `/api/notifications/` | |
| POST | `/api/notifications/{id}/mark_read/` | |
| POST | `/api/notifications/mark-all-read/` | |

Full request/response shapes are visible directly from DRF's browsable API
if you open any of these URLs in a browser while logged in via session auth,
or via the Django admin at `/admin/`.
