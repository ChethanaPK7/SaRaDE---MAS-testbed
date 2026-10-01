import django_filters
from django.db.models import Count, Q
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from .models import InternshipPosting
from .serializers import (
    PostingDetailSerializer,
    PostingListSerializer,
    PostingWriteSerializer,
)


class IsFacultyOrInstitutionAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_faculty or request.user.is_institution_admin)
        )

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.institution_id == request.user.institution_id


class PostingFilter(django_filters.FilterSet):
    min_stipend = django_filters.NumberFilter(field_name="stipend", lookup_expr="gte")
    max_duration = django_filters.NumberFilter(
        field_name="duration_weeks", lookup_expr="lte"
    )
    institution = django_filters.NumberFilter(field_name="institution_id")
    lab = django_filters.CharFilter(field_name="lab", lookup_expr="icontains")
    open_only = django_filters.BooleanFilter(method="filter_open_only")

    class Meta:
        model = InternshipPosting
        fields = ["min_stipend", "max_duration", "institution", "lab", "open_only"]

    def filter_open_only(self, queryset, name, value):
        from django.utils import timezone

        if value:
            return queryset.filter(
                is_active=True, application_deadline__gte=timezone.localdate()
            )
        return queryset


class PostingViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsFacultyOrInstitutionAdmin]
    filterset_class = PostingFilter
    search_fields = ["title", "lab", "description"]

    def get_queryset(self):
        qs = InternshipPosting.objects.select_related(
            "institution", "created_by"
        ).annotate(application_count=Count("applications"))
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(lab__icontains=search)
                | Q(description__icontains=search)
            )
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return PostingListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PostingWriteSerializer
        return PostingDetailSerializer

    def perform_create(self, serializer):
        user = self.request.user
        if not (user.is_faculty or user.is_institution_admin):
            raise PermissionDenied("Only faculty or institution admins can post internships.")
        if not user.institution_id:
            raise PermissionDenied("Your account has no institution set.")
        serializer.save(institution=user.institution, created_by=user)

    def perform_update(self, serializer):
        posting = self.get_object()
        if posting.institution_id != self.request.user.institution_id:
            raise PermissionDenied("You can only edit postings from your own institution.")
        serializer.save()
