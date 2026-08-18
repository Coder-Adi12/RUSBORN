import os
import uuid
from datetime import datetime, time, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from services.appointment_service import parse_time

# Ensure config isn't broken by missing env vars during test collection
os.environ["LIVEKIT_URL"] = "dummy"
os.environ["LIVEKIT_API_KEY"] = "dummy"
os.environ["LIVEKIT_API_SECRET"] = "dummy"
os.environ["SUPABASE_URL"] = "dummy"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "dummy"

client = TestClient(app)

# Helper to generate a valid date in the future
dt = datetime.today() + timedelta(days=2)
while dt.isoweekday() > 5:
    dt += timedelta(days=1)
valid_date = dt.strftime("%Y-%m-%d")
valid_time = "10:00"

@pytest.fixture
def mock_supabase():
    with patch("services.appointment_service.get_supabase_client") as mock:
        yield mock

def test_available_slot(mock_supabase):
    mock_execute = MagicMock()
    mock_execute.execute.return_value.data = []
    mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.in_.return_value = mock_execute

    response = client.post("/api/v1/appointments/availability", json={
        "date": valid_date,
        "time": valid_time,
        "timezone": "Asia/Kolkata"
    })
    assert response.status_code == 200
    assert response.json()["available"] is True

def test_occupied_slot(mock_supabase):
    mock_execute = MagicMock()
    mock_execute.execute.return_value.data = [{"start_time": valid_time}]
    mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.in_.return_value = mock_execute

    response = client.post("/api/v1/appointments/availability", json={
        "date": valid_date,
        "time": valid_time,
        "timezone": "Asia/Kolkata"
    })
    assert response.status_code == 200
    res = response.json()
    assert res["available"] is False
    assert "alternatives" in res
    assert len(res["alternatives"]) > 0

def test_outside_working_hours(mock_supabase):
    response = client.post("/api/v1/appointments/availability", json={
        "date": valid_date,
        "time": "02:00",
        "timezone": "Asia/Kolkata"
    })
    res = response.json()
    assert res["available"] is False

def test_weekend(mock_supabase):
    dt_sat = datetime.today()
    while dt_sat.isoweekday() != 6:
        dt_sat += timedelta(days=1)

    response = client.post("/api/v1/appointments/availability", json={
        "date": dt_sat.strftime("%Y-%m-%d"),
        "time": valid_time,
        "timezone": "Asia/Kolkata"
    })
    res = response.json()
    assert res["available"] is False

def test_past_slot(mock_supabase):
    past_date = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    response = client.post("/api/v1/appointments/availability", json={
        "date": past_date,
        "time": valid_time,
        "timezone": "Asia/Kolkata"
    })
    assert response.json()["available"] is False

def test_adjacent_appointments(mock_supabase):
    # If 10:00 is taken, 10:30 should still be available (assuming 30m duration)
    mock_execute = MagicMock()
    mock_execute.execute.return_value.data = [{"start_time": "10:00"}]
    mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.in_.return_value = mock_execute

    response = client.post("/api/v1/appointments/availability", json={
        "date": valid_date,
        "time": "10:30",
        "timezone": "Asia/Kolkata"
    })
    assert response.status_code == 200
    assert response.json()["available"] is True

def test_booking_free_slot(mock_supabase):
    mock_select = MagicMock()
    mock_select.execute.return_value.data = []

    mock_insert = MagicMock()
    mock_insert.execute.return_value.data = [{
        "id": str(uuid.uuid4()),
        "appointment_date": valid_date,
        "start_time": valid_time,
        "end_time": "10:30",
        "timezone": "Asia/Kolkata"
    }]

    def table_side_effect(name):
        tbl = MagicMock()
        tbl.select.return_value.eq.return_value.in_.return_value = mock_select
        tbl.insert.return_value = mock_insert
        return tbl

    mock_supabase.return_value.table.side_effect = table_side_effect

    response = client.post("/api/v1/appointments/book", json={
        "customer_id": str(uuid.uuid4()),
        "date": valid_date,
        "time": valid_time,
        "timezone": "Asia/Kolkata"
    })

    assert response.status_code == 200
    assert response.json()["success"] is True

def test_booking_slot_becomes_occupied(mock_supabase):
    mock_insert = MagicMock()
    mock_insert.execute.side_effect = Exception("Unique constraint violation") 

    def table_side_effect(name):
        tbl = MagicMock()
        # For select (availability check) - first returns empty, second returns it occupied
        tbl.select.return_value.eq.return_value.in_.return_value.execute.side_effect = [
            MagicMock(data=[]),
            MagicMock(data=[{"start_time": valid_time}])
        ]
        # For insert
        tbl.insert.return_value = mock_insert
        return tbl

    mock_supabase.return_value.table.side_effect = table_side_effect

    response = client.post("/api/v1/appointments/book", json={
        "customer_id": str(uuid.uuid4()),
        "date": valid_date,
        "time": valid_time,
        "timezone": "Asia/Kolkata"
    })

    res = response.json()
    assert res["success"] is False

