# MUST be set before any OAuth imports to allow HTTP for local development
import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from core.database import create_tables

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Routers
from app.routers import dashboard, plans, posts, api, settings

app = FastAPI(title="LinkedIn AI Manager", version="2.0")

# Mount static files (if any in future)
# app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.on_event("startup")
async def startup_event():
    await create_tables()

# Include Routers
app.include_router(dashboard.router)
app.include_router(plans.router)
app.include_router(posts.router)
app.include_router(api.router)
app.include_router(settings.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)