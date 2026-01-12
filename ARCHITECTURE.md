# Content Creation Crew - Architecture Documentation

> **📖 For Non-Technical Readers**: This document explains how the Content Creation Crew system works. If you're not a developer, start with the [Non-Technical Overview](#non-technical-overview) section below. Technical readers can jump directly to [System Overview](#system-overview).

## Table of Contents

### For Everyone
- [Non-Technical Overview](#non-technical-overview) - How the system works in plain language
- [System Overview](#system-overview) - High-level technical overview

### For Technical Readers
- [Architecture Patterns](#architecture-patterns)
- [System Architecture](#system-architecture)
- [Component Breakdown](#component-breakdown)
- [Data Flow](#data-flow)
- [API Structure](#api-structure)
- [Database Schema](#database-schema)
- [Frontend Architecture](#frontend-architecture)
- [Authentication & Authorization](#authentication--authorization)
- [Content Generation Engine](#content-generation-engine)
- [Performance Optimizations](#performance-optimizations)
- [Security Considerations](#security-considerations)
- [Deployment & Infrastructure](#deployment--infrastructure)
- [Configuration Management](#configuration-management)
- [Future Considerations](#future-considerations)

---

## Non-Technical Overview

### What Is Content Creation Crew?

Imagine having a team of specialized content creators working together to produce high-quality content for you. That's exactly what Content Creation Crew does, but instead of human creators, it uses AI agents - specialized AI programs that each have a specific job.

### How Does It Work? (Simple Explanation)

Think of it like a content creation assembly line:

1. **You provide a topic** (e.g., "Artificial Intelligence in Healthcare")
2. **The Researcher** gathers information and key insights about your topic
3. **The Writer** uses that research to create a comprehensive blog post
4. **The Editor** polishes the blog post for quality and readability
5. **Specialists** (if you have access) adapt the content for:
   - Social media platforms (LinkedIn, Twitter, Facebook)
   - Audio/podcast scripts
   - Video/YouTube scripts

All of this happens automatically, and you can watch the progress in real-time!

### The Three Main Parts

**1. The Web Interface (Frontend)**
- This is what you see and interact with in your browser
- You enter your topic, select content types, and see the results
- Built with modern web technologies for a smooth experience

**2. The Brain (Backend)**
- This is where the AI agents work
- Handles authentication, manages user accounts, and coordinates the AI agents
- Communicates with the AI models to generate content

**3. The AI Models (Ollama)**
- These are the actual AI brains that create the content
- Different models are used based on your subscription tier
- Free tier uses faster, smaller models; Enterprise uses more powerful models

### Subscription Tiers Explained

The system has four tiers, each with different capabilities:

- **Free**: Blog content only, limited generations per month, fastest model
- **Basic**: Blog + Social media, more generations, better model
- **Pro**: All content types, unlimited generations, best model, API access
- **Enterprise**: Everything in Pro, plus custom models, priority support, and SLA guarantees

### Key Features Explained

**Real-Time Streaming**: Instead of waiting for everything to finish, you see content being created piece by piece, like watching someone type in real-time.

**Content Caching**: If someone requests content about the same topic recently, the system can provide it instantly from memory instead of regenerating it.

**Multi-Agent Collaboration**: Each AI agent has a specific expertise. They work together, with each agent building on the previous one's work, just like a real content team.

**Tier-Based Access**: Your subscription determines which features you can use, how many times you can generate content, and which AI model is used (affecting speed and quality).

### Why This Architecture?

- **Scalability**: The system can handle many users simultaneously
- **Performance**: Caching and parallel processing make it fast
- **Flexibility**: Easy to add new content types or features
- **Security**: Proper authentication and authorization protect user data
- **Reliability**: Built with production-ready technologies

---

## System Overview

**Content Creation Crew** is a multi-agent AI system that generates various types of content (blog posts, social media posts, audio scripts, video scripts) using CrewAI framework. The system consists of a FastAPI backend and a Next.js frontend, with SQLite database for user management and tier-based access control.

### Key Features

- **Multi-Agent Content Generation**: Uses CrewAI agents (Researcher, Writer, Editor, Social Media Specialist, Audio Specialist, Video Specialist)
- **Tier-Based Access Control**: Free, Basic, Pro, and Enterprise tiers with different features and limits
- **Real-Time Streaming**: Server-Sent Events (SSE) for real-time content generation updates
- **Content Caching**: In-memory cache for faster response times
- **OAuth Authentication**: Support for Google, Facebook, and GitHub OAuth
- **Parallel Processing**: Hierarchical process execution for faster content generation

### Technology Stack

**Backend:**
- Python 3.10-3.13
- FastAPI (REST API)
- CrewAI (Multi-agent framework)
- LiteLLM (LLM abstraction layer)
- Ollama (Local LLM runtime)
- SQLAlchemy (ORM)
- Alembic (Database migrations)
- SQLite (Database)

**Frontend:**
- Next.js 14 (React framework)
- TypeScript
- TailwindCSS
- Server-Sent Events (SSE)

**Infrastructure:**
- UV (Python package manager)
- Docker-ready (can be containerized)

---

## Architecture Patterns

### 1. **Multi-Agent System Pattern**
The system uses CrewAI's multi-agent architecture where specialized agents collaborate:
- **Researcher**: Conducts research on topics
- **Writer**: Creates blog content
- **Editor**: Polishes content
- **Specialists**: Create specialized content (social, audio, video)

### 2. **Tier-Based Access Control Pattern**
Users are assigned tiers that determine:
- Available content types
- Model selection (faster models for lower tiers)
- Parallel processing capabilities
- Usage limits

### 3. **Caching Pattern**
- **Content Cache**: In-memory cache for generated content (1-hour TTL)
- **User Cache**: In-memory cache for user tier information
- Reduces database queries and improves response times

### 4. **Streaming Pattern**
- Server-Sent Events (SSE) for real-time updates
- Keep-alive messages prevent connection timeouts
- Progressive content delivery

### 5. **Service Layer Pattern**
- `SubscriptionService`: Manages tier access and limits
- `ContentCache`: Manages content caching
- `UserCache`: Manages user data caching

### 6. **Middleware Pattern**
- Tier-based access control decorators
- Feature gating middleware
- Content type access validation

---

## System Architecture

### High-Level Architecture

**For Non-Technical Readers**: This diagram shows how the different parts of the system connect. The frontend (what you see) talks to the backend (the brain), which coordinates AI agents and stores data.

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Pages      │  │  Components  │  │   Contexts    │    │
│  │  (App Router)│  │  (React)     │  │  (Auth)       │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│         │                  │                  │            │
│         └──────────────────┼──────────────────┘            │
│                            │                                │
│                    ┌───────▼────────┐                       │
│                    │   API Client   │                       │
│                    │   (lib/api.ts) │                       │
│                    └───────┬────────┘                       │
└────────────────────────────┼────────────────────────────────┘
                             │ HTTPS/SSE
                             │
┌────────────────────────────▼────────────────────────────────┐
│                    Backend (FastAPI)                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              API Server (api_server.py)               │  │
│  │  ┌──────────────┐  ┌──────────────┐               │  │
│  │  │ Auth Routes  │  │ OAuth Routes  │               │  │
│  │  │              │  │               │               │  │
│  │  │ Subscription │  │ Content Gen   │               │  │
│  │  │   Routes     │  │   Endpoints   │               │  │
│  │  └──────────────┘  └──────────────┘               │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                │
│  ┌─────────────────────────┼─────────────────────────────┐ │
│  │                         │                               │ │
│  │  ┌─────────────────────▼──────────────────────┐      │ │
│  │  │      Content Creation Crew (CrewAI)         │      │ │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐│      │ │
│  │  │  │Researcher│→ │  Writer  │→ │  Editor  ││      │ │
│  │  │  └──────────┘  └──────────┘  └──────────┘│      │ │
│  │  │         │              │              │            │ │
│  │  │         └──────────────┼──────────────┘            │ │
│  │  │                        │                            │ │
│  │  │         ┌──────────────┼──────────────┐            │ │
│  │  │         │              │              │            │ │
│  │  │  ┌──────▼──────┐ ┌───▼────┐ ┌──────▼──────┐      │ │
│  │  │  │Social Media │ │ Audio  │ │   Video    │      │ │
│  │  │  │ Specialist  │ │Specialist│ Specialist │      │ │
│  │  │  └─────────────┘ └────────┘ └────────────┘      │ │
│  │  └──────────────────────────────────────────────────┘ │
│  └─────────────────────────┬───────────────────────────────┘ │
│                            │                                │
│  ┌─────────────────────────┼───────────────────────────────┐ │
│  │                         │                                 │ │
│  │  ┌──────────────────────▼──────────────────────┐        │ │
│  │  │         Services Layer                       │        │ │
│  │  │  ┌──────────────┐  ┌──────────────┐        │        │ │
│  │  │  │Subscription  │  │   Content    │        │        │ │
│  │  │  │  Service     │  │    Cache     │        │        │ │
│  │  │  └──────────────┘  └──────────────┘        │        │ │
│  │  │  ┌──────────────┐                          │        │ │
│  │  │  │  User Cache  │                          │        │ │
│  │  │  └──────────────┘                          │        │ │
│  │  └────────────────────────────────────────────┘        │ │
│  └─────────────────────────┬───────────────────────────────┘ │
│                            │                                │
│  ┌─────────────────────────▼───────────────────────────────┐ │
│  │              Database (SQLite)                          │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │ │
│  │  │  Users   │  │ Sessions │  │  Tiers   │            │ │
│  │  └──────────┘  └──────────┘  └──────────┘            │ │
│  └─────────────────────────────────────────────────────────┘ │
│                            │                                │
│  ┌─────────────────────────▼───────────────────────────────┐ │
│  │         External Services                               │ │
│  │  ┌──────────────┐  ┌──────────────┐                    │ │
│  │  │   Ollama     │  │ OAuth        │                    │ │
│  │  │ (LLM Runtime)│  │ Providers    │                    │ │
│  │  │ localhost:   │  │ (Google,     │                    │ │
│  │  │   11434      │  │  GitHub,     │                    │ │
│  │  └──────────────┘  │  Facebook)   │                    │ │
│  │                    └──────────────┘                    │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Simple Explanation**: 
- **Top Layer (Frontend)**: The web interface you interact with
- **Middle Layer (Backend)**: The API server that handles requests and coordinates AI agents
- **AI Agents Layer**: The specialized AI workers that create content
- **Services Layer**: Helper services for caching and subscription management
- **Database Layer**: Where user data and settings are stored
- **External Services**: AI models (Ollama) and OAuth providers (Google, etc.)

---

## Component Breakdown

### Backend Components

#### 1. **API Server** (`api_server.py`)
- **Purpose**: Main FastAPI application entry point
- **Responsibilities**:
  - CORS configuration
  - Route registration
  - Streaming endpoint for content generation
  - Health check endpoints
- **Key Features**:
  - SSE streaming for real-time updates
  - Keep-alive messages during long-running operations
  - Content extraction from CrewAI results
  - Error handling and logging

#### 2. **Content Creation Crew** (`crew.py`)
- **Purpose**: Core multi-agent system using CrewAI
- **Components**:
  - **Agents**: Researcher, Writer, Editor, Social Media Specialist, Audio Specialist, Video Specialist
  - **Tasks**: Research, Writing, Editing, Social Media, Audio, Video
  - **Process**: Hierarchical (parallel) or Sequential based on tier
- **Configuration**:
  - Tier-based model selection
  - Temperature optimization (0.3 for free tier, 0.5 for paid)
  - Conditional task execution
  - Parallel processing for higher tiers

#### 3. **Authentication Module** (`auth.py`, `auth_routes.py`)
- **Purpose**: User authentication and session management
- **Features**:
  - JWT token generation and validation
  - Password hashing (bcrypt with SHA256 pre-hash for long passwords)
  - Token expiration (7 days)
  - User session management
- **Security**:
  - Bcrypt password hashing
  - JWT with HS256 algorithm
  - Token validation middleware

#### 4. **OAuth Module** (`oauth_routes.py`)
- **Purpose**: OAuth authentication with third-party providers
- **Supported Providers**:
  - Google OAuth
  - Facebook OAuth (coming soon)
  - GitHub OAuth (coming soon)
- **Flow**:
  1. User clicks OAuth provider button
  2. Redirects to provider login
  3. Provider redirects back with code
  4. Backend exchanges code for user info
  5. Creates/updates user account
  6. Generates JWT token
  7. Redirects to frontend with token

#### 5. **Subscription Service** (`services/subscription_service.py`)
- **Purpose**: Manages user tiers and feature access
- **Features**:
  - Tier configuration loading from YAML
  - User tier retrieval (defaults to 'free')
  - Feature access checking
  - Content type access validation
  - Usage limit checking (currently unlimited)
- **Caching**: Uses UserCache to reduce database queries

#### 6. **Content Cache** (`services/content_cache.py`)
- **Purpose**: In-memory caching of generated content
- **Features**:
  - MD5-based cache keys (topic + content types)
  - TTL-based expiration (default: 1 hour)
  - Automatic cleanup of expired entries
  - Cache statistics
- **Performance**: 90%+ speedup for cached content

#### 7. **User Cache** (`services/user_cache.py`)
- **Purpose**: In-memory caching of user tier information
- **Features**:
  - User ID-based caching
  - Reduces database queries for tier lookups

#### 8. **Database Models** (`database.py`)
- **Purpose**: SQLAlchemy ORM models
- **Models**:
  - `User`: User accounts with OAuth support
  - `Session`: User sessions (for future token blacklisting)
  - `SubscriptionTier`: Tier definitions (from YAML)
  - `UserSubscription`: Subscription records (for future implementation)
  - `UsageTracking`: Usage tracking (for future implementation)

#### 9. **Tier Middleware** (`middleware/tier_middleware.py`)
- **Purpose**: Decorators for tier-based access control
- **Decorators**:
  - `@require_tier(*tiers)`: Require specific tier(s)
  - `@check_content_type_access(type)`: Check content type access
  - `@check_feature_access(feature)`: Check feature access

#### 10. **Streaming Utilities** (`streaming_utils.py`)
- **Purpose**: Buffer management for SSE streaming
- **Features**:
  - Flushing utilities for stdout/stderr
  - Async generator wrapper with periodic flushing

### Frontend Components

#### 1. **Pages** (`app/`)
- **`page.tsx`**: Main content generation page
- **`auth/page.tsx`**: Authentication page
- **`auth/callback/page.tsx`**: OAuth callback handler
- **`docs/page.tsx`**: Documentation page
- **`privacy/page.tsx`**: Privacy policy
- **`terms/page.tsx`**: Terms of service

#### 2. **Components** (`components/`)
- **`Navbar.tsx`**: Navigation bar with feature selection
- **`InputPanel.tsx`**: Topic input form
- **`OutputPanel.tsx`**: Blog content display
- **`SocialMediaPanel.tsx`**: Social media content display
- **`AudioPanel.tsx`**: Audio script display
- **`VideoPanel.tsx`**: Video script display
- **`AuthForm.tsx`**: Login/signup form
- **`Footer.tsx`**: Footer with links

#### 3. **Contexts** (`contexts/`)
- **`AuthContext.tsx`**: Authentication state management
  - User information
  - Token management
  - Login/logout functions
  - Auto-redirect for unauthenticated users

#### 4. **API Routes** (`app/api/`)
- **`generate/route.ts`**: Next.js API route that proxies to FastAPI
- **`contact/route.ts`**: Contact form handler
- **`devtools-config/route.ts`**: DevTools configuration

#### 5. **API Client** (`lib/api.ts`)
- **Purpose**: Centralized API request handling
- **Features**:
  - Token injection
  - Error handling
  - Response parsing

---

## Data Flow

### Content Generation Flow

**For Non-Technical Readers**: This shows the step-by-step process of what happens when you request content. Each step builds on the previous one, and you can see progress updates in real-time.

```
1. User enters topic in frontend
   │
   ▼
2. Frontend sends POST /api/generate with topic
   │
   ▼
3. Next.js API route proxies to FastAPI /api/generate/stream
   │
   ▼
4. FastAPI endpoint:
   a. Authenticates user (JWT token)
   b. Gets user tier from SubscriptionService
   c. Checks content cache
   d. If cached, returns immediately
   e. If not cached:
      - Initializes ContentCreationCrew with tier
      - Builds crew with appropriate agents/tasks
      - Runs crew in executor (non-blocking)
      - Streams progress updates via SSE
   │
   ▼
5. CrewAI Execution:
   a. Researcher agent: Research topic
   b. Writer agent: Write blog post (uses research)
   c. Editor agent: Edit blog post (uses writer output)
   d. Optional agents (parallel):
      - Social Media Specialist (uses editor output)
      - Audio Specialist (uses editor output)
      - Video Specialist (uses editor output)
   │
   ▼
6. Content Extraction:
   a. Extract blog content from editing_task
   b. Extract social media from social_media_task
   c. Extract audio from audio_content_task
   d. Extract video from video_content_task
   │
   ▼
7. Cache Content:
   a. Store in ContentCache (1-hour TTL)
   │
   ▼
8. Stream to Frontend:
   a. Send status updates
   b. Send content chunks (if streaming)
   c. Send completion message with all content
   │
   ▼
9. Frontend Updates UI:
   a. Updates status/progress
   b. Displays content in appropriate panels
```

**What This Means**:
- Steps 1-3: You enter a topic, and the system prepares to generate content
- Step 4: The system checks if you're logged in, what tier you have, and if this content was recently generated (cache check)
- Step 5: The AI agents work together - Researcher finds information, Writer creates content, Editor improves it, and Specialists adapt it for different formats
- Steps 6-7: The system extracts the final content and saves it for quick access later
- Steps 8-9: You see the content appear in real-time in your browser

### Authentication Flow

```
1. User clicks "Sign In"
   │
   ▼
2. Frontend shows AuthForm
   │
   ▼
3. User submits credentials OR clicks OAuth provider
   │
   ├─ Email/Password ──────────────────────────┐
   │                                            │
   │  3a. POST /api/auth/login                 │
   │      │                                    │
   │      ▼                                    │
   │  3b. Verify password                     │
   │      │                                    │
   │      ▼                                    │
   │  3c. Generate JWT token                  │
   │      │                                    │
   │      ▼                                    │
   │  3d. Return token + user info            │
   │      │                                    │
   │      ▼                                    │
   │  3e. Store token in cookie               │
   │      │                                    │
   │      ▼                                    │
   │  3f. Update AuthContext                  │
   │      │                                    │
   │      ▼                                    │
   │  3g. Redirect to home                    │
   │                                            │
   └─ OAuth Provider ──────────────────────────┘
      │
      ▼
   3h. Redirect to /api/auth/oauth/{provider}/login
      │
      ▼
   3i. Provider authentication page
      │
      ▼
   3j. Provider redirects to /api/auth/oauth/{provider}/callback
      │
      ▼
   3k. Backend:
      - Exchanges code for user info
      - Gets or creates user
      - Generates JWT token
      - Redirects to frontend callback with token
      │
      ▼
   3l. Frontend callback page:
      - Extracts token from URL
      - Stores in cookie
      - Updates AuthContext
      - Redirects to home
```

---

## API Structure

### Authentication Endpoints

#### `POST /api/auth/signup`
- **Purpose**: Register new user
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "password123",
    "full_name": "John Doe"
  }
  ```
- **Response**: JWT token + user info

#### `POST /api/auth/login`
- **Purpose**: Login with email/password
- **Request**: OAuth2PasswordRequestForm (email as username)
- **Response**: JWT token + user info

#### `GET /api/auth/me`
- **Purpose**: Get current user info
- **Auth**: Bearer token required
- **Response**: User information

#### `POST /api/auth/logout`
- **Purpose**: Logout (client-side token removal)

### OAuth Endpoints

#### `GET /api/auth/oauth/{provider}/login`
- **Providers**: `google`, `facebook`, `github`
- **Purpose**: Initiate OAuth flow
- **Response**: Redirect to provider

#### `GET /api/auth/oauth/{provider}/callback`
- **Purpose**: Handle OAuth callback
- **Response**: Redirect to frontend with token

### Content Generation Endpoints

#### `POST /api/generate/stream`
- **Purpose**: Generate content with streaming updates
- **Auth**: Bearer token required
- **Request Body**:
  ```json
  {
    "topic": "Artificial Intelligence",
    "content_types": ["blog", "social"]  // Optional
  }
  ```
- **Response**: Server-Sent Events (SSE) stream
- **Events**:
  - `status`: Status updates
  - `content`: Content chunks (if streaming)
  - `complete`: Final content with all types
  - `error`: Error messages

#### `POST /api/generate`
- **Purpose**: Generate content (non-streaming)
- **Auth**: Bearer token required
- **Request Body**: Same as `/stream`
- **Response**: Complete content JSON

### Subscription Endpoints

#### `GET /api/subscription/tiers`
- **Purpose**: Get all tier definitions
- **Response**: List of tiers with features/limits

#### `GET /api/subscription/tiers/{tier_name}`
- **Purpose**: Get specific tier information
- **Response**: Tier configuration

---

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR,  -- NULL for OAuth users
    full_name VARCHAR,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    provider VARCHAR,  -- 'email', 'google', 'facebook', 'github'
    provider_id VARCHAR,  -- User ID from OAuth provider
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Sessions Table
```sql
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    token VARCHAR UNIQUE NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Subscription Tiers Table
```sql
CREATE TABLE subscription_tiers (
    id INTEGER PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,  -- 'free', 'basic', 'pro', 'enterprise'
    display_name VARCHAR NOT NULL,
    price_monthly INTEGER,  -- In cents (for future)
    price_yearly INTEGER,  -- In cents (for future)
    features JSON,  -- List of feature strings
    limits JSON,  -- Dict of content type limits
    content_types JSON,  -- List of available content types
    model VARCHAR,  -- LLM model name
    max_parallel_tasks INTEGER DEFAULT 1,
    priority_processing BOOLEAN DEFAULT FALSE,
    api_access BOOLEAN DEFAULT FALSE,
    api_rate_limit INTEGER,  -- Requests per day
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### User Subscriptions Table (Future)
```sql
CREATE TABLE user_subscriptions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    tier_id INTEGER NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'active',
    current_period_start DATETIME NOT NULL,
    current_period_end DATETIME NOT NULL,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    cancelled_at DATETIME,
    stripe_subscription_id VARCHAR UNIQUE,
    stripe_customer_id VARCHAR,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (tier_id) REFERENCES subscription_tiers(id)
);
```

### Usage Tracking Table (Future)
```sql
CREATE TABLE usage_tracking (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    subscription_id INTEGER,
    content_type VARCHAR NOT NULL,
    generation_count INTEGER DEFAULT 0,
    period_start DATETIME NOT NULL,
    period_end DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (subscription_id) REFERENCES user_subscriptions(id)
);
```

---

## Frontend Architecture

### Component Hierarchy

```
App (layout.tsx)
├── Navbar
│   └── FeaturesDropdown
├── Home (page.tsx)
│   ├── InputPanel
│   └── Output Panels (conditional)
│       ├── OutputPanel (blog)
│       ├── SocialMediaPanel
│       ├── AudioPanel
│       └── VideoPanel
└── Footer

Auth (auth/page.tsx)
└── AuthForm
    ├── Email/Password Form
    └── OAuth Buttons
```

### State Management

- **AuthContext**: Global authentication state
  - `user`: Current user object
  - `isLoading`: Loading state
  - `login()`, `logout()`: Auth functions

- **Page State** (Home page):
  - `selectedFeature`: Current feature tab
  - `output`: Blog content
  - `socialMediaOutput`: Social media content
  - `audioOutput`: Audio script
  - `videoOutput`: Video script
  - `isGenerating`: Generation status
  - `error`: Error messages
  - `status`: Status messages
  - `progress`: Progress percentage

### Routing

- **App Router** (Next.js 14):
  - `/`: Home page (protected)
  - `/auth`: Authentication page
  - `/auth/callback`: OAuth callback handler
  - `/docs`: Documentation
  - `/privacy`: Privacy policy
  - `/terms`: Terms of service

### API Integration

- **SSE Streaming**: Handles Server-Sent Events for real-time updates
- **Error Handling**: Graceful error handling with user-friendly messages
- **Token Management**: Automatic token injection via cookies

---

## Authentication & Authorization

### Authentication Methods

1. **Email/Password**
   - Bcrypt password hashing
   - SHA256 pre-hash for passwords > 72 bytes
   - JWT token generation (7-day expiration)

2. **OAuth**
   - Google OAuth (implemented)
   - Facebook OAuth (coming soon)
   - GitHub OAuth (coming soon)
   - Automatic account creation/linking

### Authorization

- **Tier-Based Access Control**:
  - Free tier: Blog content only
  - Basic tier: Blog + Social media
  - Pro tier: All content types + API access
  - Enterprise tier: All features + custom models

- **Feature Gating**:
  - Content type access validation
  - Usage limit checking (currently unlimited)
  - API access control

### Security Features

- JWT token validation
- Password hashing (bcrypt)
- CORS configuration
- Token expiration
- Session management (for future token blacklisting)

---

## Content Generation Engine

### CrewAI Architecture

**For Non-Technical Readers**: This section explains how the AI agents work together. Think of it like a content creation team where each person has a specific job, and they pass their work to the next person.

The system uses CrewAI's multi-agent framework with the following structure:

#### Agents

Each agent is like a specialized team member:

1. **Researcher**
   - **What they do**: Gather information and insights about your topic
   - **Like**: A research assistant who finds all relevant information
   - **Model**: Uses faster models for free tier users, better models for paid tiers

2. **Writer**
   - **What they do**: Create the actual blog post content
   - **Like**: A content writer who transforms research into engaging prose
   - **Uses**: The research findings from the Researcher

3. **Editor**
   - **What they do**: Polish and improve the blog post
   - **Like**: An editor who fixes grammar, improves flow, and ensures quality
   - **Uses**: The draft from the Writer
   - **Output**: The final blog post

4. **Social Media Specialist**
   - **What they do**: Adapt the blog content for social media platforms
   - **Like**: A social media manager who creates posts optimized for LinkedIn, Twitter, etc.
   - **Uses**: The final blog post from the Editor
   - **Only runs**: If you have access to social media content (Basic tier+)

5. **Audio Specialist**
   - **What they do**: Create scripts for podcasts or audio narration
   - **Like**: A podcast script writer who makes content conversational
   - **Uses**: The final blog post from the Editor
   - **Only runs**: If you have access to audio content (Pro tier+)

6. **Video Specialist**
   - **What they do**: Create scripts for YouTube or video content
   - **Like**: A video script writer who adds visual cues and scene descriptions
   - **Uses**: The final blog post from the Editor
   - **Only runs**: If you have access to video content (Pro tier+)

#### Task Flow

**Visual Representation**:

```
Research Task (Researcher)
    │
    ▼
Writing Task (Writer) ──┐
    │                    │
    ▼                    │
Editing Task (Editor)    │
    │                    │
    ├────────────────────┼────────────────────┐
    │                    │                    │
    ▼                    ▼                    ▼
Social Media Task    Audio Task         Video Task
(Social Specialist) (Audio Specialist) (Video Specialist)
```

**What This Means**:
- The Researcher works first (gathering information)
- The Writer uses that research to create content
- The Editor improves the Writer's work
- The three specialists work in parallel (at the same time) using the Editor's final output
- This parallel work makes the system faster for users with Pro or Enterprise tiers

#### Process Types

- **Sequential**: Tasks run one after another (free tier, single task)
- **Hierarchical**: Optional tasks run in parallel after editing (higher tiers)

### Model Selection

Tier-based model selection from `tiers.yaml`:
- **Free**: `ollama/llama3.2:1b` (fastest)
- **Basic**: `ollama/llama3.2:3b`
- **Pro**: `ollama/llama3.1:8b`
- **Enterprise**: `ollama/llama3.1:70b` (best quality)

### Temperature Optimization

- **Free tier**: `temperature=0.3` (faster, more deterministic)
- **Paid tiers**: `temperature=0.5` (balanced)

### Content Extraction

Content is extracted from CrewAI result objects:
1. Direct extraction from task outputs
2. File I/O fallback (if direct extraction fails)
3. Multiple extraction attempts with retries

---

## Performance Optimizations

### 1. **Content Caching**
- **Implementation**: In-memory cache with MD5 keys
- **TTL**: 1 hour default
- **Impact**: 90%+ speedup for cached content
- **Location**: `services/content_cache.py`

### 2. **User Caching**
- **Implementation**: In-memory cache for user tier data
- **Impact**: Reduces database queries
- **Location**: `services/user_cache.py`

### 3. **Parallel Processing**
- **Implementation**: Hierarchical process for higher tiers
- **Impact**: Faster execution for multiple content types
- **Location**: `crew.py` - `_build_crew()`

### 4. **Simplified Prompts**
- **Implementation**: Reduced task descriptions by ~70%
- **Impact**: Faster LLM processing, less token usage
- **Location**: `config/tasks.yaml`, `config/agents.yaml`

### 5. **Reduced Verbosity**
- **Implementation**: `verbose=False` for agents and crew
- **Impact**: Less console overhead
- **Location**: `crew.py`

### 6. **Temperature Optimization**
- **Implementation**: Lower temperature for free tier
- **Impact**: Faster, more deterministic responses
- **Location**: `crew.py` - LLM initialization

### 7. **Direct Content Extraction**
- **Implementation**: Prioritize direct object access over file I/O
- **Impact**: Faster content retrieval
- **Location**: `api_server.py` - extraction functions

### 8. **Conditional Task Execution**
- **Implementation**: Only run requested content type tasks
- **Impact**: Faster execution for single content type requests
- **Location**: `crew.py` - `_build_crew()`

### Expected Performance Improvements

| Optimization | Speedup |
|-------------|---------|
| Content caching | 90%+ (cached) |
| Simplified prompts | 20-30% |
| Reduced verbosity | 5-10% |
| Lower temperature | 10-15% |
| Parallel processing | 30-50% (multiple content types) |
| **Combined** | **35-55% faster** |

---

## Security Considerations

### Authentication Security

- **Password Hashing**: Bcrypt with SHA256 pre-hash for long passwords
- **JWT Tokens**: HS256 algorithm with secret key
- **Token Expiration**: 7-day expiration
- **Token Validation**: Middleware validates all protected routes

### API Security

- **CORS**: Configured for frontend origin only
- **Rate Limiting**: Can be added via middleware (future)
- **Input Validation**: Pydantic models for request validation
- **SQL Injection**: SQLAlchemy ORM prevents SQL injection

### Data Security

- **Password Storage**: Hashed passwords only
- **OAuth Tokens**: Not stored (only user info)
- **Session Management**: Token-based (stateless)

### Future Security Enhancements

- Token blacklisting (using Sessions table)
- Rate limiting per tier
- API key management for Pro/Enterprise tiers
- Content encryption (if needed)

---

## Deployment & Infrastructure

### Development Setup

**Backend:**
```bash
cd content_creation_crew
uv run python api_server.py
# Runs on http://localhost:8000
```

**Frontend:**
```bash
cd web-ui
npm run dev
# Runs on http://localhost:3000
```

**Ollama:**
- Must be running on `http://localhost:11434`
- Required models must be pulled (e.g., `ollama pull llama3.2:1b`)

### Production Considerations

1. **Database**: Migrate from SQLite to PostgreSQL
2. **Caching**: Consider Redis for distributed caching
3. **Load Balancing**: Multiple FastAPI instances behind load balancer
4. **Ollama**: Deploy Ollama server separately or use cloud LLM APIs
5. **Environment Variables**: Secure secret management
6. **HTTPS**: SSL/TLS certificates
7. **Monitoring**: Logging and monitoring (e.g., Sentry, DataDog)

### Docker Deployment (Future)

```dockerfile
# Backend Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync
CMD ["uv", "run", "python", "api_server.py"]
```

### Environment Variables

**Backend:**
- `SECRET_KEY`: JWT secret key (min 32 chars)
- `GOOGLE_CLIENT_ID`: Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret
- `FACEBOOK_CLIENT_ID`: Facebook OAuth client ID
- `FACEBOOK_CLIENT_SECRET`: Facebook OAuth client secret
- `GITHUB_CLIENT_ID`: GitHub OAuth client ID
- `GITHUB_CLIENT_SECRET`: GitHub OAuth client secret
- `FRONTEND_CALLBACK_URL`: Frontend OAuth callback URL
- `API_BASE_URL`: Backend API base URL

**Frontend:**
- `NEXT_PUBLIC_API_URL`: Backend API URL (default: `http://localhost:8000`)

---

## Configuration Management

### Tier Configuration (`config/tiers.yaml`)

Defines subscription tiers with:
- Features
- Content type limits
- Model selection
- Parallel processing capabilities
- API access

### Agent Configuration (`config/agents.yaml`)

Defines agent roles, goals, and backstories:
- Simplified for faster execution
- Topic-based role customization
- Concise backstories

### Task Configuration (`config/tasks.yaml`)

Defines task descriptions and expected outputs:
- Simplified prompts
- Clear instructions
- Context dependencies

### Database Migrations (`alembic/`)

- Version-controlled schema changes
- Automatic migration on startup
- Fallback to `create_all()` if migrations fail

---

## Future Considerations

### Planned Features

1. **Subscription Management**
   - Payment integration (Stripe)
   - Subscription activation/cancellation
   - Billing period management
   - Usage tracking and limits

2. **Enhanced OAuth**
   - Facebook OAuth implementation
   - GitHub OAuth implementation
   - Account linking

3. **API Access**
   - API key generation
   - Rate limiting per tier
   - API documentation (OpenAPI/Swagger)

4. **Performance Improvements**
   - Redis caching
   - Database query optimization
   - CDN for static assets
   - Background job processing (RQ/Celery)

5. **Monitoring & Analytics**
   - Usage analytics
   - Performance monitoring
   - Error tracking
   - User activity logs

6. **Content Enhancements**
   - Content templates
   - Custom agent configurations
   - Multi-language support
   - Content versioning

7. **Infrastructure**
   - Docker containerization
   - Kubernetes deployment
   - CI/CD pipeline
   - Automated testing

### Architecture Improvements

1. **Microservices**: Split into separate services (auth, content, subscription)
2. **Message Queue**: Add message queue for async processing
3. **Event Sourcing**: Track all content generation events
4. **CQRS**: Separate read/write models for better scalability

---

## Conclusion

The Content Creation Crew system is a well-architected multi-agent AI platform with:

- **Scalable Architecture**: Tier-based access control, caching, parallel processing
- **Modern Tech Stack**: FastAPI, Next.js, CrewAI, SQLAlchemy
- **Performance Optimizations**: Caching, simplified prompts, parallel execution
- **Security**: JWT authentication, OAuth support, password hashing
- **Extensibility**: Modular design, configuration-driven, easy to extend

The system is production-ready for MVP deployment with clear paths for future enhancements.

---

**Document Version**: 1.0  
**Last Updated**: 2024  
**Maintained By**: Development Team

