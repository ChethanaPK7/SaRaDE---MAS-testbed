from rest_framework import serializers


class LinkStudentLockerSerializer(serializers.Serializer):
    anumati_username = serializers.CharField()
    # Optional: if provided, SRIP makes a one-time verify call to Anumati
    # and never stores it. If omitted, this is a self-attested link from
    # the redirect-out flow -- see views.LinkStudentLockerView.
    anumati_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    locker_name = serializers.CharField(default="Academic")


class LinkInstitutionLockerSerializer(serializers.Serializer):
    anumati_username = serializers.CharField()
    anumati_password = serializers.CharField(write_only=True)
    locker_name = serializers.CharField(default="Admissions")


class AnumatiStatusSerializer(serializers.Serializer):
    user_linked = serializers.BooleanField()
    user_verified = serializers.BooleanField()
    user_locker_name = serializers.CharField(allow_blank=True)
    user_linked_at = serializers.DateTimeField(allow_null=True)
    institution_linked = serializers.BooleanField(allow_null=True)
    institution_locker_name = serializers.CharField(allow_blank=True, allow_null=True)
    institution_linked_at = serializers.DateTimeField(allow_null=True)
    institution_linked_via_oauth = serializers.BooleanField(allow_null=True)
    portal_url = serializers.CharField()
