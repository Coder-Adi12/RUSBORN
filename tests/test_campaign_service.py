import os
from unittest.mock import MagicMock, patch

from services.campaign_service import validate_campaign


@patch("services.campaign_service.get_supabase_client")
@patch.dict(os.environ, {"LIVEKIT_SIP_TRUNK_ID": "ST_XYZ123"})
def test_campaign_validation_success(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Mock campaign
    mock_client.table().select().eq().execute.return_value.data = [{
        "id": "camp123",
        "status": "DRAFT",
        "name": "Test Campaign",
        "objective": "Test",
        "timezone": "UTC"
    }]

    # Mock contacts (2 valid, 1 DNC, 1 no phone)
    mock_client.table().select().eq().execute.side_effect = [
        # First call is for campaign, second is for contacts in validate_campaign
        MagicMock(data=[{
            "id": "camp123",
            "status": "DRAFT",
            "name": "Test Campaign",
            "objective": "Test",
            "timezone": "UTC"
        }]),
        MagicMock(data=[
            {"customer_id": "c1", "customers": {"do_not_call": False, "phone": "+123"}},
            {"customer_id": "c2", "customers": {"do_not_call": False, "phone": "+456"}},
            {"customer_id": "c3", "customers": {"do_not_call": True, "phone": "+789"}},
            {"customer_id": "c4", "customers": {"do_not_call": False, "phone": None}}
        ])
    ]

    res = validate_campaign("camp123")

    assert res["valid"] is True
    assert res["valid_contacts_count"] == 2

    # Check that the DB update was called to mark c3 as DNC and c4 as FAILED
    # the second update call would be for FAILED
    update_calls = mock_client.table().update.call_args_list
    assert len(update_calls) >= 2

@patch("services.campaign_service.get_supabase_client")
@patch.dict(os.environ, {}, clear=True)
def test_campaign_validation_fails_no_sip_trunk(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Mock campaign
    mock_client.table().select().eq().execute.side_effect = [
        MagicMock(data=[{
            "id": "camp123",
            "status": "DRAFT",
            "name": "Test Campaign",
            "objective": "Test",
            "timezone": "UTC"
        }]),
        MagicMock(data=[])
    ]

    res = validate_campaign("camp123")
    assert res["valid"] is False
    assert "LIVEKIT_SIP_TRUNK_ID" in " ".join(res["errors"])

@patch("services.campaign_service.get_supabase_client")
@patch.dict(os.environ, {"LIVEKIT_SIP_TRUNK_ID": "ST_XYZ123"})
def test_campaign_validation_one_contact_success(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Mock campaign
    mock_client.table().select().eq().execute.side_effect = [
        MagicMock(data=[{
            "id": "camp123",
            "status": "DRAFT",
            "name": "Test Campaign",
            "objective": "Test",
            "timezone": "UTC"
        }]),
        MagicMock(data=[
            {"customer_id": "c1", "customers": {"do_not_call": False, "phone": "+917397981185"}}
        ])
    ]

    res = validate_campaign("camp123")

    assert res["valid"] is True
    assert res["valid_contacts_count"] == 1
