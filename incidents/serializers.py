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

    def validate_status(self, value):
        if self.instance is None:
            if value != Incident.Status.OPEN:
                raise serializers.ValidationError("New incidents must start as 'open'.")
        elif value != self.instance.status:
            if not self.instance.can_transition_to(value):
                raise serializers.ValidationError(
                    f"Cannot change status from '{self.instance.status}' to '{value}'."
                )
        return value