import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.database import SessionLocal
from models.orm import App, Post, Analytics
from models.schemas import AppCreate, AppOut, AppUpdate

logger = logging.getLogger(__name__)

router = APIRouter(tags=["apps"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/apps", response_model=List[AppOut], summary="List all apps")
def list_apps(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    q = db.query(App)
    if active_only:
        q = q.filter(App.is_active == True)
    return q.order_by(App.name).all()


@router.post("/apps", response_model=AppOut, status_code=201, summary="Create a new app")
def create_app(payload: AppCreate, db: Session = Depends(get_db)):
    app = App(**payload.model_dump())
    db.add(app)
    db.commit()
    db.refresh(app)
    logger.info("Created app %d: %s", app.id, app.name)
    return app


@router.get("/apps/{app_id}", response_model=AppOut, summary="Get an app by ID")
def get_app(app_id: int, db: Session = Depends(get_db)):
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    return app


@router.patch("/apps/{app_id}", response_model=AppOut, summary="Update an app")
def update_app(app_id: int, payload: AppUpdate, db: Session = Depends(get_db)):
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(app, field, value)
    db.commit()
    db.refresh(app)
    return app


@router.delete("/apps/{app_id}", status_code=204, summary="Deactivate an app (soft-delete)")
def deactivate_app(app_id: int, db: Session = Depends(get_db)):
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    app.is_active = False
    db.commit()


@router.get("/apps/{app_id}/stats", summary="Per-app post and engagement stats")
def app_stats(app_id: int, db: Session = Depends(get_db)):
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    total_posts = db.query(func.count(Post.id)).filter(Post.app_id == app_id).scalar() or 0
    posted = db.query(func.count(Post.id)).filter(Post.app_id == app_id, Post.status == "posted").scalar() or 0

    avg_engagement = (
        db.query(func.avg(Analytics.engagement_score))
        .join(Post, Post.id == Analytics.post_id)
        .filter(Post.app_id == app_id)
        .scalar()
    )

    return {
        "app_id": app_id,
        "app_name": app.name,
        "total_posts_generated": total_posts,
        "total_posts_published": posted,
        "avg_engagement_score": round(float(avg_engagement), 4) if avg_engagement else None,
        "store_rating": app.raw_store_data.get("rating"),
        "store_review_count": app.raw_store_data.get("review_count"),
    }


@router.post("/apps/{app_id}/refresh-store-data", status_code=202, summary="Trigger immediate App Store / Play Store data refresh")
def refresh_store(app_id: int, db: Session = Depends(get_db)):
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    from workers.appstore_tasks import refresh_store_data
    task = refresh_store_data.delay(app_id)
    return {"app_id": app_id, "task_id": task.id, "message": "Store refresh queued"}


@router.post("/apps/{app_id}/generate-campaign", status_code=202, summary="Generate promo posts for all active trends")
def generate_campaign(
    app_id: int,
    viral_format: Optional[str] = Query(None, description="Viral format key — leave blank for random"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """Trigger content generation for every recent trend, grounding all posts in this app's context."""
    app = db.query(App).filter(App.id == app_id, App.is_active == True).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found or inactive")

    from models.orm import Trend
    trends = db.query(Trend).order_by(Trend.score.desc()).limit(10).all()
    if not trends:
        raise HTTPException(status_code=404, detail="No trends available — run trend discovery first")

    from workers.content_tasks import generate_posts_for_trend
    queued = []
    for trend in trends:
        generate_posts_for_trend.delay(trend.id, viral_format=viral_format, app_id=app_id)
        queued.append(trend.id)

    logger.info("Campaign queued for app %d: %d trends", app_id, len(queued))
    return {"app_id": app_id, "trend_ids_queued": queued, "message": f"Generating posts for {len(queued)} trends"}
