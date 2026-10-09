import datetime

import pytest
from rest_framework.test import APIClient

from incidents.models import Event, Incident

pytestmark = pytest.mark.django_db

EVENTS_URL = "/api/events/"
INCIDENTS_URL = "/api/incidents/"
REPORT_URL = "/api/reports/summary/"


@pytest.fixture
def api_client():
    return APIClient()


def make_event(**kwargs):
    data = {
        "source": "firewall",
        "event_type": "failed_login",
        "severity": "high",
        "description": "",
    }
    data.update(kwargs)
    return Event.objects.create(**data)


def status_url(incident):
    return f"{INCIDENTS_URL}{incident.id}/status/"


# ---------- Events ----------


def test_create_event(api_client):
    payload = {
        "source": "web-server",
        "event_type": "port_scan",
        "severity": "medium",
        "description": "Port scan detected",
    }
    response = api_client.post(EVENTS_URL, payload, format="json")
    assert response.status_code == 201
    assert response.data["event_type"] == "port_scan"
    assert Event.objects.count() == 1


def test_create_event_rejects_invalid_severity(api_client):
    payload = {"source": "vpn", "event_type": "failed_login", "severity": "banana"}
    response = api_client.post(EVENTS_URL, payload, format="json")
    assert response.status_code == 400
    assert "severity" in response.data


def test_create_event_requires_source(api_client):
    response = api_client.post(EVENTS_URL, {"event_type": "port_scan"}, format="json")
    assert response.status_code == 400
    assert "source" in response.data


def test_list_events(api_client):
    make_event()
    make_event(event_type="port_scan")
    response = api_client.get(EVENTS_URL)
    assert response.status_code == 200
    assert len(response.data) == 2


def test_filter_events_by_severity(api_client):
    make_event(severity="high")
    make_event(severity="low")
    response = api_client.get(EVENTS_URL, {"severity": "high"})
    assert len(response.data) == 1
    assert response.data[0]["severity"] == "high"


def test_filter_events_by_event_type(api_client):
    make_event(event_type="failed_login")
    make_event(event_type="port_scan")
    response = api_client.get(EVENTS_URL, {"event_type": "port_scan"})
    assert len(response.data) == 1
    assert response.data[0]["event_type"] == "port_scan"


def test_get_event_detail(api_client):
    event = make_event()
    response = api_client.get(f"{EVENTS_URL}{event.id}/")
    assert response.status_code == 200
    assert response.data["id"] == event.id


def test_get_missing_event_returns_404(api_client):
    response = api_client.get(f"{EVENTS_URL}999/")
    assert response.status_code == 404


def test_delete_event(api_client):
    event = make_event()
    response = api_client.delete(f"{EVENTS_URL}{event.id}/")
    assert response.status_code == 204
    assert Event.objects.count() == 0


# ---------- Incidents ----------


def test_create_incident_defaults_to_open(api_client):
    response = api_client.post(
        INCIDENTS_URL, {"title": "Test", "severity": "low"}, format="json"
    )
    assert response.status_code == 201
    assert response.data["status"] == "open"


def test_create_incident_with_events(api_client):
    first = make_event()
    second = make_event(event_type="port_scan")
    payload = {"title": "Linked", "events": [first.id, second.id]}
    response = api_client.post(INCIDENTS_URL, payload, format="json")
    assert response.status_code == 201
    assert sorted(response.data["events"]) == sorted([first.id, second.id])


def test_create_incident_rejects_non_open_status(api_client):
    payload = {"title": "Test", "status": "resolved"}
    response = api_client.post(INCIDENTS_URL, payload, format="json")
    assert response.status_code == 400
    assert "status" in response.data
    assert Incident.objects.count() == 0


def test_create_incident_rejects_unknown_event(api_client):
    payload = {"title": "Test", "events": [999]}
    response = api_client.post(INCIDENTS_URL, payload, format="json")
    assert response.status_code == 400
    assert "events" in response.data


def test_filter_incidents_by_status(api_client):
    Incident.objects.create(title="First", status="open")
    Incident.objects.create(title="Second", status="investigating")
    response = api_client.get(INCIDENTS_URL, {"status": "investigating"})
    assert len(response.data) == 1
    assert response.data[0]["title"] == "Second"


def test_patch_updates_description_only(api_client):
    incident = Incident.objects.create(title="Test")
    response = api_client.patch(
        f"{INCIDENTS_URL}{incident.id}/",
        {"description": "Blocked IP at firewall"},
        format="json",
    )
    assert response.status_code == 200
    incident.refresh_from_db()
    assert incident.description == "Blocked IP at firewall"
    assert incident.status == "open"


def test_patch_rejects_invalid_status_transition(api_client):
    incident = Incident.objects.create(title="Test")
    response = api_client.patch(
        f"{INCIDENTS_URL}{incident.id}/", {"status": "resolved"}, format="json"
    )
    assert response.status_code == 400
    incident.refresh_from_db()
    assert incident.status == "open"


