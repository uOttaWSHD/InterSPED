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
from app.services.solace_service import (
    start_sam,
    stop_sam,
    wait_for_sam_ready,
    start_sam_with_rotation,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting Unified Backend...")
    # Use the new robust startup that tests keys
    await start_sam_with_rotation()

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


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {
        "message": "Unified Backend is running",
        "endpoints": ["/api/v1/scrape", "/api/interview/start", "/ws/voice"],
    }
