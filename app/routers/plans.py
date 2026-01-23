from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.database import get_db
from core.models import WeeklyPlan, Post, Curriculum

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/plans", response_class=HTMLResponse)
async def view_plans(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WeeklyPlan).options(selectinload(WeeklyPlan.posts)).order_by(WeeklyPlan.week_start.desc()))
    plans = result.scalars().all()
    
    # Fetch Curriculum data
    curr_result = await db.execute(select(Curriculum).order_by(Curriculum.priority.desc(), Curriculum.created_at.desc()))
    curriculum_items = curr_result.scalars().all()
    
    # Separate by status
    completed = [c for c in curriculum_items if c.status in ("completed", "posted")]
    in_progress = [c for c in curriculum_items if c.status == "in_progress"]
    planned = [c for c in curriculum_items if c.status == "planned"]
    
    return templates.TemplateResponse("plans.html", {
        "request": request, 
        "plans": plans,
        "curriculum_completed": completed,
        "curriculum_in_progress": in_progress,
        "curriculum_planned": planned
    })

@router.get("/plans/{plan_id}", response_class=HTMLResponse)
async def read_plan(plan_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """View details of a specific weekly plan"""
    # Fetch plan
    result = await db.execute(select(WeeklyPlan).where(WeeklyPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    # Fetch associated posts
    result_posts = await db.execute(select(Post).where(Post.plan_id == plan_id).order_by(Post.created_at))
    posts = result_posts.scalars().all()
    
    return templates.TemplateResponse("plan_detail.html", {
        "request": request, 
        "plan": plan, 
        "posts": posts
    })
