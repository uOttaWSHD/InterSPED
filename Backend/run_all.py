import os
import subprocess
import signal
import sys
import time
import threading
from dotenv import load_dotenv


def main():
    # Load env from root
    load_dotenv(".env")

    # Force working model name for Cerebras
    if os.environ.get("LLM_SERVICE_API_KEY", "").startswith("csk-"):
        os.environ["LLM_SERVICE_PLANNING_MODEL_NAME"] = "llama3.3-70b"
        os.environ["LLM_SERVICE_GENERAL_MODEL_NAME"] = "llama3.3-70b"
        os.environ["LLM_SERVICE_ENDPOINT"] = "https://api.cerebras.ai/v1"

    print("🚀 Starting Unified Backend & Solace Agent Mesh...")

    # Start SAM
    sam_dir = "app/services/solace_agent"
    sam_cmd = ["uv", "run", "sam", "run", "configs/"]

    sam_proc = subprocess.Popen(
        sam_cmd,
        cwd=sam_dir,
        stdout=sys.stdout,
        stderr=sys.stderr,
        env=os.environ.copy(),
    )

    # Start FastAPI
    api_cmd = [
        "uv",
        "run",
        "uvicorn",
        "app.main:app",
        "--port",
        "8001",
        "--host",
        "0.0.0.0",
    ]
    api_proc = subprocess.Popen(
        api_cmd, stdout=sys.stdout, stderr=sys.stderr, env=os.environ.copy()
    )

    def signal_handler(sig, frame):
        print("\n🛑 Shutting down...")
        api_proc.terminate()
        sam_proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Keep main thread alive
    while True:
        if sam_proc.poll() is not None:
            print("❌ SAM process died. Restarting...")
            sam_proc = subprocess.Popen(
                sam_cmd,
                cwd=sam_dir,
                stdout=sys.stdout,
                stderr=sys.stderr,
                env=os.environ.copy(),
            )
        if api_proc.poll() is not None:
            print("❌ API process died. Exiting.")
            sam_proc.terminate()
            break
        time.sleep(5)


if __name__ == "__main__":
    main()
