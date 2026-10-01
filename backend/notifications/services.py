from .models import Notification

_MESSAGES = {
    "start_review": "Your application to {posting} is now under review.",
    "shortlist": "You've been shortlisted for {posting}.",
    "admit": "Congratulations -- you've been admitted to {posting}.",
    "reject": "Your application to {posting} was not selected.",
    "auto_reject_not_selected": "Your application to {posting} was not selected.",
    "withdraw": "Your application to {posting} has been withdrawn.",
    "auto_document_stage": "Documents are now required to complete your admission to {posting}.",
}

_REVIEWER_MESSAGES = {
    "withdraw": "{student} withdrew their application to {posting}.",
}


def notify_status_change(application, action: str):
    posting_title = application.posting.title
    student_message = _MESSAGES.get(action)
    if student_message:
        Notification.objects.create(
            recipient=application.student,
            application=application,
            message=student_message.format(posting=posting_title),
        )

    reviewer_message = _REVIEWER_MESSAGES.get(action)
    if reviewer_message and application.posting.created_by_id:
        Notification.objects.create(
            recipient=application.posting.created_by,
            application=application,
            message=reviewer_message.format(
                posting=posting_title, student=application.student.username
            ),
        )
