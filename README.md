# Content Creation Crew

<div align="center">

**AI-Powered Multi-Agent Content Generation Platform**

Transform any topic into comprehensive, multi-format content with intelligent AI agent collaboration.

[Features](#features) • [Quick Start](#quick-start) • [Architecture](#architecture) • [Documentation](#documentation)

</div>

---

## Overview

**Content Creation Crew** is an advanced AI-powered platform that leverages a multi-agent system to generate high-quality content across multiple formats. Using CrewAI's framework, specialized AI agents collaborate to produce blog posts, social media content, audio scripts, and video scripts from a single topic input.

### What Makes It Special?

- 🤖 **Multi-Agent Collaboration**: Specialized AI agents (Researcher, Writer, Editor, and format specialists) work together to ensure comprehensive, well-researched content
- ⚡ **Real-Time Generation**: Watch your content being created in real-time with live progress updates
- 📝 **Multiple Formats**: Generate blog posts, social media posts, audio scripts, and video scripts simultaneously
- 🎯 **Tier-Based Access**: Flexible subscription tiers from free to enterprise with appropriate features and limits
- 🚀 **Optimized Performance**: Built with caching, parallel processing, and optimized prompts for fast content generation
- 🔐 **Secure & Scalable**: Enterprise-grade authentication, OAuth support, and production-ready architecture

---

## Features

### Core Capabilities

- **Blog Content Generation**: Comprehensive, well-researched blog posts (500+ words) with proper structure
- **Social Media Content**: Platform-optimized posts for LinkedIn, Twitter/X, and Facebook with hashtags and CTAs
- **Audio Scripts**: Conversational scripts optimized for podcasts and audio narration
- **Video Scripts**: YouTube-ready scripts with visual cues, scene descriptions, and pacing markers

### Platform Features

- **Real-Time Streaming**: Server-Sent Events (SSE) for live content generation updates
- **Content Caching**: Intelligent caching system for faster response times on repeated topics
- **OAuth Authentication**: Sign in with Google, Facebook, or GitHub (email/password also supported)
- **Tier-Based Access Control**: Four subscription tiers (Free, Basic, Pro, Enterprise) with different capabilities
- **Responsive Web UI**: Modern, intuitive interface built with Next.js and TailwindCSS
- **RESTful API**: Well-documented API endpoints for programmatic access

### Subscription Tiers

| Tier | Blog | Social Media | Audio | Video | Model | Parallel Tasks |
|------|------|--------------|-------|-------|-------|----------------|
| **Free** | ✅ (5/month) | ❌ | ❌ | ❌ | llama3.2:1b | 1 |
| **Basic** | ✅ (50/month) | ✅ (50/month) | ❌ | ❌ | llama3.2:3b | 2 |
| **Pro** | ✅ (Unlimited) | ✅ (Unlimited) | ✅ (Unlimited) | ✅ (Unlimited) | llama3.1:8b | 4 |
| **Enterprise** | ✅ (Unlimited) | ✅ (Unlimited) | ✅ (Unlimited) | ✅ (Unlimited) | llama3.1:70b | 8 |

---

## Prerequisites

### Required System Dependencies

- **FFmpeg**: Required for video rendering
  - **Windows**: Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) or use `choco install ffmpeg`
  - **macOS**: `brew install ffmpeg`
  - **Linux**: `sudo apt-get install ffmpeg` (Ubuntu/Debian) or `sudo dnf install ffmpeg` (Fedora)
  
  Check installation: `python scripts/check_ffmpeg.py`
  
  Or use the Makefile: `make check-deps` or `make install-ffmpeg`

### Python Dependencies

All Python dependencies are managed via `pyproject.toml` and will be installed automatically.

## Quick Start

### Prerequisites

