#!/bin/bash

# --- Antigravity Unified Start Script ---

# Colors for better logging
GREEN='\033[0-1;32m'
BLUE='\033[0-1;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting the Antigravity Unified System...${NC}"

# 0. Kill existing uvicorn and SAM processes to free up ports
echo -e "${BLUE}🧹 Cleaning up existing backend processes...${NC}"
pkill -f uvicorn
pkill -f sam
sleep 1

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
    kill $BACKEND_PID
    kill $FRONTEND_PID
    # Specifically kill uvicorn and SAM processes just in case
    pkill -f uvicorn
    pkill -f sam
    exit
}

# Trap SIGINT (Ctrl+C)
trap cleanup SIGINT

# 5. Start Backend
echo -e "${GREEN}python Starting FastAPI Backend (Port 8001)...${NC}"
cd Backend
if command -v uv &> /dev/null; then
    uv run uvicorn app.main:app --port 8001 --reload &
else
    python3 -m uvicorn app.main:app --port 8001 --reload &
fi
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
echo -e "🔗 Backend API: http://localhost:8000"
echo -e "Press Ctrl+C to stop everything."

# Wait for background processes
wait
