from unittest.mock import MagicMock, patch

import pytest

from services.email_service import (
    _process_email_delivery,
    _send_smtp_email,
    send_customer_confirmation,
    send_sales_summary,
)


@pytest.fixture(autouse=True)
def mock_smtp_settings():
    with patch("services.email_service.settings") as mock_settings:
        mock_settings.email_provider = "smtp"
        mock_settings.smtp_host = "localhost"
        mock_settings.email_from = "test@test.com"
        mock_settings.sales_team_email = "sales@test.com"
        mock_settings.smtp_use_tls = False
        yield mock_settings

def test_send_smtp_email_success():
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        success = _send_smtp_email("user@example.com", "Test Subject", "Test Body")
        assert success is True
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()

def test_send_smtp_email_failure():
    with patch("smtplib.SMTP") as mock_smtp:
        mock_smtp.side_effect = Exception("SMTP error")
        success = _send_smtp_email("user@example.com", "Test Subject", "Test Body")
        assert success is False

def test_process_email_delivery_idempotent():
    with patch("services.email_service.get_supabase_client") as mock_get_client, \
         patch("services.email_service._send_smtp_email") as mock_send_email:

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Simulate record already exists with status sent
        mock_client.table().select().eq().eq().execute.return_value.data = [{"id": "123", "status": "sent"}]

        _process_email_delivery(
            "customer_confirmation", "user@example.com", "Subject", "Body", 
            appointment_id="appt_123"
        )

        mock_send_email.assert_not_called()

def test_process_email_delivery_new_record():
    with patch("services.email_service.get_supabase_client") as mock_get_client, \
         patch("services.email_service._send_smtp_email") as mock_send_email:

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Simulate record doesn't exist
        mock_client.table().select().eq().eq().execute.return_value.data = []

        # Simulate successful insert
        mock_client.table().insert().execute.return_value.data = [{"id": "new_123"}]
        mock_send_email.return_value = True

        _process_email_delivery(
            "customer_confirmation", "user@example.com", "Subject", "Body", 
            appointment_id="appt_123"
        )

        mock_send_email.assert_called_once()
        mock_client.table().update.assert_called()

def test_send_customer_confirmation():
    customer = {"id": "c1", "email": "customer@example.com", "name": "Test Customer"}
    appointment = {"id": "a1", "appointment_date": "2026-08-19", "start_time": "14:00", "timezone": "IST"}

    with patch("services.email_service._process_email_delivery") as mock_process:
        send_customer_confirmation("a1", customer, appointment)
        mock_process.assert_called_once()
        kwargs = mock_process.call_args[1]
        assert kwargs["email_type"] == "customer_confirmation"
        assert kwargs["recipient_email"] == "customer@example.com"
        assert kwargs["appointment_id"] == "a1"

def test_send_sales_summary():
    customer = {"id": "c1", "name": "Test Customer"}
    call = {"id": "call1", "outcome": "completed"}

    with patch("services.email_service._process_email_delivery") as mock_process:
        send_sales_summary(call, customer, None, "Test summary")
        mock_process.assert_called_once()
        kwargs = mock_process.call_args[1]
        assert kwargs["email_type"] == "sales_summary"
        assert kwargs["recipient_email"] == "sales@test.com"
        assert kwargs["call_id"] == "call1"
