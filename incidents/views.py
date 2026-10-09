from django.db.models import Count
from django.utils.dateparse import parse_date
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

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


class ReportSummaryView(APIView):
    def _get_date(self, request, name):
        value = request.query_params.get(name)
        if not value:
            return None
        try:
            parsed = parse_date(value)
        except ValueError:
            parsed = None
        if parsed is None:
            raise ValidationError({name: "Use YYYY-MM-DD format."})
        return parsed

    def get(self, request):
        date_from = self._get_date(request, "date_from")
        date_to = self._get_date(request, "date_to")

        if date_from and date_to and date_from > date_to:
            raise ValidationError({"date_from": "date_from must not be after date_to."})

        events = Event.objects.all()
        incidents = Incident.objects.all()
        if date_from:
            events = events.filter(created_at__date__gte=date_from)
            incidents = incidents.filter(created_at__date__gte=date_from)
        if date_to:
            events = events.filter(created_at__date__lte=date_to)
            incidents = incidents.filter(created_at__date__lte=date_to)

        by_severity = (
            events.values("severity")
            .annotate(count=Count("id"))
            .order_by("-count", "severity")
        )
        top_event_types = (
            events.values("event_type")
            .annotate(count=Count("id"))
            .order_by("-count", "event_type")[:5]
        )
        incidents_by_status = (
            incidents.values("status")
            .annotate(count=Count("id"))
            .order_by("-count", "status")
        )

        return Response(
            {
                "date_from": date_from,
                "date_to": date_to,
                "total_events": events.count(),
                "events_by_severity": list(by_severity),
                "top_event_types": list(top_event_types),
                "total_incidents": incidents.count(),
                "incidents_by_status": list(incidents_by_status),
            }
        )