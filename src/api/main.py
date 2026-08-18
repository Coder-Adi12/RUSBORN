from fastapi import FastAPI, HTTPException

from db.client import get_supabase_client

app = FastAPI(title="Rusborn Voice Agent API")

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
                pass # Connection works, table just isn't there yet
            else:
                # Other exceptions like authentication or network error
                raise
        return {"status": "ok", "db_connected": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {e!s}") from e
