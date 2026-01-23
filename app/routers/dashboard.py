from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.models import Trend, WeeklyPlan, Post

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: AsyncSession = Depends(get_db)):
    result_trends = await db.execute(select(Trend).order_by(Trend.discovered_at.desc()).limit(10))
    trends = result_trends.scalars().all()

    result_plans = await db.execute(select(WeeklyPlan).order_by(WeeklyPlan.week_start.desc()).limit(5))
    weekly_plans = result_plans.scalars().all()

    result_posts = await db.execute(select(Post).order_by(Post.created_at.desc()).limit(10))
    posts = result_posts.scalars().all()

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "trends": trends, "weekly_plans": weekly_plans, "posts": posts}
    )

@router.get("/trends", response_class=HTMLResponse)
async def view_trends(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Trend).order_by(Trend.discovered_at.desc()))
    trends = result.scalars().all()
    return templates.TemplateResponse("trends.html", {"request": request, "trends": trends})
