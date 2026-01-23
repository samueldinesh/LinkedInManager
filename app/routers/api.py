from fastapi import APIRouter, Request, BackgroundTasks, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

logger = __import__("logging").getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Run agents manually
@router.get("/run-agents", response_class=HTMLResponse)
async def run_agents_page(request: Request):
    return templates.TemplateResponse("run_agents.html", {"request": request})

@router.get("/api/workflow-status")
async def get_workflow_status():
    """Get the current workflow execution status"""
    from core.orchestrator import orchestrator
    return orchestrator.get_status()

@router.post("/run-agents")
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

# LinkedIn Auth Routes
@router.get("/linkedin/auth")
async def linkedin_auth():
    from core.linkedin_api import get_linkedin_auth_url
    url, state = get_linkedin_auth_url()
    # In a real app, save state to session
    return RedirectResponse(url=url)

@router.get("/linkedin/callback")
async def linkedin_callback(code: str = None, error: str = None):
    if error:
        return RedirectResponse(url=f"/?linkedin_error={error}")
    
    from core.linkedin_api import exchange_code_for_token
    result = await exchange_code_for_token(code)
    
    if result.get("success"):
        return RedirectResponse(url="/?linkedin_connected=true")
    else:
        return RedirectResponse(url=f"/?linkedin_error={result.get('error')}")

@router.get("/api/linkedin/status")
async def linkedin_status():
    from core.linkedin_api import is_authenticated
    # Mock user info for now if authenticated
    if is_authenticated():
        return {
            "connected": True, 
            "user": {"name": "User", "picture": "https://via.placeholder.com/150"}
        }
    return {"connected": False}
