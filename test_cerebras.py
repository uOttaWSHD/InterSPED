import httpx
import os
import json
import asyncio
import traceback
from dotenv import load_dotenv


async def run_test():
    # Load .env from root
    load_dotenv()

    raw_keys = os.environ.get("LLM_SERVICE_API_KEY", "")
    if not raw_keys:
        print("❌ Error: LLM_SERVICE_API_KEY not found in .env")
        return

    # Take the first key from the comma-separated list
    key = raw_keys.split(",")[0].strip()
    endpoint = "https://api.cerebras.ai/v1"

    # Common variations of the model name
    models_to_test = ["llama3.3-70b", "llama-3.3-70b", "cerebras/llama-3.3-70b"]

    print(f"🧪 Testing Cerebras API Connectivity")
    print(f"📡 Endpoint: {endpoint}")
    print(f"🔑 Key: {key[:8]}...{key[-4:]}")

    async with httpx.AsyncClient() as client:
        for model in models_to_test:
            print(f"\n📝 Trying model: '{model}'")
            url = f"{endpoint}/chat/completions"
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": "Say 'Cerebras is working!'"}],
                "max_tokens": 20,
            }

            try:
                response = await client.post(
                    url, headers=headers, json=payload, timeout=15.0
                )
                print(f"📊 Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(
                        f"✅ SUCCESS! Response: {data['choices'][0]['message']['content']}"
                    )
                    return
                else:
                    print(f"❌ FAILED: {response.text}")
            except Exception as e:
                print(f"💥 Exception: {str(e)}")
                # traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_test())
