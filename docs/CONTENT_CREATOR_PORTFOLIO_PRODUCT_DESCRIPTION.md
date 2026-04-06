# Content Creation Crew — Portfolio product description

**Audience:** Product owners, product managers, lead platform architects, technical program leads, and hiring managers evaluating delivery breadth.  
**Use:** Case studies, LinkedIn featured links, resume project blurbs, and interview talking points.

---

## Executive summary

**Content Creation Crew** is a web platform that turns a single topic into **multi-format marketing and creator assets**—blog articles, social copy, audio-oriented scripts, and video-oriented scripts—using a **multi-agent AI pipeline** (research → draft → edit → format specialists), **real-time streaming** of progress, and a **full-stack architecture** suited to SaaS-style delivery. It demonstrates how to pair **generative AI orchestration** with **identity, API design, PostgreSQL persistence, containers, and production-readiness documentation**.

**One-line positioning:**  
*An AI-native content platform that packages multi-agent workflows, streaming UX, and tier-ready commercial logic behind a secure API and web client.*

---

## Experience the product (trust & transparency)

**We invite you to validate the work yourself.** The application exposes a dedicated **`/demo`** route in the web UI: a short, plain-language landing page that sets expectations, then links into the same product surface used in deployment (home and authentication). For hiring managers, clients, and collaborators, **seeing the live flow—streaming progress and multi-format outputs—builds more confidence than slides or repository stars alone.**

**Best practices reflected in this flow:**

| Practice | How it shows up here |
|----------|----------------------|
| **Single primary action** | “Open the application” leads to the main experience; sign-in is a clear secondary step. |
| **Expectations before commitment** | The demo page states what visitors will observe (streaming, outputs, auth behavior). |
| **Low friction** | Exploration does not require payment; account creation may be needed for generation, consistent with a real SaaS boundary. |
| **Honest framing** | Portfolio/evaluation context is explicit so visitors understand why the route exists. |

**How to link it in your portfolio:**  
Use your **deployed base URL** plus **`/demo`** (for example `https://your-app.example.com/demo`). Replace the host with your real production or staging URL (e.g. Railway, Vercel frontend, or custom domain). If you list only the repo, add one line: *“Live demo: [URL]/demo.”*

---

## Problem and opportunity

**Problem:** Teams and creators repeat the same intellectual work—research once, then rewrite for blog, social, audio, and video—with inconsistent quality and high coordination cost.

**Opportunity:** One input can drive a **structured pipeline** that preserves narrative coherence across channels while exposing **governed access** (who can run which modalities, at what parallelism, under which model policy) and **operational discipline** (health checks, migrations, observability hooks, compliance-oriented documentation).

---

## Who it serves (personas)

- **Creators and freelancers** needing fast first drafts across formats.  
- **Marketing and content leads** scaling campaigns without linear headcount.  
- **Platform and product teams** evaluating how to productize LLM workflows with clear boundaries, configuration, and deployment paths.

*(See also `PRODUCT_REQUIREMENTS.md` for full persona detail.)*

---

## Product value proposition

| Dimension | What the product delivers |
|-----------|---------------------------|
| **Outcome** | One topic → **blog + social + audio script + video script** (where enabled by configuration and gates). |
| **Experience** | **Live generation** via streaming (SSE-class patterns) so users see progress rather than an opaque wait. |
| **Quality model** | **Role-specialized agents** (research, writing, editing, format adaptation) rather than a single generic prompt. |
| **Commercial readiness (architected)** | **Tier definitions** in configuration (features, limits, model id, parallelism, API flags); subscription enforcement and payments can be layered on without rewriting the core loop. |
| **Trust** | **Try `/demo`** on the live deployment; **PostgreSQL-only** persistence, JWT auth, OAuth-oriented flows, and a broad **docs** set (security, GDPR-oriented themes, CI/CD, invoicing design, monitoring, deployment). |

---

## Core capabilities (what ships)

1. **Authenticated product surface** — Email/password and OAuth-oriented auth; JWT sessions; protected generation flows.  
2. **Multi-agent content engine** — CrewAI-orchestrated crew with sequential/hierarchical patterns and tier-informed parallelism.  
3. **Multi-format outputs** — Blog, social, audio-leaning and video-leaning scripts with UI panels (Next.js).  
4. **Streaming API** — Generation with server-pushed updates for responsive UX.  
5. **Caching layer** — Content keyed by topic/type to accelerate repeat requests.  
6. **Tier metadata API** — Listing tier capabilities for product surfaces (e.g. `/api/subscription/tiers`).  
7. **Containerized delivery** — Docker / Compose paths documented for repeatable environments.  
8. **Deep operational and compliance documentation** — Security, rate limits, retention, monitoring, backup/DR, migrations—supporting **platform-owner** narratives in interviews.

