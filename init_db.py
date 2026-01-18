import asyncio
from core.database import create_tables
from core.models import Base

async def main():
    await create_tables()
    print("Database tables created successfully.")

if __name__ == "__main__":
    asyncio.run(main())