- **Python**: 3.10, 3.11, 3.12, or 3.13 (3.14 not supported)
- **Node.js**: 18.x or higher (for frontend)
- **Ollama**: Local LLM runtime (see [Ollama Setup](#ollama-setup))
- **UV**: Python package manager (will be installed automatically)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd content_creation_crew
   ```

2. **Install Python dependencies**
   ```bash
   pip install uv
   crewai install
   # Or manually: uv pip install -r pyproject.toml
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env  # If you have an example file
   ```
   
   Create a `.env` file with:
   ```env
   SECRET_KEY=your-secret-key-min-32-characters-long
   OLLAMA_BASE_URL=http://localhost:11434
   DATABASE_URL=postgresql://user:password@localhost:5432/content_crew
   ```

4. **Install frontend dependencies**
   ```bash
   cd web-ui
   npm install
   cd ..
   ```

### Ollama Setup

1. **Install Ollama** (if not already installed)
   - Visit [ollama.ai](https://ollama.ai) and download for your platform
   - Or use Docker: `docker run -d -p 11434:11434 ollama/ollama`

2. **Pull required models**
   ```bash
   ollama pull llama3.2:1b    # For Free tier
   ollama pull llama3.2:3b    # For Basic tier
   ollama pull llama3.1:8b    # For Pro tier
   ollama pull llama3.1:70b   # For Enterprise tier
   ```

3. **Verify Ollama is running**
   ```bash
   curl http://localhost:11434/api/tags
   ```

### FFmpeg Setup

FFmpeg is required for video rendering functionality.

1. **Check if FFmpeg is installed**
   ```bash
   python scripts/check_ffmpeg.py
   # Or
   make check-deps
   ```

2. **Install FFmpeg** (if not installed)

   **Windows:**
   ```powershell
   # Using Chocolatey
   choco install ffmpeg
   
   # Using winget
   winget install ffmpeg
   
   # Or use installation script
   powershell -ExecutionPolicy Bypass -File scripts/install_ffmpeg.ps1
   ```

   **macOS:**
   ```bash
   brew install ffmpeg
   # Or
   bash scripts/install_ffmpeg.sh
   ```

   **Linux:**
   ```bash
   # Ubuntu/Debian
   sudo apt-get update && sudo apt-get install ffmpeg
   
   # Fedora
   sudo dnf install ffmpeg
   
   # Or use installation script
   bash scripts/install_ffmpeg.sh
   ```

   **Using Makefile (auto-detects platform):**
   ```bash
   make install-ffmpeg
   ```

3. **Verify installation**
   ```bash
   ffmpeg -version
   ```

### Running the Application

#### Option 1: Separate Services (Development)

**Terminal 1 - Backend:**
```bash
python api_server.py
# Backend runs on http://localhost:8000
```

**Terminal 2 - Frontend:**
```bash
cd web-ui
npm run dev
# Frontend runs on http://localhost:3000
```

#### Option 2: Docker Compose (Recommended)

```bash
docker-compose up -d
```

This starts:
- PostgreSQL database (port 5432)
- Backend API (port 8000)
- Frontend UI (port 3000)
- Ollama service (port 11434)

**Note**: After starting, pull models in the Ollama container:
```bash
docker exec content-crew-ollama ollama pull llama3.2:1b
```

#### Option 3: Helper Scripts

**Windows (PowerShell):**
```powershell
.\start_backend.ps1
.\start_ui.ps1
```

**Linux/Mac:**
```bash
chmod +x start_backend.sh start_ui.sh
./start_backend.sh
./start_ui.sh
```

### First Run

1. Open your browser to `http://localhost:3000`
2. Click "Sign Up" to create an account
3. Enter a topic (e.g., "Artificial Intelligence in Healthcare")
4. Click "Generate Content"
5. Watch as the AI agents collaborate to create your content!

---

## Architecture

Content Creation Crew uses a modern, scalable architecture:

### System Components

- **Frontend**: Next.js 14 with TypeScript and TailwindCSS
- **Backend**: FastAPI (Python) with async/await support
- **AI Framework**: CrewAI for multi-agent orchestration
- **LLM Runtime**: Ollama (local) or cloud LLM APIs via LiteLLM
- **Database**: PostgreSQL (required for all environments)
- **Authentication**: JWT tokens with OAuth support

### Multi-Agent System

The platform uses specialized AI agents that collaborate:

1. **Researcher**: Conducts research and gathers insights
2. **Writer**: Creates engaging blog content
3. **Editor**: Polishes content for quality and readability
4. **Social Media Specialist**: Adapts content for social platforms
5. **Audio Specialist**: Creates podcast/audio scripts
6. **Video Specialist**: Creates video scripts with visual cues

For detailed architecture documentation, see [ARCHITECTURE.md](./ARCHITECTURE.md).

---

## Configuration

### Backend Configuration

**Agent Configuration**: `src/content_creation_crew/config/agents.yaml`
- Define agent roles, goals, and backstories

**Task Configuration**: `src/content_creation_crew/config/tasks.yaml`
- Define task descriptions and expected outputs

**Tier Configuration**: `src/content_creation_crew/config/tiers.yaml`
- Configure subscription tiers, features, and limits

### Environment Variables

**Backend** (`.env`):
```env
# Required
SECRET_KEY=your-secret-key-min-32-characters
OLLAMA_BASE_URL=http://localhost:11434

# Database (required - PostgreSQL only)
DATABASE_URL=postgresql://user:password@localhost:5432/content_crew
# Or PostgreSQL: postgresql://user:password@host:port/database

# OAuth (optional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
FACEBOOK_CLIENT_ID=your-facebook-client-id
FACEBOOK_CLIENT_SECRET=your-facebook-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# Frontend URLs
FRONTEND_CALLBACK_URL=http://localhost:3000/auth/callback
API_BASE_URL=http://localhost:8000

# CORS (optional)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

**Frontend** (`web-ui/.env.local`):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## API Documentation

### Authentication Endpoints

- `POST /api/auth/signup` - Register new user
- `POST /api/auth/login` - Login with email/password
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/logout` - Logout

### OAuth Endpoints

- `GET /api/auth/oauth/{provider}/login` - Initiate OAuth flow
- `GET /api/auth/oauth/{provider}/callback` - OAuth callback handler

**Providers**: `google`, `facebook`, `github`

### Content Generation

- `POST /api/generate` - Generate content with streaming (SSE)
  ```json
  {
    "topic": "Your topic here",
    "content_types": ["blog", "social"]  // Optional
  }
  ```

### Subscription Endpoints

- `GET /api/subscription/tiers` - Get all tier definitions
- `GET /api/subscription/tiers/{tier_name}` - Get specific tier info

### Health Check

- `GET /health` - Health check endpoint

For detailed API documentation, visit `http://localhost:8000/docs` when the backend is running (FastAPI auto-generated docs).

---

## Development

### Project Structure

```
content_creation_crew/
├── src/
│   └── content_creation_crew/
│       ├── config/          # YAML configuration files
│       ├── services/        # Business logic services
│       ├── middleware/      # Middleware and decorators
│       ├── tools/           # Custom CrewAI tools
│       ├── crew.py          # Main CrewAI crew definition
│       ├── main.py          # CLI entry point
│       ├── database.py      # Database models
│       └── auth.py          # Authentication logic
├── web-ui/                  # Next.js frontend
│   ├── app/                 # Next.js app router pages
│   ├── components/          # React components
│   └── contexts/           # React contexts
├── api_server.py            # FastAPI application entry point
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile               # Backend Dockerfile
└── pyproject.toml           # Python dependencies
```

### Running Tests

```bash
# Backend tests (if available)
pytest tests/

# Frontend tests (if available)
cd web-ui
npm test
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Code Style

- **Python**: Follow PEP 8, use type hints
- **TypeScript**: Use ESLint and Prettier configurations
- **Formatting**: Use `black` for Python, Prettier for TypeScript

---

## Deployment

### Production Considerations

1. **Database**: PostgreSQL-only (SQLite removed)
2. **Environment Variables**: Use secure secret management
3. **HTTPS**: Configure SSL/TLS certificates
4. **Caching**: Consider Redis for distributed caching
5. **Monitoring**: Set up logging and monitoring (e.g., Sentry, DataDog)
6. **Load Balancing**: Deploy multiple FastAPI instances behind a load balancer

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose -f docker-compose.yml up -d

# Or build individual services
docker build -t content-crew-backend .
docker build -t content-crew-frontend ./web-ui
```

### Railway Deployment

The project includes `railway.json` configuration files for easy Railway deployment. See [RAILWAY_DEPLOYMENT.md](./RAILWAY_DEPLOYMENT.md) for details.

---

## Troubleshooting

### Common Issues

**Ollama Connection Error**
- Ensure Ollama is running: `curl http://localhost:11434/api/tags`
- Check `OLLAMA_BASE_URL` environment variable
- Verify models are pulled: `ollama list`

**Database Connection Error**
- Check `DATABASE_URL` environment variable
- Ensure database is accessible
- Run migrations: `alembic upgrade head`

**Frontend Can't Connect to Backend**
- Verify `NEXT_PUBLIC_API_URL` is set correctly
- Check CORS configuration in backend
- Ensure backend is running on the correct port

**Content Generation Fails**
- Check Ollama is running and models are available
- Verify user has appropriate tier for requested content types
- Check server logs for detailed error messages

### Getting Help

- Check [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed system documentation
- Review [USER_GUIDE.md](./USER_GUIDE.md) for user-facing documentation
- See [PRODUCT_REQUIREMENTS.md](./PRODUCT_REQUIREMENTS.md) for feature specifications

---

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Write clear commit messages
- Add tests for new features
- Update documentation as needed
- Follow existing code style
- Ensure all tests pass before submitting

---

## License

[Add your license here]

---

## Support

For support, questions, or feedback:

- 📖 [Documentation](https://docs.crewai.com) - CrewAI framework documentation
- 💬 [Discord](https://discord.com/invite/X4JWnZnxPb) - Join our community
- 🐛 [GitHub Issues](https://github.com/joaomdmoura/crewai/issues) - Report bugs or request features

---

## Acknowledgments

- Built with [CrewAI](https://crewai.com) - Multi-agent AI framework
- Powered by [Ollama](https://ollama.ai) - Local LLM runtime
- Frontend built with [Next.js](https://nextjs.org) and [TailwindCSS](https://tailwindcss.com)

---

<div align="center">

**Made with ❤️ using CrewAI**

[Back to Top](#content-creation-crew)

</div>
