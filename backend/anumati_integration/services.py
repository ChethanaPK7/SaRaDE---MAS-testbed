"""
High-level Anumati operations, one function per workflow moment. These are
what applications/hooks.py calls -- hooks.py itself stays free of any
Anumati-specific code (client, field names, request shapes); it only calls
these three functions.

Each function is defensive: if the Anumati call fails, it records a
`failed` AnumatiConnectionRecord and logs, but does NOT raise -- a
transient Anumati outage should not block a student from submitting an
application or a reviewer from admitting someone. Reconciliation for
failed records is a Phase 2 follow-up (a retry/sync job), not handled yet.
"""
import logging
from datetime import timedelta

from django.utils import timezone

from .client import AnumatiAPIError
from .mock_client import get_anumati_client
from .models import AnumatiConnectionRecord

logger = logging.getLogger("srip.anumati_integration.services")

SCREENING_CONNECTION_TYPE_NAME = "SRIP Application Screening"
ADMISSION_CONNECTION_TYPE_NAME = "SRIP Internship - Active"


def _student_ready(student):
    return student.anumati_linked


def _institution_ready(institution):
    return bool(
        institution
        and institution.anumati_admissions_locker_name
        and institution.anumati_linked
    )


def create_screening_connection(application):
    """Stage 1 fan-out (architecture doc S11): one connection per
    applicant, forward-only terms, short validity. Called from
    hooks.on_submitted."""
    student = application.student
    institution = application.posting.institution

    if not (_student_ready(student) and _institution_ready(institution)):
        logger.info(
            "Skipping Anumati screening connection for application=%s: "
            "student or institution hasn't linked a locker yet.",
            application.id,
        )
        return None

    record = AnumatiConnectionRecord.objects.create(
        application=application, purpose=AnumatiConnectionRecord.Purpose.SCREENING
    )
    client = get_anumati_client()
    institution_password = institution.get_anumati_password()
    institution_refresh_token = institution.get_anumati_refresh_token()
    try:
        ct_id = client.create_connection_type(
            connection_name=SCREENING_CONNECTION_TYPE_NAME,
            connection_description="Screening documents for internship applicants",
            locker_name=institution.anumati_admissions_locker_name,
            validity_iso=application.posting.application_deadline.isoformat() + "T00:00:00Z",
            username=institution.anumati_username,
            password=institution_password,
            refresh_token=institution_refresh_token,
            directions=[
                {
                    "from": "GUEST",
                    "to": "HOST",
                    "obligations": [
                        {
                            "labelName": doc,
                            "labelDescription": doc.replace("_", " "),
                            "typeOfAction": "document",
                            "typeOfSharing": "share",
                            "purpose": "Internship application screening",
                            "hostPermissions": ["view"],
                        }
                        for doc in (application.posting.required_documents or ["resume"])
                    ],
                    "permissions": {"canShareMoreData": False, "canDownloadData": False},
                    "forbidden": [],
                }
            ],
        )
        connection_id = client.create_connection(
            connection_type_id=ct_id,
            connection_name=f"Screening-{application.id}",
            connection_description=f"Screening for application {application.id}",
            host_locker_name=institution.anumati_admissions_locker_name,
            guest_locker_name=student.anumati_locker_name,
            host_username=institution.anumati_username,
            guest_username=student.anumati_username or student.username,
            password=institution_password,
            refresh_token=institution_refresh_token,
        )
    except AnumatiAPIError as exc:
        record.status = AnumatiConnectionRecord.Status.FAILED
        record.error_detail = str(exc)
        record.save()
        logger.error("Anumati screening connection failed for application=%s: %s", application.id, exc)
        return record

    record.status = AnumatiConnectionRecord.Status.PENDING  # awaits student consent
    record.anumati_connection_type_id = str(ct_id)
    record.anumati_connection_id = str(connection_id)
    record.valid_until = timezone.make_aware(
        timezone.datetime.combine(application.posting.application_deadline, timezone.datetime.min.time())
    )
    record.save()
    return record


