import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load .env first, then .env.local as an override (matching README instructions).
load_dotenv(".env")
load_dotenv(".env.local", override=True)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str
    backend_url: str
    backend_host: str
    backend_port: int
    supabase_url: str
    supabase_service_role_key: str

    appointment_timezone: str
    appointment_duration_minutes: int
    appointment_working_days: str
    appointment_start_time: str
    appointment_end_time: str

    email_provider: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_use_tls: bool
    email_from: str
    sales_team_email: str

    # Authentication
    internal_api_secret: str
    dashboard_username: str
    dashboard_password: str
    dashboard_session_secret: str
    environment: str

    @classmethod
    def from_env(cls) -> "Settings":
        environment = os.getenv("ENVIRONMENT", "development")

        required = {
            "LIVEKIT_URL": os.getenv("LIVEKIT_URL"),
            "LIVEKIT_API_KEY": os.getenv("LIVEKIT_API_KEY"),
            "LIVEKIT_API_SECRET": os.getenv("LIVEKIT_API_SECRET"),
            "SUPABASE_URL": os.getenv("SUPABASE_URL"),
            "SUPABASE_SERVICE_ROLE_KEY": os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        }

        # BACKEND_URL: require in production, fall back in development
        backend_url_raw = os.getenv("BACKEND_URL", "").strip()
        if not backend_url_raw:
            if environment in ("production", "staging"):
                required["BACKEND_URL"] = None  # will trigger missing-var error
            else:
                backend_url_raw = "http://127.0.0.1:8000"
                logger.warning(
                    "BACKEND_URL not set — defaulting to %s (development only)",
                    backend_url_raw,
                )

        missing = [key for key, value in required.items() if not value]

        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        return cls(
            livekit_url=required["LIVEKIT_URL"].strip(),
            livekit_api_key=required["LIVEKIT_API_KEY"].strip(),
            livekit_api_secret=required["LIVEKIT_API_SECRET"].strip(),
            backend_url=backend_url_raw.rstrip("/"),
            backend_host=os.getenv("BACKEND_HOST", "127.0.0.1").strip(),
            backend_port=int(os.getenv("BACKEND_PORT", "8000")),
            supabase_url=required["SUPABASE_URL"].strip(),
            supabase_service_role_key=required["SUPABASE_SERVICE_ROLE_KEY"].strip(),
            appointment_timezone=os.getenv("APPOINTMENT_TIMEZONE", "Asia/Kolkata"),
            appointment_duration_minutes=int(
                os.getenv("APPOINTMENT_DURATION_MINUTES", "30")
            ),
            appointment_working_days=os.getenv(
                "APPOINTMENT_WORKING_DAYS", "1,2,3,4,5"
            ),
            appointment_start_time=os.getenv("APPOINTMENT_START_TIME", "09:00"),
            appointment_end_time=os.getenv("APPOINTMENT_END_TIME", "18:00"),
            email_provider=os.getenv("EMAIL_PROVIDER", "smtp"),
            smtp_host=os.getenv("SMTP_HOST", ""),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            smtp_use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
            email_from=os.getenv("EMAIL_FROM", ""),
            sales_team_email=os.getenv("SALES_TEAM_EMAIL", ""),
            # Auth
            internal_api_secret=os.getenv("INTERNAL_API_SECRET", ""),
            dashboard_username=os.getenv("DASHBOARD_USERNAME", ""),
            dashboard_password=os.getenv("DASHBOARD_PASSWORD", ""),
            dashboard_session_secret=os.getenv(
                "DASHBOARD_SESSION_SECRET",
                "change-me-in-production-use-a-long-random-string",
            ),
            environment=environment,
        )


settings = Settings.from_env()