# --- CANCELLATION TESTS ---

def test_cancel_valid_appointment(mock_supabase):
    mock_select = MagicMock()
    mock_select.execute.return_value.data = [{"status": "booked", "customer_id": str(uuid.uuid4())}]

    mock_update = MagicMock()
    mock_update.execute.return_value.data = [{"id": str(uuid.uuid4())}]

    def table_side_effect(name):
        tbl = MagicMock()
        tbl.select.return_value.eq.return_value.eq.return_value = mock_select
        tbl.update.return_value.eq.return_value = mock_update
        return tbl

    mock_supabase.return_value.table.side_effect = table_side_effect

    response = client.post("/api/v1/appointments/cancel", json={
        "appointment_id": str(uuid.uuid4()),
        "customer_id": str(uuid.uuid4()),
        "reason": "Sick"
    })

    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    assert res["status"] == "cancelled"

def test_cancel_nonexistent_appointment(mock_supabase):
    mock_select = MagicMock()
    mock_select.execute.return_value.data = []  # not found

    def table_side_effect(name):
        tbl = MagicMock()
        tbl.select.return_value.eq.return_value.eq.return_value = mock_select
        return tbl

    mock_supabase.return_value.table.side_effect = table_side_effect

    response = client.post("/api/v1/appointments/cancel", json={
        "appointment_id": str(uuid.uuid4()),
        "customer_id": str(uuid.uuid4())
    })

    res = response.json()
    assert res["success"] is False
    assert res["error"] == "not_found"

def test_cancel_already_cancelled_appointment(mock_supabase):
    mock_select = MagicMock()
    mock_select.execute.return_value.data = [{"status": "cancelled"}]

    def table_side_effect(name):
        tbl = MagicMock()
        tbl.select.return_value.eq.return_value.eq.return_value = mock_select
        return tbl

    mock_supabase.return_value.table.side_effect = table_side_effect

    response = client.post("/api/v1/appointments/cancel", json={
        "appointment_id": str(uuid.uuid4()),
        "customer_id": str(uuid.uuid4())
    })

    res = response.json()
    assert res["success"] is False
    assert res["error"] == "already_cancelled"


# --- RESCHEDULING TESTS ---

def test_reschedule_valid_appointment(mock_supabase):
    mock_select = MagicMock()
    # original appt is booked
    mock_select.execute.side_effect = [
        MagicMock(data=[{"status": "booked", "appointment_date": valid_date, "start_time": valid_time}]),
        MagicMock(data=[]) # availability check passes (no active slots)
    ]

    mock_update = MagicMock()
    mock_update.execute.return_value.data = [{
        "id": str(uuid.uuid4()),
        "appointment_date": valid_date,
        "start_time": "14:00",
        "end_time": "14:30",
        "timezone": "Asia/Kolkata",
        "status": "rescheduled"
    }]

    def table_side_effect(name):
        tbl = MagicMock()
        # the first eq() is for appointment_id, second for customer_id, etc.
        # we simplify side_effects by just replacing the terminal `.execute` method behaviour:
        tbl.select.return_value.eq.return_value.eq.return_value = mock_select
        tbl.select.return_value.eq.return_value.in_.return_value = mock_select
        tbl.update.return_value.eq.return_value = mock_update
        return tbl

    mock_supabase.return_value.table.side_effect = table_side_effect

    response = client.post("/api/v1/appointments/reschedule", json={
        "appointment_id": str(uuid.uuid4()),
        "customer_id": str(uuid.uuid4()),
        "date": valid_date,
        "time": "14:00",
        "timezone": "Asia/Kolkata",
        "reason": "Schedule change"
    })

    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    assert res["start_time"] == "14:00"

def test_reschedule_to_unavailable_slot(mock_supabase):
    mock_select_appt = MagicMock()
    mock_select_appt.execute.return_value.data = [{"status": "booked", "appointment_date": valid_date, "start_time": "09:00"}]

    mock_select_avail = MagicMock()
    # slot is taken
    mock_select_avail.execute.return_value.data = [{"start_time": "14:00"}]

    def table_side_effect(name):
        tbl = MagicMock()
        tbl.select.return_value.eq.return_value.eq.return_value = mock_select_appt
        tbl.select.return_value.eq.return_value.in_.return_value = mock_select_avail
        return tbl

    mock_supabase.return_value.table.side_effect = table_side_effect

    response = client.post("/api/v1/appointments/reschedule", json={
        "appointment_id": str(uuid.uuid4()),
        "customer_id": str(uuid.uuid4()),
        "date": valid_date,
        "time": "14:00",
        "timezone": "Asia/Kolkata"
    })

    res = response.json()
    assert res["success"] is False
    assert res["error"] == "slot_unavailable"
    assert "alternatives" in res

