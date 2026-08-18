import asyncio
from src.services.campaign_orchestrator import orchestrate_campaign
from src.db.client import get_supabase_client
import os

async def main():
    client = get_supabase_client()
    response = client.table("campaigns").select("*").eq("status", "RUNNING").execute()
    active_campaigns = response.data or []
    print(f"Active campaigns: {len(active_campaigns)}")
    for campaign in active_campaigns:
        await orchestrate_campaign(campaign)

asyncio.run(main())
