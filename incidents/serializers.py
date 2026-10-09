from rest_framework import serializers

from .models import Event, Incident


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["id", "source", "event_type", "severity", "description", "created_at"]
        read_only_fields = ["id", "created_at"]


class IncidentSerializer(serializers.ModelSerializer):
    events = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Event.objects.all(), required=False
    )

    class Meta:
        model = Incident
        fields = [
            "id", "title", "description", "status", "severity",
            "events", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]