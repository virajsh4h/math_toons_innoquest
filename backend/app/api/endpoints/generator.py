# backend/app/api/endpoints/generator.py
import uuid
import os
import json
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models.video import VideoGenerationRequest
from app.services.video_generator import create_personalized_video

# Redis client (optional). We'll lazily import to avoid hard dependency for local runs.
REDIS_URL = os.environ.get("REDIS_URL")  # e.g. "redis://:password@hostname:6379/0"

try:
    if REDIS_URL:
        import redis  # redis-py (sync)
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    else:
        redis_client = None
except Exception as e:
    # If redis import fails, keep client None to fall back to in-memory cache
    print(f"[generator] Could not create redis client: {e}")
    redis_client = None

# Simple in-memory cache for local/dev fallback (not shared across processes)
TASK_CACHE: Dict[str, Any] = {}

router = APIRouter()

def _redis_set(task_id: str, payload: dict, expire_seconds: Optional[int] = None):
    if redis_client:
        key = f"task:{task_id}"
        redis_client.set(key, json.dumps(payload))
        if expire_seconds:
            redis_client.expire(key, expire_seconds)
    else:
        TASK_CACHE[task_id] = payload

def _redis_get(task_id: str) -> Optional[dict]:
    if redis_client:
        key = f"task:{task_id}"
        raw = redis_client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None
    else:
        return TASK_CACHE.get(task_id)

async def run_video_generation_pipeline(task_id: str, request: VideoGenerationRequest):
    """
    Async background function that runs the async generator and updates persistent store.
    FastAPI's BackgroundTasks will await async callables as background tasks.
    """
    print(f"--- Background task started (task_id={task_id}) ---")
    _redis_set(task_id, {"status": "IN_PROGRESS", "message": "Video generation started..."}, expire_seconds=3600)

    try:
        # Await the async generator instead of using asyncio.run
        final_video_url = await create_personalized_video(request)

        if final_video_url and "R2 Upload Successful: Missing" not in final_video_url:
            print(f"--- Background task finished successfully. Final video at: {final_video_url} ---")
            _redis_set(task_id, {"status": "COMPLETE", "url": final_video_url, "message": "Video is ready."}, expire_seconds=86400)
        else:
            print("--- Background task finished with an error. ---")
            _redis_set(task_id, {"status": "FAILED", "message": final_video_url or "A critical error occurred."}, expire_seconds=3600)

    except Exception as e:
        print(f"--- Background task failed with an unhandled exception: {e} ---")
        _redis_set(task_id, {"status": "FAILED", "message": f"An unhandled exception occurred: {e}"}, expire_seconds=3600)


@router.post("/generate-video", status_code=202)
def generate_video(request: VideoGenerationRequest, background_tasks: BackgroundTasks):
    """
    Accepts a video generation request and starts the process in the background.
    """
    task_id = uuid.uuid4().hex
    print(f"Received request for {request.student_name}. Adding to background tasks with ID: {task_id}")

    # initialize in store
    _redis_set(task_id, {"status": "ACCEPTED", "message": "Task accepted."}, expire_seconds=3600)

    # schedule background task (FastAPI will await async functions)
    background_tasks.add_task(run_video_generation_pipeline, task_id, request)

    # include Location header? Can't set headers from here easily in simple return; return endpoint and task_id.
    return {
        "message": "Video generation process has been accepted and started in the background. Use the task_id to poll for the final video URL.",
        "task_id": task_id,
        "details": request.dict()
    }


@router.get("/check-status/{task_id}")
def check_status(task_id: str):
    """
    Polls the status of a background video generation task.
    """
    status_info = _redis_get(task_id)

    if not status_info:
        raise HTTPException(status_code=404, detail="Task ID not found.")

    # If complete return canonical small payload
    if status_info.get("status") == "COMPLETE":
        return {"status": "COMPLETE", "url": status_info["url"]}

    # Otherwise return whatever we have (IN_PROGRESS/FAILED/ACCEPTED)
    return status_info
