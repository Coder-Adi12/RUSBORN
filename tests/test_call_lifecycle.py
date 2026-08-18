import json
from unittest.mock import MagicMock, patch

import pytest

from agent_core.context import build_call_context
from services.call_service import create_or_reuse_call


@pytest.fixture
def mock_supabase():
    with patch("services.call_service.get_supabase_client") as mock:
        yield mock

def test_new_room_creates_call(mock_supabase):
    mock_client = MagicMock()
    mock_supabase.return_value = mock_client

    # get_call_by_room_id returns None initially
    mock_client.table().select().eq().execute.return_value.data = []

    # insert returns a new call row
    mock_client.table().insert().execute.return_value.data = [
        {"id": "new-call-uuid", "livekit_room_id": "test-room"}
    ]

    call = create_or_reuse_call(
        customer_id="cust-123",
        direction="inbound",
        livekit_room_id="test-room",
        started_at="2026-08-18T12:00:00Z"
    )

    assert call["id"] == "new-call-uuid"
    assert mock_client.table().insert.called

    # Check that insert arguments were correct
    insert_args = mock_client.table().insert.call_args[0][0]
    assert insert_args["customer_id"] == "cust-123"
    assert insert_args["livekit_room_id"] == "test-room"
    assert insert_args["status"] == "in_progress"

def test_reuse_existing_call(mock_supabase):
    mock_client = MagicMock()
    mock_supabase.return_value = mock_client

    # get_call_by_room_id returns an existing call
    mock_client.table().select().eq().execute.return_value.data = [
        {"id": "existing-call-uuid", "livekit_room_id": "test-room"}
    ]

    call = create_or_reuse_call(
        customer_id="cust-123",
        direction="inbound",
        livekit_room_id="test-room",
        started_at="2026-08-18T12:00:00Z"
    )

    assert call["id"] == "existing-call-uuid"
    # insert should not have been called
    assert not mock_client.table().insert.called

def test_build_call_context_does_not_use_call_id_from_metadata():
    metadata = json.dumps({
        "customer_id": "cust-123",
        "call_id": "malicious-or-old-call-id",
        "direction": "outbound"
    })

    ctx = build_call_context(metadata)

    assert ctx.customer_id == "cust-123"
    assert ctx.direction == "outbound"
    # Call ID must be None because it should only come from DB row creation now
    assert ctx.call_id is None

def test_missing_customer_context_does_not_fabricate_id(mock_supabase):
    mock_client = MagicMock()
    mock_supabase.return_value = mock_client

    mock_client.table().select().eq().execute.return_value.data = []
    mock_client.table().insert().execute.return_value.data = [
        {"id": "new-call-uuid", "livekit_room_id": "test-room"}
    ]

    import os
    with patch.dict(os.environ, {}, clear=True):
        ctx = build_call_context(None) # Missing metadata
        assert ctx.customer_id is None
        assert not ctx.has_customer

    _ = create_or_reuse_call(
        customer_id=ctx.customer_id,
        direction=ctx.direction,
        livekit_room_id="test-room",
        started_at="2026-08-18T12:00:00Z"
    )

    insert_args = mock_client.table().insert.call_args[0][0]
    assert "customer_id" not in insert_args  # Did not inject a fabricated ID
