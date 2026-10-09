from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import EventViewSet, IncidentViewSet

router = DefaultRouter()
router.register("events", EventViewSet, basename="event")
router.register("incidents", IncidentViewSet, basename="incident")

urlpatterns = [
    path("", include(router.urls)),
]