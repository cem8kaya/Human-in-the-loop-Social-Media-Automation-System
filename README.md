# Human-in-the-Loop Social Media Automation System

A self-hostable, open-source MVP for promoting mobile apps and games on social media — with AI-generated content, human review, automated scheduling, and an analytics feedback loop.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                     │
│  Dashboard │ Trend Discovery │ Review Queue │ Analytics       │
└──────────────────────┬──────────────────────────────────────-┘
                       │ REST API
┌──────────────────────▼──────────────────────────────────────-┐
│                    Backend (FastAPI)                           │
│  /trends  /posts  /analytics  /accounts                       │
└──────┬──────────────────────────────────────────┬────────────┘
       │ Celery tasks                              │ SQLAlchemy
┌──────▼──────┐  ┌────────────┐  ┌──────────┐  ┌─▼──────────┐
│  Celery     │  │   Redis    │  │  Ollama  │  │ PostgreSQL │
│  Workers   │  │  (broker)  │  │  (LLM)   │  │    (DB)    │
│  + Beat     │  └────────────┘  └──────────┘  └────────────┘
└─────────────┘
```

---

## Features

| Module | Description |
|---|---|
| **Trend Discovery** | Reddit (PRAW), Twitter/X, TikTok — with mock fallbacks when no credentials present |
| **Content Generation** | 3 variations × viral format per trend. Ollama → OpenRouter → template fallback |
| **Human-in-the-Loop Review** | Approve / Reject / Edit posts with full inline editing |
| **Scheduler & Publisher** | Celery Beat checks every minute; mock + real platform posting |
| **Analytics Feedback Loop** | Engagement scoring, A/B variation ranking, feeds back into prompts |
| **Media Generation** | Pillow text-overlay images + FFmpeg script scaffolding |
| **Multi-account Support** | Account model with per-platform credentials |

### Status Flow

```
generated → pending_review → approved → scheduled → posted
                          ↘ rejected
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | Python 3.12, FastAPI |
| Task Queue | Celery 5 + Redis |
| Database | PostgreSQL 16 |
| AI (primary) | Ollama (llama3 / mistral — local) |
| AI (fallback) | OpenRouter free-tier |
| AI (fallback 2) | Template-based (zero dependencies) |
| Frontend | Next.js 14, React 18, Tailwind CSS |
| Containers | Docker + Docker Compose |

---

## Quick Start

### 1. Clone & configure

```bash
git clone <repo-url>
cd Human-in-the-loop-Social-Media-Automation-System
cp .env.example .env
# Edit .env — all fields have sensible defaults for local dev
```

### 2. Start everything

```bash
docker compose up --build
```

Services that start:
- `http://localhost:3000` — Frontend dashboard
- `http://localhost:8000` — Backend API + Swagger docs at `/docs`
- `http://localhost:8000/health` — Health check
- PostgreSQL, Redis, Celery worker + beat, Ollama

### 3. Pull an LLM (first time only)

```bash
docker compose exec ollama ollama pull llama3
# Or use mistral for lighter resource usage:
docker compose exec ollama ollama pull mistral
```

> **No GPU? No problem.** Ollama runs on CPU. Set `OLLAMA_MODEL=mistral` in `.env` for faster inference.
> If Ollama is slow, set `OPENROUTER_API_KEY` to use the free-tier cloud fallback.
> If neither is available, the template-based fallback generates content instantly.

### 4. Run the demo workflow

```bash
curl -X GET http://localhost:8000/api/v1/workflow/demo
```

Or click **"Run Demo Workflow"** on the dashboard home page.

This will:
1. Discover trending topics (mock data by default)
2. Generate 3 content variations per top trend
3. Queue them for human review

---

## Example Workflow

```
1. System discovers trends from Reddit / TikTok / Twitter
   → { source: "reddit", topic: "I built a mobile game in 30 days", score: 0.88 }

2. AI generates 3 variations using "curiosity_gap" format:
   Hook:    "Nobody knows this game exists — but 50k people downloaded it anyway."
   Script:  "Okay, real talk. This indie dev dropped their game with zero marketing budget..."
   Caption: "Built in 30 days. Zero ads. 50k downloads. Here's the full breakdown."
   Tags:    "#IndieGame, #GameDev, #BuildInPublic, #MobileGaming, ..."

3. Human reviews on dashboard:
   → Edits caption, selects "tiktok" platform, clicks Approve

4. Schedules for 6 PM:
   → Status: scheduled

5. Celery Beat fires at 6 PM:
   → Calls publish API (real or mock)
   → Status: posted

6. Analytics refreshed hourly:
   → Engagement score computed
   → Variation 2 consistently wins → system learns to prefer that format
```

---

## Project Structure

