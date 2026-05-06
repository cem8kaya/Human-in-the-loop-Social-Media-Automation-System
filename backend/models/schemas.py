from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# ── Trend ──────────────────────────────────────────────────────────────────

class TrendBase(BaseModel):
    source: str
    topic: str
    score: float = 0.0
    raw_data: dict = {}

class TrendCreate(TrendBase):
    pass

class TrendOut(TrendBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Post ───────────────────────────────────────────────────────────────────

class PostBase(BaseModel):
    hook: str
    script: str
    caption: str
    hashtags: str
    platform: str = "twitter"
    variation_index: int = 0

class PostCreate(PostBase):
    trend_id: Optional[int] = None

class PostUpdate(BaseModel):
    hook: Optional[str] = None
    script: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[str] = None
    platform: Optional[str] = None
    status: Optional[str] = None
    rejection_reason: Optional[str] = None
    editor_notes: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    account_id: Optional[str] = None

class PostOut(PostBase):
    id: int
    trend_id: Optional[int]
    status: str
    rejection_reason: Optional[str]
    editor_notes: Optional[str]
    media_url: Optional[str]
    scheduled_at: Optional[datetime]
    posted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Review Actions ─────────────────────────────────────────────────────────

class ReviewAction(BaseModel):
    action: str          # approve | reject | edit
    platform: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    editor_notes: Optional[str] = None
    hook: Optional[str] = None
    script: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[str] = None
    account_id: Optional[str] = None


# ── Analytics ──────────────────────────────────────────────────────────────

class AnalyticsOut(BaseModel):
    id: int
    post_id: int
    views: int
    likes: int
    comments: int
    shares: int
    clicks: int
    engagement_score: float
    content_score: float
    fetched_at: datetime

    class Config:
        from_attributes = True


# ── Account ────────────────────────────────────────────────────────────────

class AccountCreate(BaseModel):
    name: str
    platform: str
    handle: str
    credentials: dict = {}

class AccountOut(BaseModel):
    id: int
    name: str
    platform: str
    handle: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Pagination ─────────────────────────────────────────────────────────────

class PaginatedPosts(BaseModel):
    items: List[PostOut]
    total: int
    page: int
    page_size: int
    pages: int
