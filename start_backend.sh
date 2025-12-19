#!/bin/bash
# Shell script to start the backend API server

echo "Starting Content Creation Crew API Server..."
echo ""

# Check if port 8000 is already in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "Warning: Port 8000 is already in use!"
    echo "You may need to stop the existing process first."
    echo ""
fi

# Start the server
echo "Starting server on http://localhost:8000"
echo "Press Ctrl+C to stop the server"
echo ""

uv run python api_server.py

