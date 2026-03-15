import os
import django
import asyncio
import json

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from chatbot.services import get_agent_response

async def test_chat():
    print("Testing get_agent_response...")
    try:
        response = await get_agent_response("hi", [])
        print(f"Response: {response}")
    except Exception as e:
        print(f"Caught exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_chat())