---

## Technical architecture (platform view)

- **Client:** Next.js (App Router), TypeScript, Tailwind—including **`/demo` as an evaluation entry**.  
- **API:** FastAPI, async-friendly patterns, structured routing for auth, generation, and subscription/tier metadata.  
- **AI layer:** CrewAI for agent graphs; LLM abstraction (e.g. LiteLLM); tier configuration aligned with **cost-aware** models such as `gpt-4o-mini` in `tiers.yaml`.  
- **Data:** **PostgreSQL** enforced in application configuration (SQLite not supported in current config).  
- **Cross-cutting:** Pydantic validation, middleware for tier/content checks, YAML-driven agents, tasks, and tiers.  
- **Media path:** FFmpeg-related documentation for video/voice pipelines where rendering is in scope.

See `ARCHITECTURE.md` and `docs/target-deploy-architecture.md` for diagrams and scaling paths.

---

## Product governance: current state vs. future

**As implemented in code (precision matters for interviews):**

- **Tier assignment:** `SubscriptionService.get_user_tier()` currently returns **`free` for all users** while subscription records are deferred (`subscription_service.py`).  
- **Usage limits:** Values exist in `tiers.yaml`, but **usage metering is largely deferred** (e.g. unlimited path / no-op recording); treat limits as **product-policy hooks** until billing is integrated.  
- **Monetization:** Pricing and some subscription endpoints may be commented or removed while **tier catalog** endpoints remain for discovery and future checkout.

**Roadmap signal:** Payment integration, usage metering, API keys, dashboards, exports—see `PRODUCT_REQUIREMENTS.md` and phase docs under `docs/`.

**Framing for employers:** *You separated “deliver AI value” from “enforce billing and SLA,” without trapping the architecture.*

---

## Differentiation (not “just a ChatGPT wrapper”)

- **Workflow orchestration** with explicit agent roles and dependencies.  
- **SSE-class real-time UX** for long-running jobs.  
- **Policy-as-code** (YAML tiers/agents/tasks).  
- **Operational documentation depth** and a **`/demo` path** for live verification.

---

## What this project demonstrates (by role)

**Product owner / product manager** — Problem framing, personas, phased roadmap, acceptance-style thinking; trade-offs on MVP vs. monetization; API/UX alignment including demo funnel.

**Lead platform / solutions architect** — Web → API → orchestration → LLM → PostgreSQL; security and compliance docs as deliverables; scale path (stateless API, cache, managed DB).

**Contracting profile** — Phased deliverables visible across `docs/`; container and deployment readiness.

---

## Suggested short blurbs (with demo CTA)

**50 words:**  
Content Creation Crew is a full-stack AI product that generates blog, social, audio, and video scripts from one topic using a multi-agent CrewAI pipeline, real-time streaming, and FastAPI + Next.js + PostgreSQL. **See it live:** open **[your URL]/demo**, then step into the app. Tier-ready configuration and deep ops docs included; billing can be layered on.

**100 words:**  
Content Creation Crew shows how to productize generative AI as a SaaS-style platform: authenticated users submit a topic and receive coordinated outputs with streamed progress. The stack spans FastAPI, PostgreSQL, JWT/OAuth patterns, and YAML-driven tiers and agents. **For hiring managers and clients, we invite you to visit the live `/demo` route**—a transparent entry point that explains what you will see before you sign in—then open the application to experience generation end to end. Documentation covers security, compliance-oriented design, CI/CD, and deployment, reflecting platform ownership rather than feature-only code.

---

## Tech stack sidebar (resume / case study)

Python (FastAPI), TypeScript (Next.js 14), PostgreSQL, CrewAI, LiteLLM, Docker, JWT/OAuth, SSE streaming, Alembic/migrations (per project docs), YAML configuration, FFmpeg-related media path, **`/demo` evaluation route**.

---

## Document maintenance

- Keep **demo URL** in sync with your real deployment.  
- When subscription behavior changes, refresh the **Governance** section from `subscription_service.py` and `subscription_routes.py`.  
- **Version:** 1.1 (added live demo invitation and `/demo` route reference).
