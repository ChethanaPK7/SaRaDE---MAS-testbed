from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    posting_title = serializers.CharField(source="application.posting.title", default=None, read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "message", "application", "posting_title", "is_read", "created_at"]
