import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv(".env")


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

    @classmethod
    def from_env(cls) -> "Settings":
        required = {
            "LIVEKIT_URL": os.getenv("LIVEKIT_URL"),
            "LIVEKIT_API_KEY": os.getenv("LIVEKIT_API_KEY"),
            "LIVEKIT_API_SECRET": os.getenv("LIVEKIT_API_SECRET"),
            "BACKEND_URL": os.getenv("BACKEND_URL", "http://127.0.0.1:8000"),
            "SUPABASE_URL": os.getenv("SUPABASE_URL"),
            "SUPABASE_SERVICE_ROLE_KEY": os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        }

        missing = [key for key, value in required.items() if not value]

        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        return cls(
            livekit_url=required["LIVEKIT_URL"],
            livekit_api_key=required["LIVEKIT_API_KEY"],
            livekit_api_secret=required["LIVEKIT_API_SECRET"],
            backend_url=required["BACKEND_URL"].rstrip("/"),
            backend_host=os.getenv("BACKEND_HOST", "127.0.0.1"),
            backend_port=int(os.getenv("BACKEND_PORT", "8000")),
            supabase_url=required["SUPABASE_URL"],
            supabase_service_role_key=required["SUPABASE_SERVICE_ROLE_KEY"],
        )

settings = Settings.from_env()
