# Web UI Setup Guide

This guide will help you set up and run the Content Creation Crew web interface.

## Architecture

The web UI consists of two parts:
1. **Next.js Frontend** (`web-ui/`) - Modern React-based UI
2. **FastAPI Backend** (`api_server.py`) - Python API server that wraps the CrewAI crew

## Prerequisites

- Node.js 18+ installed
- Python 3.10+ with uv (already set up)
- Ollama running with llama3.2:1b model

## Setup Instructions

### 1. Install Frontend Dependencies

```bash
cd web-ui
npm install
```

### 2. Start the FastAPI Backend Server

In the project root directory:

```bash
# Make sure you're in content_creation_crew directory
uv run python api_server.py
```

The API server will start on `http://localhost:8000`

### 3. Start the Next.js Frontend

In a new terminal, navigate to web-ui:

```bash
cd web-ui
npm run dev
```

The frontend will start on `http://localhost:3000`

### 4. Access the Web UI

Open your browser and navigate to: `http://localhost:3000`

## Running Both Servers

You can run both servers simultaneously:

**Terminal 1 (Backend):**
```bash
cd content_creation_crew
uv run python api_server.py
```

**Terminal 2 (Frontend):**
```bash
cd content_creation_crew/web-ui
npm run dev
```

## Features

- ✨ **Sharp Neon Design**: Modern glassmorphism UI with neon accents
- 📝 **Input Panel**: Clean topic input with validation
- 📄 **Output Panel**: Real-time content display with copy/download options
- 🎨 **Calming Effects**: Smooth animations and transitions
- 📱 **Responsive**: Works on desktop, tablet, and mobile

## API Endpoints

The FastAPI server provides:

- `GET /` - API status
- `GET /health` - Health check
- `POST /api/generate` - Generate content for a topic

## Troubleshooting

### API Connection Error

If you see "Failed to connect to API server":
1. Make sure the FastAPI server is running on port 8000
2. Check that Ollama is running
3. Verify the model is available: `ollama list`

### Port Already in Use

If port 3000 or 8000 is already in use:
- Change the Next.js port: `npm run dev -- -p 3001`
- Change the FastAPI port in `api_server.py`: `uvicorn.run(app, host="0.0.0.0", port=8001)`

### Build for Production

```bash
cd web-ui
npm run build
npm start
```

## Customization

### Colors

Edit `web-ui/tailwind.config.js` to customize the neon color scheme.

### API URL

Create `web-ui/.env.local`:
```
API_URL=http://localhost:8000
```

## License

MIT