# ---------- Status workflow ----------


def test_can_transition_to_rules():
    incident = Incident(title="Test", status="open")
    assert incident.can_transition_to("investigating") is True
    assert incident.can_transition_to("resolved") is False


@pytest.mark.parametrize(
    "start,target",
    [
        ("open", "investigating"),
        ("investigating", "resolved"),
        ("investigating", "open"),
    ],
)
def test_allowed_status_transitions(api_client, start, target):
    incident = Incident.objects.create(title="Test", status=start)
    response = api_client.post(status_url(incident), {"status": target}, format="json")
    assert response.status_code == 200
    incident.refresh_from_db()
    assert incident.status == target


@pytest.mark.parametrize(
    "start,target",
    [
        ("open", "resolved"),
        ("resolved", "open"),
        ("resolved", "investigating"),
    ],
)
def test_forbidden_status_transitions(api_client, start, target):
    incident = Incident.objects.create(title="Test", status=start)
    response = api_client.post(status_url(incident), {"status": target}, format="json")
    assert response.status_code == 400
    incident.refresh_from_db()
    assert incident.status == start


def test_status_endpoint_rejects_unknown_status(api_client):
    incident = Incident.objects.create(title="Test")
    response = api_client.post(status_url(incident), {"status": "closed"}, format="json")
    assert response.status_code == 400


def test_status_endpoint_requires_status(api_client):
    incident = Incident.objects.create(title="Test")
    response = api_client.post(status_url(incident), {}, format="json")
    assert response.status_code == 400


def test_status_endpoint_missing_incident_returns_404(api_client):
    response = api_client.post(f"{INCIDENTS_URL}999/status/", {"status": "investigating"}, format="json")
    assert response.status_code == 404


# ---------- Reports ----------


def test_report_with_no_data(api_client):
    response = api_client.get(REPORT_URL)
    assert response.status_code == 200
    assert response.data["total_events"] == 0
    assert response.data["events_by_severity"] == []
    assert response.data["top_event_types"] == []
    assert response.data["total_incidents"] == 0


def test_report_counts_events_by_severity(api_client):
    make_event(severity="high")
    make_event(severity="high")
    make_event(severity="low")
    response = api_client.get(REPORT_URL)
    counts = {row["severity"]: row["count"] for row in response.data["events_by_severity"]}
    assert response.data["total_events"] == 3
    assert counts == {"high": 2, "low": 1}


def test_report_top_event_types_sorted_by_count(api_client):
    for _ in range(3):
        make_event(event_type="failed_login")
    for _ in range(2):
        make_event(event_type="malware_detected")
    make_event(event_type="port_scan")
    response = api_client.get(REPORT_URL)
    top = response.data["top_event_types"]
    assert [row["event_type"] for row in top] == [
        "failed_login",
        "malware_detected",
        "port_scan",
    ]
    assert top[0]["count"] == 3


def test_report_top_event_types_limited_to_five(api_client):
    for index in range(7):
        make_event(event_type=f"type_{index}")
    response = api_client.get(REPORT_URL)
    assert len(response.data["top_event_types"]) == 5


def test_report_date_range_filters_events(api_client):
    make_event()
    old = make_event(event_type="old_event")
    Event.objects.filter(pk=old.pk).update(
        created_at=datetime.datetime(2020, 6, 1, 12, 0, tzinfo=datetime.timezone.utc)
    )

    old_range = api_client.get(
        REPORT_URL, {"date_from": "2020-01-01", "date_to": "2020-12-31"}
    )
    assert old_range.data["total_events"] == 1
    assert old_range.data["top_event_types"][0]["event_type"] == "old_event"

    wide_range = api_client.get(
        REPORT_URL, {"date_from": "2000-01-01", "date_to": "2100-01-01"}
    )
    assert wide_range.data["total_events"] == 2


def test_report_range_without_data_returns_zero(api_client):
    make_event()
    response = api_client.get(
        REPORT_URL, {"date_from": "2010-01-01", "date_to": "2010-12-31"}
    )
    assert response.status_code == 200
    assert response.data["total_events"] == 0


def test_report_counts_incidents_by_status(api_client):
    Incident.objects.create(title="A", status="open")
    Incident.objects.create(title="B", status="open")
    Incident.objects.create(title="C", status="investigating")
    response = api_client.get(REPORT_URL)
    counts = {row["status"]: row["count"] for row in response.data["incidents_by_status"]}
    assert response.data["total_incidents"] == 3
    assert counts == {"open": 2, "investigating": 1}


def test_report_rejects_invalid_date(api_client):
    response = api_client.get(REPORT_URL, {"date_from": "abc"})
    assert response.status_code == 400
    assert "date_from" in response.data


def test_report_rejects_reversed_range(api_client):
    response = api_client.get(
        REPORT_URL, {"date_from": "2026-12-31", "date_to": "2026-01-01"}
    )
    assert response.status_code == 400