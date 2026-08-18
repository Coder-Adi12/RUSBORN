from datetime import datetime
import os
import uuid
import sys
sys.path.append("src")
from config import settings
from db.client import get_supabase_client

client = get_supabase_client()
call_data = {
    "direction": "inbound",
    "livekit_room_id": "test-room",
    "status": "in_progress",
    "started_at": datetime.utcnow().isoformat()
}
response = client.table("calls").insert(call_data).execute()
print("Inserted call:", response.data)
