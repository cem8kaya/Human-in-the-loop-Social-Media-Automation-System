from datetime import date, datetime
from typing import Any, Dict, Optional, List
from pydantic import BaseModel


# ── App ────────────────────────────────────────────────────────────────────

class AppBase(BaseModel):
    name: str
    platform: str = "both"
    app_store_url: Optional[str] = None
    play_store_url: Optional[str] = None
    bundle_id: Optional[str] = None
    description: Optional[str] = None
    tagline: Optional[str] = None
    target_audience: Optional[str] = None
    genre: Optional[str] = None
    launch_date: Optional[date] = None
    screenshots_dir: Optional[str] = None
    promo_video_url: Optional[str] = None
    voice_profile: Dict[str, Any] = {}

class AppCreate(AppBase):
    pass

class AppUpdate(BaseModel):
    name: Optional[str] = None
    platform: Optional[str] = None
    app_store_url: Optional[str] = None
    play_store_url: Optional[str] = None
    bundle_id: Optional[str] = None
    description: Optional[str] = None
    tagline: Optional[str] = None
    target_audience: Optional[str] = None
    genre: Optional[str] = None
    launch_date: Optional[date] = None
    screenshots_dir: Optional[str] = None
    promo_video_url: Optional[str] = None
    is_active: Optional[bool] = None
    voice_profile: Optional[Dict[str, Any]] = None

class AppOut(AppBase):
    id: int
    is_active: bool
    raw_store_data: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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
    app_id: Optional[int] = None

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
    app_id: Optional[int] = None
    status: str
    rejection_reason: Optional[str]
    editor_notes: Optional[str]
    media_url: Optional[str]
    scheduled_at: Optional[datetime]
    posted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    # AutoPilot fields
    viral_format: Optional[str] = None
    confidence_score: Optional[float] = None
    auto_approved: bool = False
    predicted_engagement_score: Optional[float] = None

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


# ── SystemConfig ───────────────────────────────────────────────────────────

class SystemConfigOut(BaseModel):
    autopilot_enabled: bool
    autopilot_confidence_threshold: float

    class Config:
        from_attributes = True


class SystemConfigUpdate(BaseModel):
    autopilot_enabled: Optional[bool] = None
    autopilot_confidence_threshold: Optional[float] = None
