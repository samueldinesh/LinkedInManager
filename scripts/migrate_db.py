import asyncio
import logging
from sqlalchemy import text
from core.database import async_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_db():
    logger.info("Migrating database schema...")
    async with async_session() as session:
        async with session.begin():
            # Add approved_by column
            try:
                await session.execute(text("ALTER TABLE posts ADD COLUMN approved_by VARCHAR"))
                logger.info("Added approved_by column")
            except Exception as e:
                logger.warning(f"approved_by exists or error: {e}")

            # Add approval_comment column
            try:
                await session.execute(text("ALTER TABLE posts ADD COLUMN approval_comment TEXT"))
                logger.info("Added approval_comment column")
            except Exception as e:
                logger.warning(f"approval_comment exists or error: {e}")

    logger.info("Migration complete.")

if __name__ == "__main__":
    asyncio.run(migrate_db())
