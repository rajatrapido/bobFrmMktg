from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.firebase_service import FirestoreService
from app.services.report_engine import ReportEngine
from app.services.auth_service import verify_token, AdwordsOAuthService
from typing import List, Optional
import os

app = FastAPI(title="BobFrmMktg API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = FirestoreService()
engine = ReportEngine()
auth_service = AdwordsOAuthService()
scheduler = BackgroundScheduler()

def scheduled_report_job():
    print("Running scheduled weekly report generation...")
    engine.generate_and_save_weekly_report()

# Schedule for Monday at 9:00 AM
scheduler.add_job(scheduled_report_job, 'cron', day_of_week='mon', hour=9, minute=0)
scheduler.start()

@app.get("/")
async def root():
    return {"message": "Welcome to BobFrmMktg API"}

@app.get("/auth/adwords/login")
async def adwords_login():
    """Initiates the Google Ads OAuth2 flow."""
    auth_url = auth_service.get_authorization_url()
    return {"auth_url": auth_url}

@app.post("/auth/adwords/callback")
async def adwords_callback(request: Request):
    """Handles the OAuth2 callback from Google."""
    body = await request.json()
    code = body.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code is missing")
    return auth_service.exchange_code_for_token(code)

@app.get("/reports")
async def get_reports(token: dict = Depends(verify_token)):
    return db.get_all_reports()

@app.get("/reports/live")
async def get_live_report(
    weeks_back: int = 1,
    use_cached_raw: bool = True,
    cache_only: bool = False,
    token: dict = Depends(verify_token),
):
    """
    Return processed aggregates from local weekly store (cache-first).
    weeks_back=1 => last completed week.
    """
    if os.getenv("DISABLE_LIVE_FETCH", "false").lower() == "true":
        return {"error": "Live fetch disabled", "reason": "DISABLE_LIVE_FETCH=true"}
    return engine.get_live_report(weeks_back=weeks_back, use_cached_raw=use_cached_raw, cache_only=cache_only)

@app.get("/reports/{week_id}")
async def get_report(week_id: str, token: dict = Depends(verify_token)):
    report = db.get_report(week_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

@app.post("/reports/generate")
async def generate_report(
    background_tasks: BackgroundTasks,
    target_week_offset: int = 1,
    use_cached_raw: bool = True,
    cache_only: bool = False,
    token: dict = Depends(verify_token)
):
    """
    Manually trigger report generation for a completed week.
    target_week_offset=1 => last completed week.
    """
    background_tasks.add_task(
        engine.generate_and_save_weekly_report,
        target_week_offset,
        use_cached_raw,
        cache_only,
    )
    return {
        "message": "Report generation started in background",
        "mode": "processed_report_only",
        "target_week_offset": target_week_offset,
        "use_cached_raw": use_cached_raw,
        "cache_only": cache_only,
    }

@app.post("/reports/refresh-latest")
async def refresh_latest_report(
    use_cached_raw: bool = True,
    cache_only: bool = False,
    token: dict = Depends(verify_token),
):
    """
    Refresh/check latest completed week with storage-first behavior.
    """
    result = engine.refresh_latest_week(use_cached_raw=use_cached_raw, cache_only=cache_only)
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result)
    return result

@app.get("/reports/{week_id}/comments")
async def get_comments(week_id: str, token: dict = Depends(verify_token)):
    return db.get_comments(week_id)

@app.post("/comments")
async def add_comment(comment: dict, token: dict = Depends(verify_token)):
    # Automatically attach user info from the token
    comment["user_id"] = token.get("uid", "unknown")
    comment["user_name"] = token.get("name") or token.get("email") or "Unknown User"
    db.add_comment(comment)
    return {"status": "success"}

@app.get("/reports/{week_id}/tasks")
async def get_tasks(week_id: str, token: dict = Depends(verify_token)):
    return db.get_tasks(week_id)

@app.post("/tasks")
async def add_task(task: dict, token: dict = Depends(verify_token)):
    # Automatically attach user info from the token
    task["user_id"] = token.get("uid", "unknown")
    task["user_name"] = token.get("name") or token.get("email") or "Unknown User"
    db.add_task(task)
    return {"status": "success"}

@app.patch("/tasks/{task_id}")
async def update_task_status(task_id: str, status: dict, token: dict = Depends(verify_token)):
    db.update_task_status(task_id, status.get("is_completed"))
    return {"status": "success"}
