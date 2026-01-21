"""
Quick test to verify dashboard routes work.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from core.database import async_session, create_tables
from core.models import Trend, WeeklyPlan, Post
from datetime import datetime


async def test_dashboard_queries():
    """Test that all dashboard queries work"""
    print("Testing dashboard database queries...")
    
    # Create tables
    await create_tables()
    print("✓ Database initialized")
    
    # Test queries
    async with async_session() as db:
        # Test trends query
        result = await db.execute(select(Trend).order_by(Trend.discovered_at.desc()))
        trends = result.scalars().all()
        print(f"✓ Trends query works ({len(trends)} trends)")
        
        # Test plans query
        result = await db.execute(select(WeeklyPlan).order_by(WeeklyPlan.week_start.desc()))
        plans = result.scalars().all()
        print(f"✓ Plans query works ({len(plans)} plans)")
        
        # Test posts query
        result = await db.execute(select(Post).order_by(Post.created_at.desc()))
        posts = result.scalars().all()
        print(f"✓ Posts query works ({len(posts)} posts)")
    
    print("\n✅ All dashboard queries working!")


if __name__ == "__main__":
    asyncio.run(test_dashboard_queries())
