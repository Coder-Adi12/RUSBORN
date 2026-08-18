from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

@pytest.fixture
def mock_supabase():
    with patch("services.call_service.get_supabase_client") as mock:
        yield mock

def test_valid_summary_webhook(mock_supabase):
    mock_client = MagicMock()
    mock_supabase.return_value = mock_client

    # Mock get_call_by_room_id
    mock_client.table().select().eq().execute.return_value.data = [{"id": "test-call-id", "livekit_room_id": "test-room"}]
    # Mock update_call
    mock_client.table().update().eq().execute.return_value.data = [{"id": "test-call-id"}]

    payload = {
        "job_id": "job_123",
        "room_id": "test-room",
        "room": "room-name",
        "started_at": "2026-08-18T12:00:00Z",
        "ended_at": "2026-08-18T12:30:00Z",
        "summary": "Customer: John\nCall outcome: Appointment booked\nRequirement: Software"
    }

    response = client.post("/api/v1/webhooks/livekit/call-summary", json=payload)

    assert response.status_code == 200
    assert response.json() == {"success": True}

    # Verify update was called correctly
    update_args = mock_client.table().update.call_args[0][0]
    assert update_args["status"] == "completed"
    assert update_args["duration_seconds"] == 1800  # 30 mins = 1800 seconds
    assert update_args["outcome"] == "appointment_booked"

def test_missing_optional_fields(mock_supabase):
    mock_client = MagicMock()
    mock_supabase.return_value = mock_client

    mock_client.table().select().eq().execute.return_value.data = [{"id": "test-call-id", "livekit_room_id": "test-room"}]
    mock_client.table().update().eq().execute.return_value.data = [{"id": "test-call-id"}]

    # Omit started_at and summary
    payload = {
        "job_id": "job_123",
        "room_id": "test-room",
        "room": "room-name",
        "ended_at": "2026-08-18T12:30:00Z"
    }

    response = client.post("/api/v1/webhooks/livekit/call-summary", json=payload)

    assert response.status_code == 200
    assert response.json() == {"success": True}

    update_args = mock_client.table().update.call_args[0][0]
    assert update_args["status"] == "completed"
    assert "duration_seconds" not in update_args
    assert update_args["summary"] is None

def test_duplicate_webhook_delivery(mock_supabase):
    # Testing idempotency - should just return 200 and perform the update again
    mock_client = MagicMock()
    mock_supabase.return_value = mock_client

    mock_client.table().select().eq().execute.return_value.data = [{"id": "test-call-id", "livekit_room_id": "test-room"}]
    mock_client.table().update().eq().execute.return_value.data = [{"id": "test-call-id"}]

    payload = {
        "job_id": "job_123",
        "room_id": "test-room",
        "room": "room-name",
        "ended_at": "2026-08-18T12:30:00Z"
    }

    # First delivery
    response1 = client.post("/api/v1/webhooks/livekit/call-summary", json=payload)
    assert response1.status_code == 200

    # Second delivery
    response2 = client.post("/api/v1/webhooks/livekit/call-summary", json=payload)
    assert response2.status_code == 200

    # Update should be called twice
    assert mock_client.table().update().eq().execute.call_count == 2

def test_unknown_call(mock_supabase):
    mock_client = MagicMock()
    mock_supabase.return_value = mock_client

    # Return empty list to simulate not found
    mock_client.table().select().eq().execute.return_value.data = []

    payload = {
        "job_id": "job_123",
        "room_id": "test-room",
        "room": "room-name",
        "ended_at": "2026-08-18T12:30:00Z"
    }

    response = client.post("/api/v1/webhooks/livekit/call-summary", json=payload)

    assert response.status_code == 404
    assert response.json() == {"success": False, "error": "call_not_found"}

def test_malformed_payload(mock_supabase):
    # Missing required field `ended_at` and `room_id`
    payload = {
        "job_id": "job_123"
    }

    response = client.post("/api/v1/webhooks/livekit/call-summary", json=payload)

    assert response.status_code == 422 # Pydantic validation error

def test_database_failure(mock_supabase):
    mock_client = MagicMock()
    mock_supabase.return_value = mock_client

    mock_client.table().select().eq().execute.return_value.data = [{"id": "test-call-id"}]

    # Simulate DB error during update
    mock_client.table().update().eq().execute.side_effect = Exception("DB Connection Lost")

    payload = {
        "job_id": "job_123",
        "room_id": "test-room",
        "room": "room-name",
        "ended_at": "2026-08-18T12:30:00Z"
    }

    response = client.post("/api/v1/webhooks/livekit/call-summary", json=payload)

    assert response.status_code == 500
    assert response.json() == {"success": False, "error": "database_error"}
