from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Trend(Base):
    __tablename__ = "trends"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String, nullable=False)  # 'breakthrough', 'scheme', 'news'
    source_url = Column(String)
    discovered_at = Column(DateTime, default=datetime.utcnow)
    region = Column(String)  # 'india', 'international', 'global'

class WeeklyPlan(Base):
    __tablename__ = "weekly_plans"

    id = Column(Integer, primary_key=True, index=True)
    week_start = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="draft")  # 'draft', 'approved', 'executing'

    # Relationship to posts
    posts = relationship("Post", back_populates="plan")

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("weekly_plans.id"))
    trend_id = Column(Integer, ForeignKey("trends.id"), nullable=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String, nullable=False)  # 'lesson', 'breakthrough', 'scheme'
    status = Column(String, default="draft")  # 'draft', 'approved', 'posted', 'rejected'
    scheduled_at = Column(DateTime, nullable=True)
    posted_at = Column(DateTime, nullable=True)
    linkedin_post_id = Column(String, nullable=True)
    
    # Governance Fields
    approved_by = Column(String, nullable=True)
    approval_comment = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    plan = relationship("WeeklyPlan", back_populates="posts")
    trend = relationship("Trend")


# ============================================================================
# v2.0 Models: Plugin-based Configuration System
# ============================================================================

class APIProvider(Base):
    """User-configured API providers (LLM, Search, etc.)"""
    __tablename__ = "api_providers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # User-friendly name: "Gemini Free Tier"
    provider_type = Column(String, nullable=False)  # Plugin name: "gemini", "openai"
    provider_category = Column(String, nullable=False)  # "llm", "search"
    api_key = Column(String, nullable=True)  # Encrypted API key
    model_name = Column(String, nullable=True)  # Model identifier
    config = Column(JSON, nullable=True)  # Additional provider-specific config
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # Higher = preferred
    daily_quota = Column(Integer, nullable=True)  # Custom quota limit
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ContentTopic(Base):
    """User-configured content topics"""
    __tablename__ = "content_topics"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # "Quantum Computing", "AI News"
    description = Column(Text)
    search_queries = Column(JSON, nullable=False)  # List of search queries
    is_active = Column(Boolean, default=True)
    strategy_plugin = Column(String, nullable=True)  # Which strategy to use
    config = Column(JSON, nullable=True)  # Topic-specific configuration
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserSettings(Base):
    """Global user settings (key-value store)"""
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Curriculum(Base):
    """Tracks Micro-Course series lifecycle"""
    __tablename__ = "curriculum"
    
    id = Column(Integer, primary_key=True, index=True)
    topic_name = Column(String, nullable=False)  # e.g., "Quantum Gates"
    topic_id = Column(Integer, ForeignKey("content_topics.id"), nullable=True)  # Link to ContentTopic
    status = Column(String, default="planned")  # planned, in_progress, completed, posted
    
    # Series tracking
    week_start = Column(DateTime, nullable=True)  # When the series started
    week_end = Column(DateTime, nullable=True)  # When the series ended
    
    # Link to actual posts (optional, for tracking)
    part1_post_id = Column(Integer, ForeignKey("posts.id"), nullable=True)
    part2_post_id = Column(Integer, ForeignKey("posts.id"), nullable=True)
    part3_post_id = Column(Integer, ForeignKey("posts.id"), nullable=True)
    
    # Metadata
    priority = Column(Integer, default=0)  # Higher = teach first
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    topic = relationship("ContentTopic")
