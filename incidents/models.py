from django.db import models


class Severity(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class Event(models.Model):
    source = models.CharField(max_length=100)
    event_type = models.CharField(max_length=100)
    severity = models.CharField(
        max_length=10, choices=Severity.choices, default=Severity.LOW
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} ({self.severity}) from {self.source}"


class Incident(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        INVESTIGATING = "investigating", "Investigating"
        RESOLVED = "resolved", "Resolved"

    ALLOWED_TRANSITIONS = {
        Status.OPEN: [Status.INVESTIGATING],
        Status.INVESTIGATING: [Status.OPEN, Status.RESOLVED],
        Status.RESOLVED: [],
    }

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    severity = models.CharField(
        max_length=10, choices=Severity.choices, default=Severity.MEDIUM
    )
    events = models.ManyToManyField(Event, related_name="incidents", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def can_transition_to(self, new_status):
        return new_status in self.ALLOWED_TRANSITIONS[self.status]

    def __str__(self):
        return f"{self.title} [{self.status}]"