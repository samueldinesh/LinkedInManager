import asyncio
import logging
from sqlalchemy import select, delete, func
from core.database import async_session
from core.models import WeeklyPlan, Post

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def cleanup_duplicates():
    async with async_session() as session:
        # Find weeks with multiple plans
        # SQLite doesn't strictly support easy distinct on checks, so we'll fetch all and process in python for safety
        result = await session.execute(select(WeeklyPlan).order_by(WeeklyPlan.week_start, WeeklyPlan.created_at.desc()))
        plans = result.scalars().all()
        
        week_map = {}
        for plan in plans:
            week_key = plan.week_start.date()
            if week_key not in week_map:
                week_map[week_key] = []
            week_map[week_key].append(plan)
        
        for week, plan_list in week_map.items():
            if len(plan_list) > 1:
                logger.info(f"Found {len(plan_list)} plans for week {week}. Keeping the most recent one.")
                
                # Keep the first one (most recent due to sort), delete others
                keep_plan = plan_list[0]
                remove_plans = plan_list[1:]
                
                for p in remove_plans:
                    logger.info(f"Deleting duplicate plan ID {p.id} (Status: {p.status})")
                    # Delete associated posts first? Cascade should handle it but manual is safer if no cascade
                    await session.execute(delete(Post).where(Post.plan_id == p.id))
                    await session.execute(delete(WeeklyPlan).where(WeeklyPlan.id == p.id))
        
        await session.commit()
        logger.info("Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(cleanup_duplicates())
