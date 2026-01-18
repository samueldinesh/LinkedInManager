from fastapi import FastAPI, Request, Depends, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import asyncio
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from core.database import get_db, create_tables
from core.models import Trend, WeeklyPlan, Post
from core.linkedin_api import post_to_linkedin

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

@app.on_event("startup")
async def startup_event():
    await create_tables()

@app.get("/", response_class=HTMLResponse)
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

@app.get("/trends", response_class=HTMLResponse)
async def view_trends(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Trend).order_by(Trend.discovered_at.desc()))
    trends = result.scalars().all()
    return templates.TemplateResponse("trends.html", {"request": request, "trends": trends})

@app.get("/plans", response_class=HTMLResponse)
async def view_plans(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WeeklyPlan).order_by(WeeklyPlan.week_start.desc()))
    plans = result.scalars().all()
    return templates.TemplateResponse("plans.html", {"request": request, "plans": plans})

@app.get("/posts", response_class=HTMLResponse)
async def view_posts(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Post).order_by(Post.created_at.desc()))
    posts = result.scalars().all()
    return templates.TemplateResponse("posts.html", {"request": request, "posts": posts})

@app.post("/posts/{post_id}/approve")
async def approve_post(post_id: int, db: AsyncSession = Depends(get_db)):
    await db.execute(update(Post).where(Post.id == post_id).values(status="approved"))
    await db.commit()
    return RedirectResponse(url="/posts", status_code=303)

@app.post("/posts/{post_id}/post")
async def post_to_linkedin_endpoint(post_id: int):
    result = await post_to_linkedin(post_id)
    if result.get("success"):
        return {"message": "Post published successfully"}
    else:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to post"))

# Run agents manually
@app.get("/run-agents", response_class=HTMLResponse)
async def run_agents_page(request: Request):
    return templates.TemplateResponse("run_agents.html", {"request": request})

@app.get("/api/workflow-status")
async def get_workflow_status():
    """Get the current workflow execution status"""
    from core.orchestrator import orchestrator
    return orchestrator.get_status()

@app.post("/run-agents")
async def run_agents(background_tasks: BackgroundTasks, request: Request):
    """Trigger the agent workflow manually with selected steps"""
    from core.orchestrator import orchestrator
    
    # Get selected steps from form
    form_data = await request.form()
    selected_steps = form_data.getlist("steps")
    
    # Default to all steps if none selected
    if not selected_steps:
        selected_steps = ['trends', 'strategy', 'content']
    
    async def run_workflow():
        try:
            # Clear logs and set status to running
            orchestrator.clear_logs()
            
            # Setup API pool if not already done
            if not orchestrator.api_pool:
                await orchestrator.setup_api_pool()
            
            # Run selected steps
            result = await orchestrator.run_full_workflow(steps=selected_steps)
            
            # Log results
            if result["success"]:
                logger.info(f"✓ Workflow completed: {result['message']}")
            else:
                logger.warning(f"⚠ Workflow incomplete: {result['message']}")
                
        except Exception as e:
            logger.error(f"Workflow error: {e}", exc_info=True)
    
    background_tasks.add_task(run_workflow)
    
    # Check if AJAX request (JSON)
    accept = request.headers.get("accept", "")
    if "application/json" in accept:
        return {"status": "started", "message": "Workflow started in background"}
    
    # Otherwise redirect (legacy form submit)
    return RedirectResponse(
        url="/?workflow_started=true", 
        status_code=303
    )

# --- Post Management Endpoints ---

@app.get("/api/posts/{post_id}")
async def get_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single post details"""
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"id": post.id, "title": post.title, "content": post.content, "status": post.status}

@app.put("/api/posts/{post_id}")
async def update_post(post_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """Update a post's content manually"""
    data = await request.json()
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    post.content = data.get("content", post.content)
    post.title = data.get("title", post.title)
    await db.commit()
    return {"success": True, "message": "Post updated"}

@app.delete("/api/posts/{post_id}")
async def delete_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a post"""
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    await db.delete(post)
    await db.commit()
    return {"success": True, "message": "Post deleted"}

@app.post("/api/posts/{post_id}/improve")
async def improve_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Ask AI to improve the post content"""
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Use the shared call_llm function
    from core.llm_caller import call_llm
    
    prompt = f"""
    Please improve the following LinkedIn post to be more engaging, professional, and viral.
    Keep the core message but enhance the hook and call to action.
    
    Original Content:
    {post.content}
    
    Return ONLY the improved content, no explanations.
    """
    
    try:
        # Calls intelligent API pool (Gemma/Gemini)
        improved_content = await call_llm(prompt)
        # Clean up response
        improved_content = improved_content.replace("```json", "").replace("```", "").strip()
        
        # Update DB
        post.content = improved_content
        await db.commit()
        return {"success": True, "message": "Post improved by AI", "new_content": improved_content}
    except Exception as e:
        logger.error(f"Error improving post: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/posts/{post_id}/improve")
async def improve_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Ask AI to improve the post content"""
    # ... (existing code) ...
    # I will keep the existing implementation here, just ensuring I don't overwrite it wrongly
    # But since I am replacing a block, I should re-state the previous function or target specifically.
    # To be safe and avoid "target content" errors, I will add the NEW routes after the existing ones.
    pass 

# ... (Intentionally skipping to new adds to avoid large replace blocks) ...

# NEW ROUTES BELOW

@app.get("/plans/{plan_id}", response_class=HTMLResponse)
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

@app.post("/api/posts/{post_id}/revoke")
async def revoke_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Revoke approval (Approved -> Draft)"""
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    post.status = "draft"
    await db.commit()
    return {"success": True, "message": "Post approval revoked"}

@app.post("/api/posts/bulk-delete")
async def bulk_delete_posts(request: Request, db: AsyncSession = Depends(get_db)):
    """Delete multiple posts"""
    data = await request.json()
    post_ids = data.get("post_ids", [])
    
    if not post_ids:
        return {"success": False, "message": "No posts selected"}
        
    # Execute delete
    from sqlalchemy import delete
    await db.execute(delete(Post).where(Post.id.in_(post_ids)))
    await db.commit()
    
    return {"success": True, "message": f"Deleted {len(post_ids)} posts"}

# Settings pages (placeholders)
@app.get("/settings/apis", response_class=HTMLResponse)
async def settings_apis(request: Request):
    return templates.TemplateResponse("settings_apis.html", {"request": request})

@app.get("/settings/topics", response_class=HTMLResponse)
async def settings_topics(request: Request):
    return templates.TemplateResponse("settings_topics.html", {"request": request})

# Placeholder for LinkedIn OAuth routes
@app.get("/linkedin/auth")
async def linkedin_auth():
    # This would redirect to LinkedIn for authorization
    return {"message": "LinkedIn OAuth not implemented yet"}

@app.get("/linkedin/callback")
async def linkedin_callback():
    # Handle OAuth callback
    return {"message": "OAuth callback not implemented yet"}