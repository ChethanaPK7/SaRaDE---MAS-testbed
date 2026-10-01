from rest_framework import serializers

from users.serializers import InstitutionSerializer, UserSerializer

from .models import InternshipPosting


class PostingListSerializer(serializers.ModelSerializer):
    institution = InstitutionSerializer(read_only=True)
    application_count = serializers.IntegerField(read_only=True)
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = InternshipPosting
        fields = [
            "id",
            "title",
            "lab",
            "institution",
            "duration_weeks",
            "stipend",
            "application_deadline",
            "is_open",
            "application_count",
        ]


class PostingDetailSerializer(serializers.ModelSerializer):
    institution = InstitutionSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    is_open = serializers.BooleanField(read_only=True)
    application_count = serializers.IntegerField(read_only=True)
    has_applied = serializers.SerializerMethodField()

    class Meta:
        model = InternshipPosting
        fields = [
            "id",
            "title",
            "lab",
            "institution",
            "created_by",
            "description",
            "eligibility",
            "duration_weeks",
            "stipend",
            "application_deadline",
            "start_date",
            "end_date",
            "required_documents",
            "is_active",
            "is_open",
            "application_count",
            "has_applied",
            "created_at",
        ]
        read_only_fields = ["institution", "created_by"]

    def get_has_applied(self, obj):
        user = self.context["request"].user
        if not getattr(user, "is_student", False):
            return None
        return obj.applications.filter(student=user).exists()


class PostingWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternshipPosting
        fields = [
            "id",
            "title",
            "lab",
            "description",
            "eligibility",
            "duration_weeks",
            "stipend",
            "application_deadline",
            "start_date",
            "end_date",
            "required_documents",
            "is_active",
        ]