```
├── backend/
│   ├── api/
│   │   ├── main.py                 # FastAPI app, CORS, lifespan, routes
│   │   └── routes/
│   │       ├── trends.py           # GET /trends, POST /trends/discover
│   │       ├── posts.py            # CRUD + review + schedule + publish
│   │       ├── analytics.py        # Engagement stats, A/B scores
│   │       └── accounts.py         # Multi-account management
│   ├── models/
│   │   ├── database.py             # SQLAlchemy engine + session
│   │   ├── orm.py                  # Trend, Post, Analytics, Account models
│   │   └── schemas.py              # Pydantic request/response schemas
│   ├── prompts/
│   │   └── templates.py            # Viral format templates + prompt builders
│   ├── services/
│   │   ├── trend_discovery.py      # Reddit + Twitter + TikTok (real + mock)
│   │   ├── content_generator.py    # Ollama → OpenRouter → template fallback
│   │   ├── publisher.py            # Platform posting (real + mock)
│   │   ├── analytics.py            # Engagement scoring + A/B computation
│   │   └── media_generator.py      # Pillow images + FFmpeg script scaffold
│   ├── workers/
│   │   ├── celery_app.py           # Celery config + Beat schedule
│   │   ├── trend_tasks.py          # discover_trends task
│   │   ├── content_tasks.py        # generate_posts_for_trend task
│   │   ├── publish_tasks.py        # publish_post_task + publish_scheduled_posts
│   │   └── analytics_tasks.py      # refresh_post_analytics + refresh_all_analytics
│   ├── config.py                   # Pydantic settings (env-driven)
│   └── requirements.txt
├── frontend/
│   └── dashboard/                  # Next.js 14 app
│       └── src/
│           ├── app/
│           │   ├── page.tsx        # Dashboard home + stats
│           │   ├── trends/         # Trend discovery page
│           │   ├── review/         # Human review queue
│           │   ├── scheduled/      # Scheduled posts
│           │   └── analytics/      # Analytics & A/B results
│           ├── components/
│           │   ├── Navbar.tsx
│           │   ├── PostCard.tsx    # Full approve/edit/reject/schedule UI
│           │   └── StatusBadge.tsx
│           └── lib/
│               └── api.ts          # Typed axios client
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.worker
│   └── Dockerfile.frontend
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## API Reference

Full interactive docs: `http://localhost:8000/docs`

### Key endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/trends/` | List all trends (sorted by score) |
| `POST` | `/api/v1/trends/discover` | Trigger async trend discovery |
| `POST` | `/api/v1/trends/generate/{trend_id}` | Queue content generation for a trend |
| `GET` | `/api/v1/posts/` | List posts (filterable by status/platform) |
| `POST` | `/api/v1/posts/{id}/review` | Approve / reject / edit a post |
| `POST` | `/api/v1/posts/{id}/schedule` | Schedule an approved post |
| `POST` | `/api/v1/posts/{id}/publish-now` | Publish immediately |
| `GET` | `/api/v1/analytics/summary` | Aggregate stats + A/B winner |
| `GET` | `/api/v1/analytics/top` | Top posts by engagement score |
| `GET` | `/api/v1/workflow/demo` | Run the full demo pipeline |

---

## Configuration

All config is environment-variable driven via `.env`:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | postgres://... | PostgreSQL connection string |
| `REDIS_URL` | redis://... | Redis URL |
| `OLLAMA_MODEL` | `llama3` | Local LLM model name |
| `OPENROUTER_API_KEY` | _(empty)_ | Optional cloud LLM fallback |
| `REDDIT_CLIENT_ID` | _(empty)_ | Optional Reddit API creds |
| `TWITTER_BEARER_TOKEN` | _(empty)_ | Optional Twitter API creds |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed frontend origins |

When API credentials are absent, all sources fall back to curated mock data. The system is fully functional without any external API keys.

---

## Viral Content Formats

The system supports 4 built-in viral formats (configurable in `prompts/templates.py`):

| Format | Description | Example Hook |
|---|---|---|
| `curiosity_gap` | Tease withheld info | "Nobody knows this game exists — yet 50k people downloaded it" |
| `controversy` | Hot take / challenge belief | "Unpopular opinion: Unity is better than Unreal for mobile" |
| `built_in_x_days` | Time-constrained creation story | "I built a complete game in 30 days. Here's what happened." |
| `nobody_knows` | Hidden gem reveal | "This app has zero marketing but it's better than anything on the App Store" |

---

## Bonus Features Implemented

- **A/B Testing**: 3 variations generated per trend; `content_score` tracks which variation performs best
- **Multi-account support**: `Account` model with platform + credentials; posts can be assigned to specific accounts
- **Content scoring algorithm**: Weighted engagement rate (shares x 3, comments x 2, likes x 1, clicks x 1.5) normalized to 0-1

---

## Development

### Run backend locally (without Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Start PostgreSQL and Redis locally, update .env accordingly
uvicorn api.main:app --reload
```

### Run frontend locally

```bash
cd frontend/dashboard
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

### Run Celery worker locally

```bash
cd backend
celery -A workers.celery_app worker --loglevel=info
celery -A workers.celery_app beat --loglevel=info  # separate terminal
```

---

## Extending the System

- **Add a new platform**: Implement a handler in `services/publisher.py`, add to `VALID_PLATFORMS` in `routes/posts.py`
- **Add a new trend source**: Add a `fetch_*` function in `services/trend_discovery.py` and call it from `discover_all_trends`
- **Add a new viral format**: Add an entry to `VIRAL_FORMATS` dict in `prompts/templates.py`
- **Add real video generation**: Extend `services/media_generator.py` — the FFmpeg command template is already scaffolded

---

## License

MIT
