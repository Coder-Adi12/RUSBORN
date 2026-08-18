import asyncio
from livekit.api import LiveKitAPI
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    api = LiveKitAPI(url=os.getenv("LIVEKIT_URL"), api_key=os.getenv("LIVEKIT_API_KEY"), api_secret=os.getenv("LIVEKIT_API_SECRET"))
    try:
        await api.agent_dispatch.list_dispatch()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await api.aclose()

asyncio.run(main())
