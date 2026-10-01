from rest_framework import serializers

from postings.serializers import PostingListSerializer
from users.serializers import UserSerializer

from .models import Application, ApplicationStatusEvent
from .services import available_actions


class ApplicationEventSerializer(serializers.ModelSerializer):
    actor = UserSerializer(read_only=True)

    class Meta:
        model = ApplicationStatusEvent
        fields = ["from_status", "to_status", "action", "actor", "note", "created_at"]


class ApplicationSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    posting = PostingListSerializer(read_only=True)
    available_actions = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            "id",
            "student",
            "posting",
            "status",
            "cover_note",
            "reviewer_note",
            "decided_by",
            "decided_at",
            "submitted_at",
            "updated_at",
            "available_actions",
        ]
        read_only_fields = ["status", "reviewer_note", "decided_by", "decided_at"]

    def get_available_actions(self, obj):
        user = self.context["request"].user
        return available_actions(user, obj)


class ApplicationDetailSerializer(ApplicationSerializer):
    events = ApplicationEventSerializer(many=True, read_only=True)

    class Meta(ApplicationSerializer.Meta):
        fields = ApplicationSerializer.Meta.fields + ["events"]


class ApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ["id", "posting", "cover_note"]

    def validate_posting(self, posting):
        if not posting.is_open:
            raise serializers.ValidationError("This posting is closed to new applications.")
        return posting


class TransitionSerializer(serializers.Serializer):
    action = serializers.CharField()
    note = serializers.CharField(required=False, allow_blank=True, default="")
