from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from models.database import get_db
from models.orm import Analytics, Post
from models.schemas import AnalyticsOut

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/posts/{post_id}", response_model=AnalyticsOut)
def get_post_analytics(post_id: int, db: Session = Depends(get_db)):
    a = db.query(Analytics).filter(Analytics.post_id == post_id).first()
    if not a:
        raise HTTPException(404, "No analytics found for this post")
    return a


@router.get("/top", summary="Top performing posts by engagement score")
def top_posts(
    limit: int = Query(10, le=50),
    platform: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = (
        db.query(Post, Analytics)
        .join(Analytics, Post.id == Analytics.post_id)
        .filter(Post.status == "posted")
        .order_by(desc(Analytics.engagement_score))
    )
    if platform:
        q = q.filter(Post.platform == platform)
    rows = q.limit(limit).all()
    return [
        {
            "post_id": post.id,
            "platform": post.platform,
            "hook": post.hook,
            "caption": post.caption[:100],
            "variation_index": post.variation_index,
            "views": a.views,
            "likes": a.likes,
            "engagement_score": a.engagement_score,
            "content_score": a.content_score,
        }
        for post, a in rows
    ]


@router.get("/summary", summary="Aggregate stats across all posted content")
def analytics_summary(db: Session = Depends(get_db)):
    total_posted = db.query(Post).filter(Post.status == "posted").count()
    totals = db.query(
        func.sum(Analytics.views),
        func.sum(Analytics.likes),
        func.sum(Analytics.comments),
        func.sum(Analytics.shares),
        func.avg(Analytics.engagement_score),
    ).first()

    # Best variation (A/B)
    best_variation = (
        db.query(Post.variation_index, func.avg(Analytics.engagement_score).label("avg_score"))
        .join(Analytics)
        .filter(Post.status == "posted")
        .group_by(Post.variation_index)
        .order_by(desc("avg_score"))
        .first()
    )

    return {
        "total_posted": total_posted,
        "total_views": totals[0] or 0,
        "total_likes": totals[1] or 0,
        "total_comments": totals[2] or 0,
        "total_shares": totals[3] or 0,
        "avg_engagement_score": round(totals[4] or 0, 4),
        "best_variation": best_variation[0] if best_variation else None,
        "best_variation_avg_score": round(best_variation[1], 4) if best_variation else None,
    }


@router.post("/refresh/{post_id}", summary="Force refresh analytics for a post")
def refresh_analytics(post_id: int):
    from workers.analytics_tasks import refresh_post_analytics
    task = refresh_post_analytics.delay(post_id)
    return {"task_id": task.id, "post_id": post_id}
