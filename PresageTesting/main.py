# main.py
# Author: Dan Shan
# Created: 2024-01-17
# Template to reference for using hello_vitals C++ code
# ** DON'T FORGET TO DEFINE YOUR SMARTSPECTRA_API_KEY IN dotenv.h**
# Build with WSL:
# rm -rf build
# cmake -S . -B build
# cmake --build build --config Release
# Run code with WSL:
# python3 main.py
import json
import subprocess
import os
from pathlib import Path

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# 1. Write to data/input.json
with open(DATA_DIR / "input.json", "w") as f:
    json.dump(
        {"video_path": "/mnt/d/Download/sample_vid1.mp4"}, # insert video path
        f,
        indent=4
    )

# 2. Build and execute C++ file
# cmd = ["xvfb-run", "-a", "./build/hello_vitals"]

# subprocess.run(cmd, check=True)
env = os.environ.copy()
env["DISPLAY"] = ""
env["QT_QPA_PLATFORM"] = "offscreen"
env["OPENCV_LOG_LEVEL"] = "SILENT"

cmd = ["./build/hello_vitals"]
subprocess.run(cmd, check=True, env=env)

# 3. Read data/output.json
with open(DATA_DIR / "output.json") as f:
    output = json.load(f)

print("Pulse:", output["pulse"][:5])
print("Breathing:", output["breathing"][:5])
