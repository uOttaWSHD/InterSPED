# PresageTesting - Vitals Extraction Service

Extracts heart rate (pulse) and breathing rate from video recordings using Presage SmartSpectra SDK.

## How it works

1. **Python server** receives video upload
2. **Python** writes video path to `data/input.json`
3. **Python** executes C++ processor via Docker
4. **C++ code** executes:
   - Reads video path from `data/input.json`
   - Calls SmartSpectra API on the video
   - Prints vitals (pulse/breathing BPM) to terminal
   - Writes results to `data/output.json`
5. **Python** reads `data/output.json` and returns vitals

## Output Format

```json
{
  "breathing": [12.5, 13.0, null, 12.8],
  "pulse": [72.0, 73.5, null, 71.0],
  "timestamp": [1000, 2000, 3000, 4000]
}
```

- Arrays are same length as timestamps
- `null` values indicate no reading at that timestamp
- Breathing in breaths/minute, pulse in beats/minute

## Setup

### 1. Set API Key

Create `.env` file:
```
SMARTSPECTRA_API_KEY=your_api_key_here
```

Get API key from: https://physiology.presagetech.com

### 2. Build Docker Image

```bash
docker build -f Dockerfile.vitals -t vitals-processor .
```

Or via API:
```bash
curl -X POST http://localhost:8001/api/build
```

### 3. Run Server

```bash
# Install dependencies
pip install fastapi uvicorn python-dotenv python-multipart

# Run server
python server.py
```

Server runs on http://localhost:8001

## API Endpoints

### Health Check
```
GET /
```

### Build Docker Image
```
POST /api/build
```

### Upload Video
```
POST /api/upload
Content-Type: multipart/form-data
file: <video.mp4>
```

### Process Video
```
POST /api/process/{filename}?headless=true
```

### Upload and Process (Combined)
```
POST /api/upload-and-process?headless=true
Content-Type: multipart/form-data
file: <video.mp4>
```

### List Recordings
```
GET /api/recordings
```

## File Structure

```
PresageTesting/
├── server.py           # FastAPI server
├── hello_vitals.cpp    # C++ processor
├── CMakeLists.txt      # CMake build config
├── Dockerfile.vitals   # Docker image definition
├── .env                # API key (create this)
├── data/
│   ├── input.json      # Input config for C++
│   └── output.json     # Output from C++
└── recordings/         # Uploaded videos
```

## Requirements

- Docker (for running on non-Ubuntu systems)
- Python 3.8+
- Presage SmartSpectra API key
