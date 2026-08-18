import asyncio
from src.services.dispatch_service import dispatch_campaign_call
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    campaign = {"id": "test", "objective": "test", "voice_agent_instructions": "test"}
    contact = {"id": "test", "customer_context": "test"}
    customer = {"id": "test", "phone": "+1234567890", "name": "test"}
    attempt = {"id": "test"}
    success = await dispatch_campaign_call(campaign, contact, customer, attempt)
    print(f"Success: {success}")

asyncio.run(main())
