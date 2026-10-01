"""
Phase 2 integration seam.

`applications` itself still imports nothing Anumati-related -- these hook
bodies are the ONLY place that bridges to `anumati_integration`. Everything
here is defensive: `anumati_integration.services` functions never raise
(they log and record failure), so a broken or unreachable Anumati instance
degrades to "no document connection was opened yet," not a 500 on the
student's or reviewer's action.
"""
import logging

logger = logging.getLogger("srip.applications.hooks")


def on_submitted(application):
    """Fan-out (architecture doc S11, Stage 1): create the per-applicant
    screening connection, forward-only terms."""
    from anumati_integration.services import create_screening_connection

    create_screening_connection(application)


def on_admitted(application):
    """Fan-in (architecture doc S11): close the selected applicant's
    screening connection (it's superseded, not extended) and open the
    bidirectional admission connection. The 99 non-selected applicants are
    handled by on_rejected, called separately for each by
    applications/services.py's auto-reject."""
    from anumati_integration.services import close_screening_connection, create_admission_connection

    close_screening_connection(application, reason="Superseded by admission connection.")
    create_admission_connection(application)


def on_rejected(application):
    """Close this applicant's screening connection -- covers both a direct
    reject and the auto-reject of the 99 non-selected applicants when
    someone else is admitted."""
    from anumati_integration.services import close_screening_connection

    close_screening_connection(application, reason="Applicant was not selected.")

