from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from . import hooks
from .models import Application
from .serializers import (
    ApplicationCreateSerializer,
    ApplicationDetailSerializer,
    ApplicationSerializer,
    TransitionSerializer,
)
from .services import TransitionForbidden, TransitionNotAllowed, transition


class ApplicationViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]  # no direct PATCH/PUT/DELETE

    def get_queryset(self):
        user = self.request.user
        qs = Application.objects.select_related(
            "student", "posting", "posting__institution", "decided_by"
        ).prefetch_related("events", "events__actor")

        if user.is_student:
            qs = qs.filter(student=user)
        elif user.is_faculty or user.is_institution_admin:
            qs = qs.filter(posting__institution_id=user.institution_id)
        else:
            qs = qs.none()

        posting_id = self.request.query_params.get("posting")
        if posting_id:
            qs = qs.filter(posting_id=posting_id)
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return ApplicationCreateSerializer
        if self.action == "retrieve":
            return ApplicationDetailSerializer
        return ApplicationSerializer

    def create(self, request, *args, **kwargs):
        if not request.user.is_student:
            raise PermissionDenied("Only students can apply to postings.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = serializer.save(student=request.user)
        hooks.on_submitted(application)
        out = ApplicationSerializer(application, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        application = self.get_object()
        serializer = TransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            transition(
                application=application,
                action=serializer.validated_data["action"],
                actor=request.user,
                note=serializer.validated_data.get("note", ""),
            )
        except TransitionNotAllowed as exc:
            raise ValidationError(str(exc))
        except TransitionForbidden as exc:
            raise PermissionDenied(str(exc))

        application.refresh_from_db()
        out = ApplicationDetailSerializer(application, context={"request": request})
        return Response(out.data)
