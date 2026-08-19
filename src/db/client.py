from config import settings
from supabase import Client, create_client

_client: Client | None = None


def get_supabase_client() -> Client:
    """Returns a cached Supabase client using the service role key."""
    global _client
    if _client is None:
        _client = create_client(
            settings.supabase_url, settings.supabase_service_role_key
        )
    return _client
