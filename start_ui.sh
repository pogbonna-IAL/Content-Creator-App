#!/bin/bash
# Start script for Web UI (Linux/Mac)

echo "Starting Content Creation Crew Web UI..."
echo ""

# Start FastAPI backend in background
echo "Starting FastAPI backend server..."
uv run python api_server.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start Next.js frontend
echo "Starting Next.js frontend..."
cd web-ui
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Both servers are running!"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for user interrupt
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait

