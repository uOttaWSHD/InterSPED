import httpx
import asyncio
import json
import time


async def test_sam_gateway():
    url = "http://localhost:8000/api/v1/message:stream"
    payload = {
        "jsonrpc": "2.0",
        "id": int(time.time()),
        "method": "message/stream",
        "params": {
            "message": {
                "messageId": f"test_{int(time.time())}",
                "kind": "message",
                "role": "user",
                "metadata": {"agent_name": "OrchestratorAgent"},
                "parts": [
                    {"kind": "text", "text": "[SYSTEM CONTEXT] Test. [Turn 1] Hi"}
                ],
            }
        },
    }

    print(f"📡 Testing SAM Gateway at {url}...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            print(f"📊 Status: {response.status_code}")
            if response.status_code != 200:
                print(f"❌ Error: {response.text}")
                return

            data = response.json()
            task_id = data.get("result", {}).get("id")
            if not task_id:
                print(f"❌ No task ID returned: {data}")
                return

            print(f"✅ Task ID: {task_id}. Subscribing to SSE...")

            async with client.stream(
                "GET", f"http://localhost:8000/api/v1/sse/subscribe/{task_id}"
            ) as sse:
                async for line in sse.aiter_lines():
                    if line.startswith("data:"):
                        event = json.loads(line[5:])
                        status = event.get("result", {}).get("status", {})
                        state = status.get("state")
                        msg = status.get("message", {})

                        if msg:
                            print(f"🔄 State: {state}, Message: {msg}")

                        if state == "completed":
                            print("✅ Task completed!")
                            return
                        if state == "failed":
                            print(f"❌ Task failed: {status.get('error')}")
                            return
    except Exception as e:
        print(f"💥 Exception: {e}")


if __name__ == "__main__":
    asyncio.run(test_sam_gateway())
