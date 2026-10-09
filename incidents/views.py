from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

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

    @action(detail=True, methods=["post"], url_path="status")
    def change_status(self, request, pk=None):
        incident = self.get_object()
        serializer = self.get_serializer(
            incident, data={"status": request.data.get("status")}, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)