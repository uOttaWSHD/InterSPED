import os
from dotenv import load_dotenv

# Load .env from project root at the very beginning
# __file__ is Backend/app/main.py, so we go up two levels to get to project root
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
root_env = os.path.join(os.path.dirname(base_dir), ".env")
load_dotenv(root_env)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.routers import voice, scraper, interview
from app.services.solace_service import start_sam, stop_sam, wait_for_sam_ready


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting Unified Backend...")
    start_sam()

    # We don't block startup indefinitely, but give it a moment
    print("⏳ Waiting for SAM gateway to be ready...")
    # Run wait in background or just wait a bit?
    # Since wait_for_sam_ready is async, we can await it.
    if await wait_for_sam_ready(timeout=10):
        print("✅ SAM gateway is ready!")
    else:
        print("⚠️  SAM gateway may not be fully ready, continuing anyway...")

    yield

    # Shutdown
    print("Shutting down Unified Backend...")
    stop_sam()


app = FastAPI(title="Unified Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(voice.router)
app.include_router(scraper.router, prefix="/api/v1")
app.include_router(interview.router, prefix="/api/interview")


@app.get("/")
async def root():
    return {
        "message": "Unified Backend is running",
        "endpoints": ["/api/v1/scrape", "/api/interview/start", "/ws/voice"],
    }
