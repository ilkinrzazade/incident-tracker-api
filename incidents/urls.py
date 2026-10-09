from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import EventViewSet, IncidentViewSet, ReportSummaryView

router = DefaultRouter()
router.register("events", EventViewSet, basename="event")
router.register("incidents", IncidentViewSet, basename="incident")

urlpatterns = [
    path("reports/summary/", ReportSummaryView.as_view(), name="report-summary"),
    path("", include(router.urls)),
]