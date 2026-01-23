from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.models import ContentTopic

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/settings/topics", response_class=HTMLResponse)
async def settings_topics(request: Request, db: AsyncSession = Depends(get_db)):
    """View topics management page"""
    result = await db.execute(select(ContentTopic).where(ContentTopic.is_active == True))
    topics = result.scalars().all()
    return templates.TemplateResponse("settings_topics.html", {"request": request, "topics": topics})

@router.post("/api/settings/topics")
async def add_topic(request: Request, db: AsyncSession = Depends(get_db)):
    """Add a new content topic"""
    try:
        data = await request.json()
        name = data.get("name")
        queries = data.get("queries", []) # List of strings
        description = data.get("description", "")
        
        if not name or not queries:
            return {"success": False, "message": "Name and queries are required"}
            
        new_topic = ContentTopic(
            name=name,
            description=description,
            search_queries=queries,
            is_active=True
        )
        db.add(new_topic)
        await db.commit()
        return {"success": True, "message": "Topic added", "id": new_topic.id}
    except Exception as e:
        return {"success": False, "message": str(e)}

@router.delete("/api/settings/topics/{topic_id}")
async def delete_topic(topic_id: int, db: AsyncSession = Depends(get_db)):
    topic = await db.get(ContentTopic, topic_id)
    if topic:
        topic.is_active = False # Soft delete
        await db.commit()
        return {"success": True}
    return {"success": False, "message": "Topic not found"}

@router.get("/settings/apis", response_class=HTMLResponse)
async def settings_apis(request: Request):
    return templates.TemplateResponse("settings_apis.html", {"request": request})