def close_screening_connection(application, *, reason=""):
    """Called for both the 99 rejected applicants and (separately) the 1
    admitted applicant, whose screening connection is superseded by the
    admission connection -- see architecture doc S11."""
    record = (
        application.anumati_records.filter(purpose=AnumatiConnectionRecord.Purpose.SCREENING)
        .exclude(status=AnumatiConnectionRecord.Status.CLOSED)
        .first()
    )
    if not record or not record.anumati_connection_id:
        return  # never got far enough to have a live connection to close

    institution = application.posting.institution
    client = get_anumati_client()
    try:
        client.close_connection_host(
            record.anumati_connection_id,
            username=institution.anumati_username,
            password=institution.get_anumati_password(),
            refresh_token=institution.get_anumati_refresh_token(),
        )
    except AnumatiAPIError as exc:
        logger.error(
            "Failed to close screening connection %s for application=%s: %s",
            record.anumati_connection_id,
            application.id,
            exc,
        )
        return

    record.status = AnumatiConnectionRecord.Status.CLOSED
    record.error_detail = reason
    record.save()


def create_admission_connection(application):
    """Stage 2 (architecture doc S11): bidirectional connection for the
    single admitted applicant, live until internship end + grace window.
    Called from hooks.on_admitted, AFTER the screening connection has been
    closed."""
    student = application.student
    institution = application.posting.institution

    if not (_student_ready(student) and _institution_ready(institution)):
        logger.info(
            "Skipping Anumati admission connection for application=%s: "
            "student or institution hasn't linked a locker yet.",
            application.id,
        )
        return None

    posting = application.posting
    end_date = posting.end_date or (posting.start_date or timezone.localdate())
    valid_until_date = end_date + timedelta(days=30)  # grace window, doc S11

    record = AnumatiConnectionRecord.objects.create(
        application=application, purpose=AnumatiConnectionRecord.Purpose.ADMISSION_ACTIVE
    )
    client = get_anumati_client()
    institution_password = institution.get_anumati_password()
    institution_refresh_token = institution.get_anumati_refresh_token()
    try:
        ct_id = client.create_connection_type(
            connection_name=ADMISSION_CONNECTION_TYPE_NAME,
            connection_description="Bidirectional document exchange for the active internship",
            locker_name=institution.anumati_admissions_locker_name,
            validity_iso=valid_until_date.isoformat() + "T00:00:00Z",
            username=institution.anumati_username,
            password=institution_password,
            refresh_token=institution_refresh_token,
            directions=[
                {
                    "from": "GUEST",
                    "to": "HOST",
                    "obligations": [
                        {
                            "labelName": "bank_details",
                            "labelDescription": "Bank details for stipend disbursal",
                            "typeOfAction": "document",
                            "typeOfSharing": "share",
                            "purpose": "Stipend disbursal",
                            "hostPermissions": ["view"],
                        }
                    ],
                    "permissions": {"canShareMoreData": True, "canDownloadData": False},
                    "forbidden": [],
                },
                {
                    "from": "HOST",
                    "to": "GUEST",
                    "obligations": [
                        {
                            "labelName": "internship_certificate",
                            "labelDescription": "Internship completion certificate",
                            "typeOfAction": "document",
                            "typeOfSharing": "share",
                            "purpose": "Proof of internship completion",
                            "hostPermissions": ["download"],
                        }
                    ],
                    "permissions": {"canShareMoreData": True, "canDownloadData": True},
                    "forbidden": [],
                },
            ],
        )
        connection_id = client.create_connection(
            connection_type_id=ct_id,
            connection_name=f"Admission-{application.id}",
            connection_description=f"Active internship connection for application {application.id}",
            host_locker_name=institution.anumati_admissions_locker_name,
            guest_locker_name=student.anumati_locker_name,
            host_username=institution.anumati_username,
            guest_username=student.anumati_username or student.username,
            password=institution_password,
            refresh_token=institution_refresh_token,
        )
    except AnumatiAPIError as exc:
        record.status = AnumatiConnectionRecord.Status.FAILED
        record.error_detail = str(exc)
        record.save()
        logger.error("Anumati admission connection failed for application=%s: %s", application.id, exc)
        return record

    record.status = AnumatiConnectionRecord.Status.PENDING  # awaits student consent
    record.anumati_connection_type_id = str(ct_id)
    record.anumati_connection_id = str(connection_id)
    record.valid_until = timezone.make_aware(
        timezone.datetime.combine(valid_until_date, timezone.datetime.min.time())
    )
    record.save()
    return record
