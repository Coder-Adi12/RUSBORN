import logging
import smtplib
from datetime import UTC, datetime
from email.message import EmailMessage
from typing import Any, Optional

from config import settings
from db.client import get_supabase_client

logger = logging.getLogger(__name__)

def _send_smtp_email(to_email: str, subject: str, content: str) -> bool:
    if not settings.smtp_host or settings.email_provider != "smtp":
        logger.warning(f"SMTP not configured properly or provider is {settings.email_provider}. Skipping email to {to_email}")
        return False

    try:
        msg = EmailMessage()
        msg.set_content(content)
        msg["Subject"] = subject
        msg["From"] = settings.email_from
        msg["To"] = to_email

        if settings.smtp_use_tls:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) if settings.smtp_port in [465] else smtplib.SMTP(settings.smtp_host, settings.smtp_port)

        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)

        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        logger.error(f"SMTP error sending to {to_email}: {e}")
        return False

def _process_email_delivery(
    email_type: str,
    recipient_email: str,
    subject: str,
    content: str,
    customer_id: Optional[str] = None,
    call_id: Optional[str] = None,
    appointment_id: Optional[str] = None,
) -> None:
    try:
        client = get_supabase_client()

        # 1. Check for existing successful delivery
        query = client.table("email_deliveries").select("*").eq("email_type", email_type)
        if appointment_id and email_type == "customer_confirmation":
            query = query.eq("appointment_id", appointment_id)
        elif call_id and email_type == "sales_summary":
            query = query.eq("call_id", call_id)

        existing = query.execute()
        if existing.data:
            # Check if there is any 'sent' record
            if any(r["status"] == "sent" for r in existing.data):
                logger.info(f"Idempotency: {email_type} email already sent.")
                return

            # Use existing record to retry
            delivery_record = existing.data[0]
            delivery_id = delivery_record["id"]
            attempt_count = delivery_record.get("attempt_count", 0) + 1
        else:
            # Create a new pending record
            insert_data = {
                "customer_id": customer_id,
                "call_id": call_id,
                "appointment_id": appointment_id,
                "email_type": email_type,
                "recipient_email": recipient_email,
                "subject": subject,
                "status": "pending",
                "provider": settings.email_provider
            }
            insert_data = {k: v for k, v in insert_data.items() if v is not None}

            resp = client.table("email_deliveries").insert(insert_data).execute()
            if not resp.data:
                logger.error("Failed to insert email delivery record.")
                return
            delivery_id = resp.data[0]["id"]
            attempt_count = 1

        # 2. Attempt delivery
        success = _send_smtp_email(recipient_email, subject, content)

        # 3. Update record
        update_data = {
            "status": "sent" if success else "failed",
            "attempt_count": attempt_count,
            "last_error": None if success else "SMTP error",
        }
        if success:
            update_data["sent_at"] = datetime.now(UTC).isoformat()

        client.table("email_deliveries").update(update_data).eq("id", delivery_id).execute()

    except Exception as e:
        logger.error(f"Error processing email delivery {email_type}: {e}")


def send_customer_confirmation(appointment_id: str, customer: dict[str, Any], appointment: dict[str, Any]) -> None:
    if not customer.get("email"):
        logger.warning(f"No email for customer {customer.get('id')}. Skipping confirmation.")
        return

    subject = "RUSBORN Appointment Confirmation"
    content = f"Hello {customer.get('name', 'Customer')},\n\nYour appointment with Rusborn has been successfully booked.\n\nDate: {appointment.get('appointment_date')}\nTime: {appointment.get('start_time')}\nTimezone: {appointment.get('timezone')}\n"
    if appointment.get('meeting_details'):
        content += f"\nMeeting:\n{appointment.get('meeting_details')}\n"

    content += "\nWe look forward to speaking with you.\n\nRegards,\nRUSBORN"

    _process_email_delivery(
        email_type="customer_confirmation",
        recipient_email=customer["email"],
        subject=subject,
        content=content,
        customer_id=customer.get("id"),
        appointment_id=appointment_id,
        call_id=appointment.get("call_id")
    )


def send_sales_summary(call: dict[str, Any], customer: dict[str, Any], appointment: Optional[dict[str, Any]], summary_text: Optional[str]) -> None:
    if not settings.sales_team_email:
        logger.warning("No SALES_TEAM_EMAIL configured. Skipping sales summary.")
        return

    subject = f"New Appointment — {customer.get('name', 'Unknown')}"

    content = f"Customer:\n{customer.get('name', 'Unknown')}\n"
    if customer.get("company"):
        content += f"\nCompany:\n{customer['company']}\n"

    if appointment:
        content += f"\nAppointment:\n{appointment.get('appointment_date')} — {appointment.get('start_time')} {appointment.get('timezone')}\n"
        if appointment.get("meeting_details"):
            content += f"\nRequirement:\n{appointment['meeting_details']}\n"

    content += f"\nCall Outcome:\n{call.get('outcome', 'completed')}\n"

    if summary_text:
        content += f"\nSummary:\n{summary_text}\n"

    _process_email_delivery(
        email_type="sales_summary",
        recipient_email=settings.sales_team_email,
        subject=subject,
        content=content,
        customer_id=customer.get("id"),
        call_id=call.get("id"),
        appointment_id=appointment.get("id") if appointment else None
    )
