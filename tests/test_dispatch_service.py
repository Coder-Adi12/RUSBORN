from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.dispatch_service import dispatch_campaign_call


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("LIVEKIT_SIP_TRUNK_ID", "ST_123")
    monkeypatch.setenv("LIVEKIT_AGENT_NAME", "agent-123")
    monkeypatch.setenv("LIVEKIT_URL", "wss://test.livekit.cloud")
    monkeypatch.setenv("LIVEKIT_API_KEY", "key123")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "secret123")


@pytest.mark.asyncio
async def test_dispatch_campaign_call_success(mock_env):
    campaign = {"id": "camp123", "objective": "test"}
    contact = {"id": "contact123", "customer_context": "test context", "status": "CALLING"}
    customer = {"id": "cust123", "phone": "+1234567890", "name": "John Doe", "do_not_call": False}
    attempt = {"id": "attempt123", "attempt_number": 1}

    with patch("services.dispatch_service.LiveKitAPI") as MockAPI:
        mock_api_instance = AsyncMock()
        MockAPI.return_value = mock_api_instance

        result = await dispatch_campaign_call(campaign, contact, customer, attempt)

        assert result is True

        # Verify create_dispatch was called
        mock_api_instance.agent_dispatch.create_dispatch.assert_called_once()
        dispatch_args = mock_api_instance.agent_dispatch.create_dispatch.call_args[0][0]
        assert dispatch_args.agent_name == "agent-123"
        assert dispatch_args.room.startswith("campaign-")

        # Verify create_sip_participant was called
        mock_api_instance.sip.create_sip_participant.assert_called_once()
        sip_args = mock_api_instance.sip.create_sip_participant.call_args[0][0]
        assert sip_args.sip_trunk_id == "ST_123"
        assert sip_args.sip_call_to == "+1234567890"
        assert sip_args.wait_until_answered is True

        mock_api_instance.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_dispatch_campaign_call_dnc(mock_env):
    campaign = {"id": "camp123"}
    contact = {"id": "contact123", "status": "CALLING"}
    customer = {"id": "cust123", "phone": "+1234567890", "do_not_call": True}
    attempt = {"id": "attempt123", "attempt_number": 1}

    with patch("services.dispatch_service.get_supabase_client") as mock_supabase:
        mock_client = MagicMock()
        mock_supabase.return_value = mock_client

        result = await dispatch_campaign_call(campaign, contact, customer, attempt)

        assert result is False
        mock_client.table.return_value.update.return_value.eq.return_value.execute.assert_called_once()
        update_call = mock_client.table.return_value.update.call_args[0][0]
        assert update_call == {"status": "DO_NOT_CALL"}


@pytest.mark.asyncio
async def test_dispatch_campaign_call_missing_env():
    # without mock_env, env vars are missing
    campaign = {"id": "camp123"}
    contact = {"id": "contact123", "status": "CALLING"}
    customer = {"id": "cust123", "phone": "+1234567890", "do_not_call": False}
    attempt = {"id": "attempt123", "attempt_number": 1}

    result = await dispatch_campaign_call(campaign, contact, customer, attempt)
    assert result is False

@pytest.mark.asyncio
async def test_dispatch_campaign_call_agent_dispatch_fails(mock_env):
    campaign = {"id": "camp123"}
    contact = {"id": "contact123", "status": "CALLING"}
    customer = {"id": "cust123", "phone": "+1234567890", "do_not_call": False}
    attempt = {"id": "attempt123", "attempt_number": 1}

    with patch("services.dispatch_service.LiveKitAPI") as MockAPI:
        mock_api_instance = AsyncMock()
        mock_api_instance.agent_dispatch.create_dispatch.side_effect = Exception("Dispatch failed")
        MockAPI.return_value = mock_api_instance

        result = await dispatch_campaign_call(campaign, contact, customer, attempt)

        assert result is False
        mock_api_instance.agent_dispatch.create_dispatch.assert_called_once()
        # SIP should NOT be created if dispatch fails
        mock_api_instance.sip.create_sip_participant.assert_not_called()

@pytest.mark.asyncio
async def test_dispatch_campaign_call_sip_fails(mock_env):
    campaign = {"id": "camp123"}
    contact = {"id": "contact123", "status": "CALLING"}
    customer = {"id": "cust123", "phone": "+1234567890", "do_not_call": False}
    attempt = {"id": "attempt123", "attempt_number": 1}

    with patch("services.dispatch_service.LiveKitAPI") as MockAPI:
        mock_api_instance = AsyncMock()
        # Agent dispatch succeeds
        mock_api_instance.agent_dispatch.create_dispatch.return_value = MagicMock(id="disp123")
        # SIP fails
        mock_api_instance.sip.create_sip_participant.side_effect = Exception("SIP failed")
        MockAPI.return_value = mock_api_instance

        result = await dispatch_campaign_call(campaign, contact, customer, attempt)

        assert result is False
        mock_api_instance.agent_dispatch.create_dispatch.assert_called_once()
        mock_api_instance.sip.create_sip_participant.assert_called_once()
