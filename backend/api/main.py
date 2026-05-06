import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from config import settings
from models.database import engine
from models.orm import Base
from api.routes import trends, posts, analytics, accounts


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Social Media Automation API",
    description="Human-in-the-loop social media automation for mobile apps & games",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated media assets
media_dir = Path("/tmp/social_media_assets")
media_dir.mkdir(exist_ok=True)
app.mount("/media", StaticFiles(directory=str(media_dir)), name="media")

# Routers
app.include_router(trends.router, prefix="/api/v1")
app.include_router(posts.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(accounts.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/v1/workflow/demo", summary="Run a full demo workflow")
def demo_workflow():
    """
    Seeds mock data and triggers the full pipeline for demonstration.
    """
    from workers.trend_tasks import discover_trends
    from workers.content_tasks import generate_posts_for_top_trends

    t1 = discover_trends.delay()
    t2 = generate_posts_for_top_trends.delay(limit=3)
    return {
        "message": "Demo workflow triggered",
        "tasks": {
            "discover_trends": t1.id,
            "generate_posts": t2.id,
        },
        "next_steps": [
            "GET /api/v1/trends to see discovered trends",
            "GET /api/v1/posts?status=generated to review generated posts",
            "POST /api/v1/posts/{id}/review to approve/reject",
            "POST /api/v1/posts/{id}/schedule to schedule",
            "GET /api/v1/analytics/summary for performance stats",
        ],
    }
