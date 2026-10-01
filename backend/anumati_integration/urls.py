from django.urls import path

from .views import (
    AnumatiStatusView,
    LinkInstitutionLockerView,
    LinkStudentLockerView,
    OAuthStartView,
    UnlinkStudentLockerView,
    oauth_callback,
)

urlpatterns = [
    path("status/", AnumatiStatusView.as_view(), name="anumati-status"),
    path("oauth/start/", OAuthStartView.as_view(), name="anumati-oauth-start"),
    path("oauth/callback/", oauth_callback, name="anumati-oauth-callback"),
    path("link-student-locker/", LinkStudentLockerView.as_view(), name="anumati-link-student"),
    path("unlink-student-locker/", UnlinkStudentLockerView.as_view(), name="anumati-unlink-student"),
    path(
        "link-institution-locker/",
        LinkInstitutionLockerView.as_view(),
        name="anumati-link-institution",
    ),
]
