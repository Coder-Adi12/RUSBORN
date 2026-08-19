import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from api.auth import router as auth_router
from api.routers import appointments, campaigns, dashboard, knowledge, webhooks
from config import settings
from db.client import get_supabase_client
from services.campaign_orchestrator import campaign_orchestrator_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: spawn campaign orchestrator loop
    orchestrator_task = asyncio.create_task(campaign_orchestrator_loop())
    yield
    # Shutdown: cancel task
    orchestrator_task.cancel()

app = FastAPI(title="Rusborn Voice Agent API", lifespan=lifespan)

# Session middleware for dashboard cookie auth
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.dashboard_session_secret,
)

base_origins = [
    "https://rusborn.vercel.app",
]
if settings.environment not in ("production", "staging"):
    base_origins.extend([
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=base_origins,
    allow_origin_regex=r"https://rusborn-.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(appointments.router)
app.include_router(webhooks.router)
app.include_router(knowledge.router)
app.include_router(dashboard.router)
app.include_router(campaigns.router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/health/db")
async def db_health_check():
    try:
        client = get_supabase_client()
        # Ping the database by checking auth or a simple table query.
        # Since we might not have tables created yet, we can just do a very basic
        # query that will fail gracefully if table doesn't exist, but prove connection.
        # Calling rpc "version" or just hitting a nonexistent table:
        try:
            client.table("knowledge_base").select("id").limit(1).execute()
        except Exception as e:
            if "relation" in str(e).lower() and "does not exist" in str(e).lower():
                pass  # Connection works, table just isn't there yet
            else:
                # Other exceptions like authentication or network error
                raise
        return {"status": "ok", "db_connected": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {e!s}") from e
