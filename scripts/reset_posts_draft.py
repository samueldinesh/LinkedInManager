import asyncio
import logging
from sqlalchemy import update
from core.database import async_session
from core.models import Post

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def reset_posts_to_draft():
    logger.info("Resetting all posts to 'draft' status...")
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(
                update(Post).values(status="draft")
            )
            logger.info(f"Updated {result.rowcount} posts to 'draft' status.")
    logger.info("Done.")

if __name__ == "__main__":
    asyncio.run(reset_posts_to_draft())
