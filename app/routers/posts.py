from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from core.database import get_db
from core.models import Post

import logging
logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# --- HTML Routes ---

@router.get("/posts", response_class=HTMLResponse)
async def view_posts(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Post).order_by(Post.created_at.desc()))
    posts = result.scalars().all()
    return templates.TemplateResponse("posts.html", {"request": request, "posts": posts})

# --- API Routes ---

@router.get("/api/posts/{post_id}")
async def get_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single post details"""
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"id": post.id, "title": post.title, "content": post.content, "status": post.status}

@router.put("/api/posts/{post_id}")
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

@router.delete("/api/posts/{post_id}")
async def delete_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a post"""
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    await db.delete(post)
    await db.commit()
    return {"success": True, "message": "Post deleted"}

@router.post("/api/posts/{post_id}/improve")
async def improve_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Ask AI to improve the post content"""
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    from core.llm_caller import call_llm
    
    prompt = f"""
    Please improve the following LinkedIn post to be more engaging, professional, and viral.
    Keep the core message but enhance the hook and call to action.
    
    Original Content:
    {post.content}
    
    Return ONLY the improved content, no explanations.
    """
    
    try:
        improved_content = await call_llm(prompt)
        improved_content = improved_content.replace("```json", "").replace("```", "").strip()
        post.content = improved_content
        await db.commit()
        return {"success": True, "message": "Post improved by AI", "new_content": improved_content}
    except Exception as e:
        logger.error(f"Error improving post: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/posts/{post_id}/revoke")
async def revoke_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Revoke approval (Approved -> Draft)"""
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    post.status = "draft"
    await db.commit()
    return {"success": True, "message": "Post approval revoked"}

@router.post("/api/posts/bulk-delete")
async def bulk_delete_posts(request: Request, db: AsyncSession = Depends(get_db)):
    """Delete multiple posts"""
    data = await request.json()
    post_ids = data.get("post_ids", [])
    
    if not post_ids:
        return {"success": False, "message": "No posts selected"}
        
    await db.execute(delete(Post).where(Post.id.in_(post_ids)))
    await db.commit()
    return {"success": True, "message": f"Deleted {len(post_ids)} posts"}

# --- Actions ---

@router.post("/posts/{post_id}/approve")
async def approve_post(post_id: int, db: AsyncSession = Depends(get_db)):
    # TODO: Add modal support via UI, but strictly this endpoint approves
    await db.execute(update(Post).where(Post.id == post_id).values(status="approved"))
    await db.commit()
    return RedirectResponse(url="/posts", status_code=303)

@router.post("/posts/{post_id}/post")
async def post_to_linkedin_endpoint(post_id: int):
    from core.linkedin_api import post_to_linkedin
    result = await post_to_linkedin(post_id)
    if result.get("success"):
        return RedirectResponse(url="/posts?posted=true", status_code=303)
    else:
        error_msg = result.get("error", "Failed to post")
        return RedirectResponse(url=f"/posts?post_error={error_msg}", status_code=303)
