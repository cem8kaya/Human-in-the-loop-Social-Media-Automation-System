from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey, JSON, Date
from sqlalchemy.orm import relationship
from models.database import Base


class Trend(Base):
    __tablename__ = "trends"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50))            # reddit, tiktok, twitter
    topic = Column(String(500))
    score = Column(Float, default=0.0)     # relevance score 0-1
    raw_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    posts = relationship("Post", back_populates="trend")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    trend_id = Column(Integer, ForeignKey("trends.id"), nullable=True)

    # Content
    hook = Column(Text)
    script = Column(Text)
    caption = Column(Text)
    hashtags = Column(Text)          # comma-separated
    variation_index = Column(Integer, default=0)  # 0, 1, 2 for A/B/C

    # Targeting
    platform = Column(String(50), default="twitter")   # twitter, instagram, tiktok
    account_id = Column(String(100), nullable=True)    # multi-account support

    # AutoPilot
    viral_format = Column(String(50), nullable=True)
    confidence_score = Column(Float, nullable=True)
    auto_approved = Column(Boolean, default=False)
    predicted_engagement_score = Column(Float, nullable=True)

    # Status flow: generated → pending_review → approved → scheduled → posted
    status = Column(String(30), default="generated")
    rejection_reason = Column(Text, nullable=True)
    editor_notes = Column(Text, nullable=True)

    # Media
    media_url = Column(Text, nullable=True)
    media_type = Column(String(20), nullable=True)     # image, video

    # Scheduling
    scheduled_at = Column(DateTime, nullable=True)
    posted_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    trend = relationship("Trend", back_populates="posts")
    analytics = relationship("Analytics", back_populates="post", uselist=False)


class Analytics(Base):
    __tablename__ = "analytics"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), unique=True)

    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    clicks = Column(Integer, default=0)

    engagement_score = Column(Float, default=0.0)   # computed metric
    content_score = Column(Float, default=0.0)      # A/B ranking score

    raw_data = Column(JSON, default=dict)
    fetched_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("Post", back_populates="analytics")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    platform = Column(String(50))
    handle = Column(String(100))
    credentials = Column(JSON, default=dict)   # encrypted in prod
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemConfig(Base):
    """Key-value store for runtime system settings (autopilot, thresholds, etc.)."""
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PostingPerformance(Base):
    """Per-(platform, hour_of_day) engagement tracking for data-driven optimal posting times."""
    __tablename__ = "posting_performance"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(String(100), nullable=True, index=True)
    platform = Column(String(50), nullable=False)
    hour_of_day = Column(Integer, nullable=False)   # 0-23 UTC
    day_of_week = Column(Integer, nullable=True)    # 0=Mon … 6=Sun
    sample_count = Column(Integer, default=0)
    avg_engagement = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