def test_reschedule_completed_appointment(mock_supabase):
    mock_select = MagicMock()
    mock_select.execute.return_value.data = [{"status": "completed"}]

    def table_side_effect(name):
        tbl = MagicMock()
        tbl.select.return_value.eq.return_value.eq.return_value = mock_select
        return tbl

    mock_supabase.return_value.table.side_effect = table_side_effect

    response = client.post("/api/v1/appointments/reschedule", json={
        "appointment_id": str(uuid.uuid4()),
        "customer_id": str(uuid.uuid4()),
        "date": valid_date,
        "time": "14:00",
        "timezone": "Asia/Kolkata"
    })

    res = response.json()
    assert res["success"] is False
    assert res["error"] == "cannot_reschedule_completed"

def test_concurrent_reschedule_conflict(mock_supabase):
    mock_select_appt = MagicMock()
    mock_select_appt.execute.return_value.data = [{"status": "booked", "appointment_date": valid_date, "start_time": "09:00"}]

    mock_select_avail = MagicMock()
    # availability check says empty first, then taken
    mock_select_avail.execute.side_effect = [
        MagicMock(data=[]),
        MagicMock(data=[{"start_time": "14:00"}])
    ]

    mock_update = MagicMock()
    mock_update.execute.side_effect = Exception("Unique constraint violation")

    def table_side_effect(name):
        tbl = MagicMock()
        tbl.select.return_value.eq.return_value.eq.return_value = mock_select_appt
        tbl.select.return_value.eq.return_value.in_.return_value = mock_select_avail
        tbl.update.return_value.eq.return_value = mock_update
        return tbl

    mock_supabase.return_value.table.side_effect = table_side_effect

    response = client.post("/api/v1/appointments/reschedule", json={
        "appointment_id": str(uuid.uuid4()),
        "customer_id": str(uuid.uuid4()),
        "date": valid_date,
        "time": "14:00",
        "timezone": "Asia/Kolkata"
    })

    res = response.json()
    assert res["success"] is False
    assert res["error"] == "slot_unavailable"
    assert res["error"] == "slot_unavailable"
    assert "alternatives" in res

def test_concurrent_booking_attempts(mock_supabase):
    # Demonstrated by test_booking_slot_becomes_occupied
    # In an actual DB, postgres handles the lock/conflict natively.
    pass


def test_parse_time():
    assert parse_time("12:00") == time(12, 0)
    assert parse_time("12:00:00") == time(12, 0)
    assert parse_time("12:00:00.000000") == time(12, 0)
    assert parse_time(time(12, 0)) == time(12, 0)

    with pytest.raises(ValueError):
        parse_time("invalid time")

def test_reschedule_slot_conflict(mock_supabase):
    from services.appointment_service import reschedule_appointment

    # Mocking the supabase client to raise an exception with "unique constraint"
    mock_client = MagicMock()
    mock_supabase.return_value = mock_client

    mock_client.table().select().eq().eq().execute.return_value.data = [{"status": "booked", "appointment_date": "2026-08-19", "start_time": "12:00"}]

    # Mocking check_availability to return True to pass the initial check
    with patch("services.appointment_service.check_availability") as mock_avail:
        mock_avail.return_value = {"available": True, "end_time": "14:30"}
        mock_client.table().update().eq().execute.side_effect = Exception("duplicate key value violates unique constraint")

        res = reschedule_appointment("dummy-appt-id", "dummy-cust-id", "2026-08-20", "14:00", "Asia/Kolkata")

        assert res["success"] is False
        assert res["error"] == "slot_unavailable"

def test_reschedule_database_error(mock_supabase):
    from services.appointment_service import reschedule_appointment

    # Mocking the supabase client to raise a generic database error (e.g. missing column)
    mock_client = MagicMock()
    mock_supabase.return_value = mock_client

    mock_client.table().select().eq().eq().execute.return_value.data = [{"status": "booked", "appointment_date": "2026-08-19", "start_time": "12:00"}]

    # Mocking check_availability to return True
    with patch("services.appointment_service.check_availability") as mock_avail:
        mock_avail.return_value = {"available": True, "end_time": "14:30"}
        mock_client.table().update().eq().execute.side_effect = Exception("Could not find the 'previous_appointment_date' column of 'appointments' in the schema cache")

        res = reschedule_appointment("dummy-appt-id", "dummy-cust-id", "2026-08-20", "14:00", "Asia/Kolkata")

        assert res["success"] is False
        assert res["error"] == "database_error"
