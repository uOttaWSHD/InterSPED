#!/bin/bash

# --- Antigravity Unified Start Script ---

# Colors for better logging
GREEN='\033[0-1;32m'
BLUE='\033[0-1;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting the Antigravity Unified System...${NC}"

# 0. Kill existing uvicorn and SAM processes to free up ports
echo -e "${BLUE}🧹 Cleaning up existing backend processes...${NC}"
pkill -f uvicorn 2>/dev/null
pkill -f "solace" 2>/dev/null
pkill -f "sam" 2>/dev/null
# Kill anything on ports 3000, 8000, 8001
fuser -k 3000/tcp 2>/dev/null
fuser -k 8000/tcp 2>/dev/null
fuser -k 8001/tcp 2>/dev/null
sleep 2

# 1. Sync BetterAuth Schema (Local)
echo -e "${BLUE}🔐 Syncing BetterAuth Database Schema...${NC}"
cd Frontend
# Using --yes to auto-accept the migration in dev
npx better-auth migrate --yes
cd ..

# 1. Check for .env file
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found in root directory."
    exit 1
fi

# 2. Setup Backend
echo -e "${BLUE}📦 Setting up Backend dependencies...${NC}"
cd Backend
if command -v uv &> /dev/null; then
    uv sync
else
    pip install -e .
fi
cd ..

# 3. Setup Frontend
echo -e "${BLUE}📦 Setting up Frontend dependencies...${NC}"
cd Frontend
npm install
cd ..

# 4. Define cleanup function
cleanup() {
    echo -e "\n${BLUE}🛑 Shutting down all services...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    # Specifically kill uvicorn and SAM processes just in case
    pkill -f uvicorn 2>/dev/null
    pkill -f "solace" 2>/dev/null
    pkill -f "sam" 2>/dev/null
    # Free up ports
    fuser -k 3000/tcp 2>/dev/null
    fuser -k 8000/tcp 2>/dev/null
    fuser -k 8001/tcp 2>/dev/null
    exit
}

# Trap SIGINT (Ctrl+C)
trap cleanup SIGINT

# 4.5. Parse arguments
DISABLE_KEY_ROTATION="false"
for arg in "$@"; do
    if [ "$arg" == "--no-rotate" ]; then
        DISABLE_KEY_ROTATION="true"
        echo -e "${BLUE}ℹ️  API key rotation is DISABLED.${NC}"
    fi
done

# 5. Start Unified Backend (API + SAM)
echo -e "${GREEN}🐍 Starting Unified Backend & Solace Agent Mesh (Port 8001 & 8000)...${NC}"
cd Backend
uv run python run_all.py &
BACKEND_PID=$!
cd ..

# 6. Start Frontend
echo -e "${GREEN}react Starting Next.js Frontend (Port 3000)...${NC}"
cd Frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo -e "${GREEN}✅ All services are launching!${NC}"
echo -e "🔗 Frontend: http://localhost:3000"
echo -e "🔗 Backend API: http://localhost:8001"
echo -e "🔗 SAM Gateway: http://localhost:8000"
echo -e "Press Ctrl+C to stop everything."

# Wait for background processes
wait
