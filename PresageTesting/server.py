"""
Vitals Server - FastAPI server for video upload and vitals extraction

Workflow:
1. Python code stores the video
2. Python code writes the video path to data/input.json
3. Python builds and executes C++ file through Docker
4. C++ Code reads input.json, processes video, writes output.json
5. Python reads output.json and returns vitals
"""

import os
import json
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Vitals Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RECORDINGS_DIR = BASE_DIR / "recordings"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
RECORDINGS_DIR.mkdir(exist_ok=True)

# Docker image name
DOCKER_IMAGE = "vitals-processor"


class VitalsResult(BaseModel):
    pulse: list
    breathing: list
    timestamp: list
    video_path: str
    processed: bool
    error: Optional[str] = None


def check_docker_image() -> bool:
    """Check if Docker image exists"""
    result = subprocess.run(
        ["docker", "images", "-q", DOCKER_IMAGE],
        capture_output=True,
        text=True
    )
    return bool(result.stdout.strip())


def build_docker_image() -> bool:
    """Build the Docker image if not exists"""
    if check_docker_image():
        print(f"Docker image '{DOCKER_IMAGE}' already exists")
        return True
    
    print(f"Building Docker image '{DOCKER_IMAGE}'...")
    result = subprocess.run(
        ["docker", "build", "-f", "Dockerfile.vitals", "-t", DOCKER_IMAGE, "."],
        cwd=BASE_DIR,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Docker build failed: {result.stderr}")
        return False
    
    print("Docker image built successfully")
    return True


def run_vitals_processor(video_path: str, headless: bool = True) -> dict:
    """
    Run the C++ vitals processor via Docker
    
    1. Write input.json with video path
    2. Execute Docker container
    3. Read output.json with results
    """
    api_key = os.getenv("SMARTSPECTRA_API_KEY", "")
    
    # Step 1: Write input.json
    input_config = {
        "video_path": f"/app/data/{Path(video_path).name}",
        "api_key": api_key,
        "headless": headless
    }
    
    input_file = DATA_DIR / "input.json"
    with open(input_file, "w") as f:
        json.dump(input_config, f, indent=2)
    
    print(f"Written input.json: {input_config}")
    
    # Copy video to data directory for Docker access
    video_in_data = DATA_DIR / Path(video_path).name
    if Path(video_path) != video_in_data:
        shutil.copy(video_path, video_in_data)
    
    # Step 2: Run Docker container
    # Mount data directory so container can read input.json and write output.json
    docker_cmd = [
        "docker", "run", "--rm",
        "-v", f"{DATA_DIR}:/app/data",
        "-e", f"SMARTSPECTRA_API_KEY={api_key}",
        DOCKER_IMAGE
    ]
    
    print(f"Running: {' '.join(docker_cmd)}")
    
    result = subprocess.run(
        docker_cmd,
        capture_output=True,
        text=True,
        timeout=300  # 5 minute timeout
    )
    
    print(f"Docker stdout: {result.stdout}")
    if result.stderr:
        print(f"Docker stderr: {result.stderr}")
    
    # Step 3: Read output.json
    output_file = DATA_DIR / "output.json"
    
    if result.returncode != 0:
        return {
            "pulse": [],
            "breathing": [],
            "timestamp": [],
            "error": f"Processing failed: {result.stderr}"
        }
    
    if not output_file.exists():
        return {
            "pulse": [],
            "breathing": [],
            "timestamp": [],
            "error": "No output file generated"
        }
    
    with open(output_file, "r") as f:
        output_data = json.load(f)
    
    return output_data


@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "ok",
        "service": "Vitals Server",
        "docker_ready": check_docker_image()
    }


@app.post("/api/build")
async def build_image():
    """Build the Docker image"""
    success = build_docker_image()
    if success:
        return {"status": "success", "message": "Docker image built"}
    else:
        raise HTTPException(status_code=500, detail="Failed to build Docker image")


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """
    Upload a video file for storage
    Returns the path where it was saved
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"interview_{timestamp}.mp4"
    filepath = RECORDINGS_DIR / filename
    
    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)
    
    print(f"Saved video: {filepath} ({len(content)} bytes)")
    
    return {
        "status": "success",
        "filename": filename,
        "path": str(filepath),
        "size": len(content)
    }


@app.post("/api/process/{filename}")
async def process_video(filename: str, headless: bool = True):
    """
    Process a previously uploaded video to extract vitals
    """
    video_path = RECORDINGS_DIR / filename
    
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Video not found: {filename}")
    
    if not check_docker_image():
        raise HTTPException(
            status_code=503, 
            detail="Docker image not built. Call POST /api/build first"
        )
    
    try:
        result = run_vitals_processor(str(video_path), headless=headless)
        
        return VitalsResult(
            pulse=result.get("pulse", []),
            breathing=result.get("breathing", []),
            timestamp=result.get("timestamp", []),
            video_path=str(video_path),
            processed=True,
            error=result.get("error")
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Processing timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload-and-process")
async def upload_and_process(file: UploadFile = File(...), headless: bool = True):
    """
    Upload a video and immediately process it for vitals
    Combined endpoint for convenience
    """
    # Upload
    upload_result = await upload_video(file)
    
    # Process
    process_result = await process_video(upload_result["filename"], headless=headless)
    
    return process_result


@app.get("/api/recordings")
async def list_recordings():
    """List all recorded videos"""
    recordings = []
    for f in RECORDINGS_DIR.glob("*.mp4"):
        recordings.append({
            "filename": f.name,
            "size": f.stat().st_size,
            "created": datetime.fromtimestamp(f.stat().st_ctime).isoformat()
        })
    return {"recordings": recordings}


if __name__ == "__main__":
    import uvicorn
    
    # Try to build Docker image on startup
    print("Checking Docker image...")
    build_docker_image()
    
    print("Starting Vitals Server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
