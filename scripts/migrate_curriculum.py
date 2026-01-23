import asyncio
import logging
from sqlalchemy import text
from core.database import async_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_curriculum():
    logger.info("Creating curriculum table...")
    async with async_session() as session:
        async with session.begin():
            # Create curriculum table
            try:
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS curriculum (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        topic_name VARCHAR NOT NULL,
                        topic_id INTEGER,
                        status VARCHAR DEFAULT 'planned',
                        week_start DATETIME,
                        week_end DATETIME,
                        part1_post_id INTEGER,
                        part2_post_id INTEGER,
                        part3_post_id INTEGER,
                        priority INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (topic_id) REFERENCES content_topics(id),
                        FOREIGN KEY (part1_post_id) REFERENCES posts(id),
                        FOREIGN KEY (part2_post_id) REFERENCES posts(id),
                        FOREIGN KEY (part3_post_id) REFERENCES posts(id)
                    )
                """))
                logger.info("Curriculum table created successfully.")
            except Exception as e:
                logger.warning(f"Table may already exist: {e}")

    logger.info("Migration complete.")

if __name__ == "__main__":
    asyncio.run(migrate_curriculum())
