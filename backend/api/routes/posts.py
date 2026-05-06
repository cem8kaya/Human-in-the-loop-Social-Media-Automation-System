from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from models.database import get_db
from models.orm import Post, Analytics
from models.schemas import PostOut, PostUpdate, ReviewAction, PaginatedPosts

router = APIRouter(prefix="/posts", tags=["posts"])

VALID_STATUSES = {"generated", "pending_review", "approved", "scheduled", "posted", "rejected"}
VALID_PLATFORMS = {"twitter", "instagram", "tiktok"}


@router.get("/", response_model=PaginatedPosts)
def list_posts(
    status: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    trend_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Post).order_by(Post.created_at.desc())
    if status:
        q = q.filter(Post.status == status)
    if platform:
        q = q.filter(Post.platform == platform)
    if trend_id:
        q = q.filter(Post.trend_id == trend_id)

    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, -(-total // page_size)),
    }


@router.get("/{post_id}", response_model=PostOut)
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(404, "Post not found")
    return post


@router.patch("/{post_id}", response_model=PostOut)
def update_post(post_id: int, updates: PostUpdate, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(404, "Post not found")
    for field, val in updates.model_dump(exclude_none=True).items():
        setattr(post, field, val)
    post.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(post)
    return post


@router.post("/{post_id}/review", response_model=PostOut, summary="Human review action")
def review_post(post_id: int, action: ReviewAction, db: Session = Depends(get_db)):
    """
    Human-in-the-loop review endpoint.
    action.action: approve | reject | edit
    """
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(404, "Post not found")

    if post.status not in ("generated", "pending_review"):
        raise HTTPException(400, f"Cannot review post with status '{post.status}'")

    act = action.action.lower()
    if act == "approve":
        post.status = "approved"
        if action.platform:
            if action.platform not in VALID_PLATFORMS:
                raise HTTPException(400, f"Invalid platform: {action.platform}")
            post.platform = action.platform
        if action.account_id:
            post.account_id = action.account_id
        if action.editor_notes:
            post.editor_notes = action.editor_notes

    elif act == "reject":
        post.status = "rejected"
        post.rejection_reason = action.rejection_reason or "No reason given"

    elif act == "edit":
        # Apply edits and mark approved
        for field in ("hook", "script", "caption", "hashtags"):
            val = getattr(action, field, None)
            if val is not None:
                setattr(post, field, val)
        if action.platform:
            post.platform = action.platform
        if action.editor_notes:
            post.editor_notes = action.editor_notes
        post.status = "approved"

    else:
        raise HTTPException(400, f"Unknown action '{act}'. Use: approve | reject | edit")

    post.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(post)
    return post


@router.post("/{post_id}/schedule", response_model=PostOut, summary="Schedule approved post")
def schedule_post(post_id: int, scheduled_at: datetime, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(404, "Post not found")
    if post.status != "approved":
        raise HTTPException(400, "Post must be approved before scheduling")
    if scheduled_at < datetime.utcnow():
        raise HTTPException(400, "scheduled_at must be in the future")

    post.status = "scheduled"
    post.scheduled_at = scheduled_at
    post.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(post)
    return post


@router.post("/{post_id}/publish-now", summary="Publish an approved post immediately")
def publish_now(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(404, "Post not found")
    if post.status not in ("approved", "scheduled"):
        raise HTTPException(400, "Post must be approved or scheduled to publish")

    post.status = "scheduled"
    post.scheduled_at = datetime.utcnow()
    db.commit()

    from workers.publish_tasks import publish_post_task
    task = publish_post_task.delay(post_id)
    return {"task_id": task.id, "post_id": post_id, "status": "publishing"}


@router.delete("/{post_id}", summary="Delete a post")
def delete_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(404, "Post not found")
    if post.status == "posted":
        raise HTTPException(400, "Cannot delete a posted post")
    db.delete(post)
    db.commit()
    return {"deleted": post_id}
