import os

# Set safe test-only configuration before application modules are imported.
os.environ.setdefault("LIVEKIT_URL", "wss://test.livekit.local")
os.environ.setdefault("LIVEKIT_API_KEY", "test-livekit-key")
os.environ.setdefault("LIVEKIT_API_SECRET", "test-livekit-secret")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.local")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-supabase-service-role-key")
os.environ.setdefault("BACKEND_URL", "http://testserver")
os.environ.setdefault("INTERNAL_API_SECRET", "test-internal-api-secret")
os.environ.setdefault("DASHBOARD_USERNAME", "operator")
os.environ.setdefault("DASHBOARD_PASSWORD", "test-dashboard-password")
os.environ.setdefault("DASHBOARD_SESSION_SECRET", "test-dashboard-session-secret-that-is-long-enough")
os.environ.setdefault("ENVIRONMENT", "test")
