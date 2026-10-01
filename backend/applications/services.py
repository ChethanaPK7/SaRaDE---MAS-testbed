"""
The admission workflow state machine.

Every status change on an Application MUST go through `transition()`. Views
never set `application.status = ...` directly -- that's what keeps illegal
transitions (e.g. rejected -> shared) impossible from the API layer, not
just hidden in the UI (see architecture doc S13, sprint 3 acceptance check).
"""
from dataclasses import dataclass
from typing import Callable, Optional

from django.db import transaction
from django.utils import timezone

from . import hooks
from .models import Application, ApplicationStatusEvent

S = Application.Status


class TransitionNotAllowed(Exception):
    """Raised when the action isn't valid from the application's current
    status. Maps to HTTP 400."""


class TransitionForbidden(Exception):
    """Raised when the actor isn't allowed to perform this action on this
    application. Maps to HTTP 403."""


def _is_reviewer_for(user, application) -> bool:
    return (
        (user.is_faculty or user.is_institution_admin)
        and user.institution_id == application.posting.institution_id
    )


def _is_owner(user, application) -> bool:
    return application.student_id == user.id


@dataclass
class ActionDef:
    from_statuses: frozenset
    to_status: str
    actor_check: Callable[[object, Application], bool]
    actor_description: str


ACTIONS: dict[str, ActionDef] = {
    "start_review": ActionDef(
        frozenset({S.SUBMITTED}), S.UNDER_REVIEW, _is_reviewer_for, "reviewer"
    ),
    "shortlist": ActionDef(
        frozenset({S.SUBMITTED, S.UNDER_REVIEW}),
        S.SHORTLISTED,
        _is_reviewer_for,
        "reviewer",
    ),
    "admit": ActionDef(
        frozenset({S.SHORTLISTED}), S.ADMITTED, _is_reviewer_for, "reviewer"
    ),
    "reject": ActionDef(
        frozenset({S.SUBMITTED, S.UNDER_REVIEW, S.SHORTLISTED}),
        S.REJECTED,
        _is_reviewer_for,
        "reviewer",
    ),
    "withdraw": ActionDef(
        frozenset({S.SUBMITTED, S.UNDER_REVIEW, S.SHORTLISTED}),
        S.WITHDRAWN,
        _is_owner,
        "the applicant",
    ),
}


def available_actions(user, application) -> list[str]:
    """Used by the API/serializer to tell the frontend which buttons to
    show, so the UI doesn't hardcode the state machine a second time."""
    out = []
    for name, action in ACTIONS.items():
        if application.status in action.from_statuses and action.actor_check(
            user, application
        ):
            out.append(name)
    return out


def transition(
    *, application: Application, action: str, actor, note: str = ""
) -> Application:
    if action not in ACTIONS:
        raise TransitionNotAllowed(f"Unknown action '{action}'.")

    action_def = ACTIONS[action]

    if application.status not in action_def.from_statuses:
        raise TransitionNotAllowed(
            f"Cannot '{action}' an application in status '{application.status}'."
        )
    if not action_def.actor_check(actor, application):
        raise TransitionForbidden(
            f"Only {action_def.actor_description} may perform '{action}'."
        )

    with transaction.atomic():
        _apply(application, action, action_def.to_status, actor, note)

        if action == "admit":
            _auto_reject_other_applicants(application, actor)
            _advance_to_documents_required(application, actor)

    return application


def _apply(application, action, to_status, actor, note):
    from_status = application.status
    application.status = to_status
    if action in ("admit", "reject"):
        application.decided_by = actor
        application.decided_at = timezone.now()
        if note:
            application.reviewer_note = note
    application.save()

    ApplicationStatusEvent.objects.create(
        application=application,
        from_status=from_status,
        to_status=to_status,
        action=action,
        actor=actor,
        note=note,
    )

    from notifications.services import notify_status_change

    notify_status_change(application, action)

    if action in ("reject", "auto_reject_not_selected"):
        hooks.on_rejected(application)


def _auto_reject_other_applicants(admitted_application: Application, actor):
    """When one applicant is admitted, every other still-open applicant to
    the same posting is auto-rejected -- this is the SRIP-side half of the
    '100 apply, 1 selected, 99 closed' scenario (architecture doc S11)."""
    siblings = Application.objects.filter(
        posting_id=admitted_application.posting_id,
        status__in=[S.SUBMITTED, S.UNDER_REVIEW, S.SHORTLISTED],
    ).exclude(id=admitted_application.id)

    for sibling in siblings:
        _apply(
            sibling,
            "auto_reject_not_selected",
            S.REJECTED,
            actor,
            note="Another applicant was admitted to this posting.",
        )


def _advance_to_documents_required(application: Application, actor):
    from_status = application.status  # ADMITTED
    application.status = S.DOCUMENTS_REQUIRED
    application.save()
    ApplicationStatusEvent.objects.create(
        application=application,
        from_status=from_status,
        to_status=S.DOCUMENTS_REQUIRED,
        action="auto_document_stage",
        actor=actor,
        note="Automatic: admission workflow requires documents next.",
    )
    from notifications.services import notify_status_change

    notify_status_change(application, "auto_document_stage")
    hooks.on_admitted(application)
