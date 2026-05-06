from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from models.database import get_db
from models.orm import Trend
from models.schemas import TrendOut, TrendCreate

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("/", response_model=List[TrendOut])
def list_trends(
    source: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Trend).order_by(Trend.score.desc())
    if source:
        q = q.filter(Trend.source == source)
    return q.limit(limit).all()


@router.get("/{trend_id}", response_model=TrendOut)
def get_trend(trend_id: int, db: Session = Depends(get_db)):
    trend = db.query(Trend).filter(Trend.id == trend_id).first()
    if not trend:
        raise HTTPException(404, "Trend not found")
    return trend


@router.post("/discover", summary="Trigger trend discovery now")
def trigger_discovery(background_tasks: BackgroundTasks):
    from workers.trend_tasks import discover_trends
    task = discover_trends.delay()
    return {"task_id": task.id, "status": "queued"}


@router.post("/generate/{trend_id}", summary="Generate content for a trend")
def generate_content(trend_id: int, viral_format: Optional[str] = None):
    from workers.content_tasks import generate_posts_for_trend
    task = generate_posts_for_trend.delay(trend_id, viral_format)
    return {"task_id": task.id, "trend_id": trend_id, "status": "queued"}
