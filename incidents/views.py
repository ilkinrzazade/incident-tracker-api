from rest_framework import viewsets

from .models import Event, Incident
from .serializers import EventSerializer, IncidentSerializer


class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer

    def get_queryset(self):
        queryset = Event.objects.all()
        severity = self.request.query_params.get("severity")
        event_type = self.request.query_params.get("event_type")
        if severity:
            queryset = queryset.filter(severity=severity)
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        return queryset


class IncidentViewSet(viewsets.ModelViewSet):
    serializer_class = IncidentSerializer

    def get_queryset(self):
        queryset = Incident.objects.prefetch_related("events")
        status = self.request.query_params.get("status")
        severity = self.request.query_params.get("severity")
        if status:
            queryset = queryset.filter(status=status)
        if severity:
            queryset = queryset.filter(severity=severity)
        return queryset