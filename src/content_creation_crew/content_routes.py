"""
Content generation API routes (v1)
Jobs-first persistence with SSE streaming support
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, BackgroundTasks
from fastapi import Request as FastAPIRequest
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, DisconnectionError
import psycopg2
import psycopg2.extensions
from pydantic import BaseModel, Field
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
import json
import asyncio
import logging
import time
import sys

from .database import User, get_db, ContentJob, ContentArtifact, JobStatus
from .auth import get_current_user
from .services.content_service import ContentService
from .services.plan_policy import PlanPolicy
from .services.tts_provider import get_tts_provider
from .services.storage_provider import get_storage_provider
from .services.sse_store import get_sse_store
from .services.task_registry import get_task_registry
from .schemas import PROMPT_VERSION
from .config import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/content", tags=["content"])


async def moderate_content_background(
    job_id: int,
    content: str,
    content_type: str,
    user_id: int,
    artifact_id: int
):
    """
    OPTIMIZATION (Phase 3): Background moderation task
    Runs moderation asynchronously after content is sent to frontend
    Note: Uses a new database session for thread safety
    """
    try:
        from .services.moderation_service import get_moderation_service
        from .database import get_db, ContentArtifact
        
        moderation_service = get_moderation_service()
        moderation_result = moderation_service.moderate_output(
            content,
            content_type,
            context={"job_id": job_id, "user_id": user_id}
        )
        
        sse_store = get_sse_store()
        
        if not moderation_result.passed:
            # Moderation failed - update artifact and send error
            # Use a new database session for thread safety
            db_gen = get_db()
            db = next(db_gen)
            try:
                artifact = db.query(ContentArtifact).filter(ContentArtifact.id == artifact_id).first()
                if artifact:
                    artifact.status = 'moderation_blocked'
                    db.commit()
            finally:
                db.close()
            
            sse_store.add_event(job_id, 'moderation_blocked', {
                'job_id': job_id,
                'artifact_type': content_type,
                'reason_code': moderation_result.reason_code.value if moderation_result.reason_code else None,
                'details': moderation_result.details
            })
            logger.warning(f"Job {job_id}: {content_type} content blocked by background moderation: {moderation_result.reason_code}")
        else:
            # Moderation passed - just log
            sse_store.add_event(job_id, 'moderation_passed', {
                'job_id': job_id,
                'artifact_type': content_type
            })
            logger.info(f"Job {job_id}: {content_type} content passed background moderation")
    except Exception as e:
        logger.error(f"Job {job_id}: Background moderation error: {e}", exc_info=True)


class GenerateRequest(BaseModel):
    """Request model for content generation"""
    topic: str = Field(..., description="Content topic", min_length=1, max_length=5000)
    content_types: Optional[List[str]] = Field(
        default=None,
        description="Content types to generate: blog, social, audio, video. Only one content type per request.",
        max_items=1  # Enforce single content type
    )
    content_type: Optional[str] = Field(
        default=None,
        description="Single content type to generate: blog, social, audio, video. Alternative to content_types list.",
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Optional idempotency key to prevent duplicate jobs",
        max_length=255
    )


class JobResponse(BaseModel):
    """Response model for job information"""
    id: int
    topic: str
    formats_requested: List[str]
    status: str
    idempotency_key: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    artifacts: List[dict] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Response model for job list"""
    jobs: List[JobResponse]
    total: int
    limit: int
    offset: int


@router.post(
    "/generate",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create content generation job",
    description="""
    Create a new content generation job for the specified topic and content types.
    
    The job will be created in `pending` status and processing will begin asynchronously.
    Use the returned job ID to:
    - Query job status: `GET /v1/content/jobs/{id}`
    - Stream progress: `GET /v1/content/jobs/{id}/stream`
    - List artifacts: `GET /v1/content/jobs/{id}/artifacts`
    
    **Content Types:**
    - `blog`: Blog post content
    - `social`: Social media posts
    - `audio`: Audio script/narration
    - `video`: Video script
    
    **Idempotency:**
    Provide an `idempotency_key` to prevent duplicate jobs for the same request.
    """,
    tags=["content"],
    responses={
        201: {
            "description": "Job created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 123,
                        "topic": "Introduction to AI",
                        "formats_requested": ["blog", "social"],
                        "status": "pending",
                        "idempotency_key": "abc123",
                        "created_at": "2026-01-13T10:30:00Z",
                        "started_at": None,
                        "finished_at": None,
                        "artifacts": []
                    }
                }
            }
        },
        400: {"description": "Invalid request"},
        403: {"description": "Plan limit exceeded or content type not available"},
        429: {"description": "Rate limit exceeded"}
    }
)
async def create_generation_job(
    request: GenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new content generation job
    
    Returns the job ID which can be used to:
    - Query job status: GET /v1/content/jobs/{id}
    - Stream progress: GET /v1/content/jobs/{id}/stream
    """
    if not request.topic or not request.topic.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Topic is required"
        )
    
    topic = request.topic.strip()
    logger.info(f"Received job creation request for topic: {topic} from user {current_user.id}")
    
    # Initialize services
    content_service = ContentService(db, current_user)
    policy = PlanPolicy(db, current_user)
    plan = policy.get_plan()
    
    # Step 1: Prompt safety check (prevent injection attacks)
    from .services.prompt_safety_service import get_prompt_safety_service
    
    safety_service = get_prompt_safety_service()
    sanitized_topic, is_safe, safety_reason, safety_details = safety_service.sanitize_input(
        topic,
        max_length=5000  # 5000 chars for topic
    )
    
    if not is_safe:
        from .exceptions import ErrorResponse
        from .logging_config import get_request_id
        
        logger.warning(f"Prompt safety check failed for user {current_user.id}: {safety_reason}")
        
        error_response = ErrorResponse.create(
            message=safety_details or "Input was blocked by safety filters",
            code="INPUT_BLOCKED",
            status_code=status.HTTP_400_BAD_REQUEST,
            request_id=get_request_id(),
            details={
                "reason": safety_reason.value if safety_reason else "unknown",
            }
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response
        )
    
    # Use sanitized topic for generation
    topic = sanitized_topic
    
    # Step 2: Moderate input (after sanitization)
    if config.ENABLE_CONTENT_MODERATION:
        from .services.moderation_service import get_moderation_service
        moderation_service = get_moderation_service()
        moderation_result = moderation_service.moderate_input(
            topic,
            context={"user_id": current_user.id, "plan": plan}
        )
        
        if not moderation_result.passed:
            from .exceptions import ErrorResponse
            from .logging_config import get_request_id
            
            error_response = ErrorResponse.create(
                message=f"Content moderation failed: {moderation_result.reason_code.value if moderation_result.reason_code else 'unknown'}",
                code="CONTENT_BLOCKED",
                status_code=status.HTTP_403_FORBIDDEN,
                request_id=get_request_id(),
                details={
                    "reason_code": moderation_result.reason_code.value if moderation_result.reason_code else None,
                    **moderation_result.details
                }
            )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_response
            )
    
    # Determine content type - enforce single content type only
    # Support both content_type (single string) and content_types (list) for backward compatibility
    requested_content_type = None
    if request.content_type:
        requested_content_type = request.content_type
    elif request.content_types and len(request.content_types) > 0:
        # If multiple content types provided, use only the first one
        if len(request.content_types) > 1:
            logger.warning(f"User {current_user.id} requested multiple content types {request.content_types}, using only first: {request.content_types[0]}")
        requested_content_type = request.content_types[0]
    
    # Default to 'blog' if no content type specified
    if not requested_content_type:
        requested_content_type = 'blog'
        logger.info(f"User {current_user.id} did not specify content type, defaulting to 'blog'")
    
    # Validate content type
    valid_content_types = [requested_content_type]  # Single content type only
    
    # Validate content type access
    if not policy.check_content_type_access(requested_content_type):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "content_type_not_available",
                "message": f"{requested_content_type.capitalize()} content is not available on your current plan ({plan}).",
                "content_type": requested_content_type,
                "plan": plan
            }
        )
    
    # Enforce monthly limit for the single content type
    try:
        policy.enforce_monthly_limit(requested_content_type)
    except HTTPException:
        raise
    
    # Notify user about the content type being generated
    content_type_display = {
        'blog': 'Blog Post',
        'social': 'Social Media Content',
        'audio': 'Audio Content',
        'video': 'Video Content'
    }.get(requested_content_type, requested_content_type.capitalize())
    
    logger.info(f"User {current_user.id} generating {content_type_display} for topic: {topic}")
    
    # Create job with single content type
    try:
        job = content_service.create_job(
            topic=topic,
            content_types=valid_content_types,  # Single content type: [requested_content_type]
            idempotency_key=request.idempotency_key
        )
    except HTTPException as e:
        raise e
    
    # Track job creation metric
    try:
        from .services.metrics import increment_counter
        increment_counter("jobs_total", labels={"content_types": ",".join(valid_content_types), "plan": plan})
    except ImportError:
        pass
    
    # Start generation asynchronously with proper error handling
    # Use asyncio.create_task() but wrap it to catch and log errors
    async def run_with_error_handling():
        """Wrapper to ensure async task errors are logged and handled"""
        try:
            logger.info(f"[ASYNC_TASK] Starting async generation task for job {job.id}")
            # Force immediate output for Railway
            print(f"[RAILWAY_DEBUG] Async task started for job {job.id}", file=sys.stdout, flush=True)
            sys.stdout.flush()
            sys.stderr.flush()
            await run_generation_async(job.id, topic, valid_content_types, plan, current_user.id)
            logger.info(f"[ASYNC_TASK] Async generation task completed successfully for job {job.id}")
            sys.stdout.flush()
            sys.stderr.flush()
        except asyncio.CancelledError:
            logger.info(f"[ASYNC_TASK] Task for job {job.id} was cancelled")
            # Update job status to cancelled
            try:
                from .services.content_service import ContentService
                from .database import SessionLocal
                cancel_session = SessionLocal()
                try:
                    cancel_user = cancel_session.query(User).filter(User.id == current_user.id).first()
                    if cancel_user:
                        cancel_content_service = ContentService(cancel_session, cancel_user)
                        cancel_content_service.update_job_status(
                            job.id,
                            JobStatus.CANCELLED.value,
                            finished_at=datetime.utcnow()
                        )
                        cancel_session.commit()
                        # Send cancellation event
                        from .services.sse_store import get_sse_store
                        cancel_sse_store = get_sse_store()
                        cancel_sse_store.add_event(job.id, 'cancelled', {
                            'job_id': job.id,
                            'message': 'Job cancelled by user',
                            'cancelled_at': datetime.utcnow().isoformat()
                        })
                        logger.info(f"[ASYNC_TASK] Updated job {job.id} status to CANCELLED")
                except Exception:
                    cancel_session.rollback()
                    raise
                finally:
                    cancel_session.close()
            except Exception as cancel_error:
                logger.error(f"[ASYNC_TASK] Failed to update job status after cancellation: {cancel_error}", exc_info=True)
            raise  # Re-raise CancelledError
        except Exception as e:
            error_type = type(e).__name__
            error_msg_raw = str(e) if str(e) else f"{error_type} occurred"
            
            # Build helpful error message
            if 'OPENAI_API_KEY' in error_msg_raw or 'api key' in error_msg_raw.lower():
                error_msg = f"LLM configuration error: {error_msg_raw}"
                hint = "Set OPENAI_API_KEY in Railway backend service variables (not frontend .env)"
            elif 'authentication' in error_msg_raw.lower() or 'unauthorized' in error_msg_raw.lower():
                error_msg = f"Authentication error: {error_msg_raw}"
                hint = "Verify OPENAI_API_KEY is correct and has proper permissions"
            else:
                error_msg = f'Content generation failed: {error_msg_raw}'
                hint = "Check backend logs for detailed error information"
            
            logger.error(f"[ASYNC_TASK] Async generation task FAILED for job {job.id}: {error_type}: {error_msg}", exc_info=True)
            sys.stdout.flush()
            sys.stderr.flush()
            
            # Try to update job status to failed
            try:
                from .services.content_service import ContentService
                from .database import SessionLocal
                error_session = SessionLocal()
                try:
                    error_user = error_session.query(User).filter(User.id == current_user.id).first()
                    if error_user:
                        error_content_service = ContentService(error_session, error_user)
                        error_content_service.update_job_status(
                            job.id,
                            JobStatus.FAILED.value,
                            finished_at=datetime.utcnow()
                        )
                        error_session.commit()
                        # Send error event to SSE store with hint
                        from .services.sse_store import get_sse_store
                        sse_store = get_sse_store()
                        sse_store.add_event(job.id, 'error', {
                            'job_id': job.id,
                            'message': error_msg,
                            'error_type': error_type,
                            'hint': hint
                        })
                        logger.info(f"[ASYNC_TASK] Updated job {job.id} status to FAILED and sent error event with hint")
                        sys.stdout.flush()
                        sys.stderr.flush()
                except Exception:
                    error_session.rollback()
                    raise
                finally:
                    error_session.close()
            except Exception as update_error:
                logger.error(f"[ASYNC_TASK] Failed to update job status after error: {update_error}", exc_info=True)
                sys.stdout.flush()
                sys.stderr.flush()
    
    # Create the task with error handling
    # Add done callback to log completion/failure
    task = asyncio.create_task(run_with_error_handling())
    
    # Register task in registry for cancellation support
    task_registry = get_task_registry()
    asyncio.create_task(task_registry.register(job.id, task))
    
    def task_done_callback(fut):
        """Callback to log task completion or failure and unregister task"""
        try:
            fut.result()  # This will raise if the task failed
            logger.info(f"[ASYNC_TASK] Task for job {job.id} completed successfully")
            sys.stdout.flush()
            sys.stderr.flush()
        except asyncio.CancelledError:
            logger.info(f"[ASYNC_TASK] Task for job {job.id} was cancelled")
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception as e:
            # Error already logged in run_with_error_handling, but log here too for visibility
            logger.error(f"[ASYNC_TASK] Task for job {job.id} failed in callback: {type(e).__name__}: {str(e)}")
            sys.stdout.flush()
            sys.stderr.flush()
        finally:
            # Unregister task when done
            asyncio.create_task(task_registry.unregister(job.id))
    
    task.add_done_callback(task_done_callback)
    
    # Verify task is running and log details
    logger.info(f"[JOB_CREATE] Created async task for job {job.id}, task_id={id(task)}, topic='{topic[:50]}...'")
    sys.stdout.flush()
    sys.stderr.flush()
    if task.done():
        logger.warning(f"[JOB_CREATE] Task for job {job.id} completed immediately (unexpected)")
        sys.stdout.flush()
        sys.stderr.flush()
        try:
            task.result()  # Check if it completed with an error
        except Exception as e:
            logger.error(f"[JOB_CREATE] Task for job {job.id} failed immediately: {type(e).__name__}: {str(e)}")
            sys.stdout.flush()
            sys.stderr.flush()
    else:
        logger.info(f"[JOB_CREATE] Task for job {job.id} is running asynchronously")
        sys.stdout.flush()
        sys.stderr.flush()
    
    # Return job info
    return _job_to_response(job)


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=Dict[str, Any],
    summary="Cancel a running job",
    description="""
    Cancel a running content generation job.
    
    This will:
    - Stop the async task (if still running)
    - Update job status to CANCELLED
    - Send cancellation event via SSE
    - Prevent further API token usage
    
    Returns job status after cancellation.
    """,
    tags=["content"]
)
async def cancel_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a running job
    
    Args:
        job_id: Job ID to cancel
    
    Returns:
        Job status after cancellation
    """
    from .services.content_service import ContentService
    
    content_service = ContentService(db, current_user)
    job = content_service.get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Check if user owns this job
    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to cancel this job"
        )
    
    # Check if job is already completed/failed/cancelled
    if job.status in [JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value]:
        logger.info(f"Job {job_id} already in final state: {job.status}")
        return {
            "job_id": job_id,
            "status": job.status,
            "message": f"Job already in final state: {job.status}"
        }
    
    # Try to cancel the async task
    task_registry = get_task_registry()
    task_cancelled = await task_registry.cancel(job_id)
    
    # Update job status to cancelled
    content_service.update_job_status(
        job_id,
        JobStatus.CANCELLED.value,
        finished_at=datetime.utcnow()
    )
    
    # Send cancellation event via SSE
    sse_store = get_sse_store()
    sse_store.add_event(job_id, 'cancelled', {
        'job_id': job_id,
        'message': 'Job cancelled by user',
        'cancelled_at': datetime.utcnow().isoformat()
    })
    
    logger.info(f"Job {job_id} cancelled by user {current_user.id}. Task cancelled: {task_cancelled}")
    
    return {
        "job_id": job_id,
        "status": JobStatus.CANCELLED.value,
        "message": "Job cancelled successfully",
        "task_cancelled": task_cancelled
    }


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Get job details",
    description="Retrieve details of a specific content generation job including status and artifacts.",
    tags=["content"]
)
async def get_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get job details by ID"""
    content_service = ContentService(db, current_user)
    job = content_service.get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return _job_to_response(job)


@router.get(
    "/jobs",
    response_model=JobListResponse,
    summary="List jobs",
    description="List all content generation jobs for the authenticated user. Supports filtering by status and pagination.",
    tags=["content"]
)
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's content generation jobs"""
    content_service = ContentService(db, current_user)
    jobs = content_service.list_jobs(status=status, limit=limit, offset=offset)
    
    # Get total count
    total = db.query(ContentJob).filter(
        ContentJob.user_id == current_user.id
    ).count()
    
    return JobListResponse(
        jobs=[_job_to_response(job) for job in jobs],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get(
    "/jobs/{job_id}/stream",
    summary="Stream job progress (SSE)",
    description="""
    Stream job progress via Server-Sent Events (SSE).
    
    **Event Types:**
    - `job_started`: Job has started processing
    - `agent_progress`: Progress update from an agent
    - `artifact_ready`: An artifact has been generated
    - `tts_started`: TTS generation started
    - `tts_progress`: TTS generation progress
    - `tts_completed`: TTS generation completed
    - `video_render_started`: Video rendering started
    - `scene_started`: Scene rendering started
    - `scene_completed`: Scene rendering completed
    - `complete`: Job completed successfully
    - `error`: Job failed
    
    **Reconnection:**
    Supports `Last-Event-ID` header for reconnection and event replay.
    """,
    tags=["content"]
)
async def stream_job_progress(
    job_id: int,
    request: FastAPIRequest,
    last_event_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Stream job progress via Server-Sent Events (SSE)
    
    Supports Last-Event-ID header for reconnection and event replay.
    
    Events:
    - job_started: Job has started processing
    - agent_progress: Progress update from an agent
    - artifact_ready: An artifact has been generated
    - complete: Job completed successfully
    - error: Job failed
    
    Args:
        job_id: Job ID to stream
        request: FastAPI request object (for Last-Event-ID header)
    """
    from fastapi.responses import StreamingResponse
    from content_creation_crew.services.sse_store import get_sse_store
    from .database import SessionLocal
    
    # Get initial job with a short-lived session
    initial_session = SessionLocal()
    try:
        content_service = ContentService(initial_session, current_user)
        job = content_service.get_job(job_id)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
    finally:
        initial_session.close()
    
    # Get SSE event store
    sse_store = get_sse_store()
    
    # Import flush utilities for immediate data delivery
    from content_creation_crew.streaming_utils import flush_buffers
    
    # Log stream start
    client_host = request.client.host if request.client else 'unknown'
    logger.info(f"[STREAM_START] Starting SSE stream for job {job_id}, client={client_host}, user_id={current_user.id}")
    
    # Get Last-Event-ID from header (use query param if header not available)
    last_event_id = request.headers.get("Last-Event-ID") or last_event_id
    last_event_id_int = None
    if last_event_id:
        try:
            last_event_id_int = int(last_event_id)
        except ValueError:
            pass
    
    async def generate_stream():
        """Generate SSE stream for job progress"""
        nonlocal job  # Ensure we can modify the outer scope 'job' variable
        logger.info(f"[STREAM_GENERATOR] Generator started for job {job_id}")
        try:
            # Replay missed events if last_event_id provided
            if last_event_id_int:
                missed_events = sse_store.get_events_since(job_id, last_event_id_int)
                for event in missed_events:
                    yield f"id: {event['id']}\n"
                    yield f"event: {event['type']}\n"
                    yield f"data: {json.dumps(event['data'])}\n\n"
                    flush_buffers()  # Flush after each event for immediate delivery
            
            # Send initial job status if not already sent
            last_sent_event_id = last_event_id_int if last_event_id_int else 0
            if not last_event_id_int:
                event_data = {'type': 'job_started', 'job_id': job_id, 'status': job.status}
                event_id = sse_store.add_event(job_id, 'job_started', event_data)
                yield f"id: {event_id}\n"
                yield f"event: job_started\n"
                yield f"data: {json.dumps(event_data)}\n\n"
                flush_buffers()  # Critical: Flush immediately after initial event
                logger.info(f"[STREAM_GENERATOR] Sent initial job_started event for job {job_id}, status={job.status}")
                last_sent_event_id = event_id
                
                # If job is already failed, check for error events and send them
                if job.status == JobStatus.FAILED.value:
                    logger.warning(f"[STREAM_GENERATOR] Job {job_id} is already failed, checking for error events")
                    # Get recent error events from SSE store
                    recent_events = sse_store.get_events_since(job_id, 0)  # Get all events
                    error_events = [e for e in recent_events if e.get('type') == 'error']
                    if error_events:
                        # Send the most recent error event
                        latest_error = error_events[-1]
                        error_data = latest_error.get('data', {})
                        if error_data:
                            yield f"id: {latest_error['id']}\n"
                            yield f"event: error\n"
                            yield f"data: {json.dumps(error_data)}\n\n"
                            flush_buffers()
                            logger.info(f"[STREAM_GENERATOR] Sent error event for failed job {job_id}: {error_data.get('message', 'Unknown error')}")
                    else:
                        # No error event found, send a generic error
                        error_data = {
                            'type': 'error',
                            'job_id': job_id,
                            'message': 'Job failed but no error details available. Check backend logs for details.',
                            'status': 'failed'
                        }
                        event_id = sse_store.add_event(job_id, 'error', error_data)
                        yield f"id: {event_id}\n"
                        yield f"event: error\n"
                        yield f"data: {json.dumps(error_data)}\n\n"
                        flush_buffers()
                        logger.warning(f"[STREAM_GENERATOR] Job {job_id} failed but no error event found, sent generic error")
            
            # Poll for job updates
            last_status = job.status
            last_artifact_count = 0
            last_keepalive_time = time.time()
            keepalive_interval = 5.0  # Send keep-alive every 5 seconds to prevent timeout
            poll_count = 0
            stream_start_time = time.time()
            consecutive_failures = 0  # Track consecutive query failures
            max_consecutive_failures = 10  # Only break stream after 10 consecutive failures
            
            logger.info(f"[STREAM_POLL] Starting polling loop for job {job_id}, initial status={job.status}")
            
            while True:
                try:
                    poll_count += 1
                    # Get fresh job from database using a short-lived session with retry logic
                    fresh_job = None
                    max_retries = 3
                    retry_delay = 0.5  # Start with 0.5 seconds
                    query_failed = False
                    
                    for retry_attempt in range(max_retries):
                        poll_session = SessionLocal()
                        try:
                            fresh_job = poll_session.query(ContentJob).filter(ContentJob.id == job_id).first()
                            if fresh_job:
                                job = fresh_job
                                consecutive_failures = 0  # Reset failure counter on success
                                break  # Success - exit retry loop
                            else:
                                # Job not found - this is not a connection error, exit retry loop
                                break
                        except (OperationalError, DisconnectionError) as db_error:
                            # Connection error - retry with exponential backoff
                            # Also check if it's a psycopg2 connection error
                            error_msg = str(db_error)
                            is_connection_error = (
                                isinstance(db_error, (OperationalError, DisconnectionError)) or
                                'connection' in error_msg.lower() or
                                'SSL' in error_msg or
                                'closed' in error_msg.lower() or
                                'reset' in error_msg.lower() or
                                'EOF' in error_msg or
                                (hasattr(db_error, 'orig') and isinstance(db_error.orig, (psycopg2.OperationalError, psycopg2.InterfaceError)))
                            )
                            
                            if is_connection_error:
                                logger.warning(f"[STREAM_RETRY] Job {job_id}: Database connection error on attempt {retry_attempt + 1}/{max_retries}: {error_msg}")
                            
                            # Close the broken session
                            try:
                                poll_session.close()
                            except:
                                pass
                            
                            if retry_attempt < max_retries - 1:
                                # Wait before retrying (exponential backoff)
                                await asyncio.sleep(retry_delay)
                                retry_delay *= 2  # Double the delay for next retry
                                continue  # Retry
                            else:
                                # All retries exhausted - log warning but continue polling
                                query_failed = True
                                consecutive_failures += 1
                                logger.warning(f"[STREAM_WARN] Job {job_id}: Database connection failed after {max_retries} retries (consecutive failures: {consecutive_failures}/{max_consecutive_failures}): {error_msg}")
                                
                                # Send warning event (not error) if this is the first failure or every 5 failures
                                if consecutive_failures == 1 or consecutive_failures % 5 == 0:
                                    warning_data = {
                                        'type': 'warning',
                                        'job_id': job_id,
                                        'message': f'Temporary database connection issue (attempt {consecutive_failures}). Retrying...',
                                        'error_type': 'OperationalError',
                                        'hint': 'The job may still be running. We will continue checking its status.'
                                    }
                                    event_id = sse_store.add_event(job_id, 'warning', warning_data)
                                    yield f"id: {event_id}\n"
                                    yield f"event: warning\n"
                                    yield f"data: {json.dumps(warning_data)}\n\n"
                                    flush_buffers()
                                
                                # Only break stream if too many consecutive failures
                                if consecutive_failures >= max_consecutive_failures:
                                    logger.error(f"[STREAM_ERROR] Job {job_id}: Too many consecutive database failures ({consecutive_failures}), giving up")
                                    error_data = {
                                        'type': 'error',
                                        'job_id': job_id,
                                        'message': f'Database connection lost after {consecutive_failures} attempts. The job may have completed but we cannot verify its status.',
                                        'error_type': 'OperationalError',
                                        'hint': 'Please check the job status manually or try again later.'
                                    }
                                    event_id = sse_store.add_event(job_id, 'error', error_data)
                                    yield f"id: {event_id}\n"
                                    yield f"event: error\n"
                                    yield f"data: {json.dumps(error_data)}\n\n"
                                    flush_buffers()
                                    break  # Exit retry loop and while loop
                                
                                # Wait longer before next poll attempt
                                await asyncio.sleep(2.0)  # Wait 2 seconds before next poll
                                break  # Exit retry loop, continue while loop
                        except Exception as db_error:
                            # Check if this is actually a connection error that wasn't caught above
                            error_msg = str(db_error)
                            is_connection_error = (
                                isinstance(db_error, (OperationalError, DisconnectionError)) or
                                'connection' in error_msg.lower() or
                                'SSL' in error_msg or
                                'closed' in error_msg.lower() or
                                'reset' in error_msg.lower() or
                                'EOF' in error_msg or
                                'psycopg2' in error_msg.lower() or
                                (hasattr(db_error, 'orig') and isinstance(db_error.orig, (psycopg2.OperationalError, psycopg2.InterfaceError)))
                            )
                            
                            if is_connection_error:
                                # Treat as connection error - retry logic
                                query_failed = True
                                consecutive_failures += 1
                                logger.warning(f"[STREAM_RETRY] Job {job_id}: Database connection error (caught as Exception) on attempt {retry_attempt + 1}/{max_retries} (consecutive failures: {consecutive_failures}/{max_consecutive_failures}): {error_msg}")
                                
                                try:
                                    poll_session.close()
                                except:
                                    pass
                                
                                if retry_attempt < max_retries - 1:
                                    await asyncio.sleep(retry_delay)
                                    retry_delay *= 2
                                    continue  # Retry
                                else:
                                    # All retries exhausted - continue polling
                                    if consecutive_failures == 1 or consecutive_failures % 5 == 0:
                                        warning_data = {
                                            'type': 'warning',
                                            'job_id': job_id,
                                            'message': f'Temporary database connection issue (attempt {consecutive_failures}). Retrying...',
                                            'error_type': 'ConnectionError',
                                            'hint': 'The job may still be running. We will continue checking its status.'
                                        }
                                        event_id = sse_store.add_event(job_id, 'warning', warning_data)
                                        yield f"id: {event_id}\n"
                                        yield f"event: warning\n"
                                        yield f"data: {json.dumps(warning_data)}\n\n"
                                        flush_buffers()
                                    
                                    if consecutive_failures >= max_consecutive_failures:
                                        logger.error(f"[STREAM_ERROR] Job {job_id}: Too many consecutive database failures ({consecutive_failures}), giving up")
                                        error_data = {
                                            'type': 'error',
                                            'job_id': job_id,
                                            'message': f'Database connection lost after {consecutive_failures} attempts. The job may have completed but we cannot verify its status.',
                                            'error_type': 'ConnectionError',
                                            'hint': 'Please check the job status manually or try again later.'
                                        }
                                        event_id = sse_store.add_event(job_id, 'error', error_data)
                                        yield f"id: {event_id}\n"
                                        yield f"event: error\n"
                                        yield f"data: {json.dumps(error_data)}\n\n"
                                        flush_buffers()
                                        break
                                    
                                    await asyncio.sleep(2.0)
                                    break  # Exit retry loop, continue while loop
                            else:
                                # Non-connection error - log but continue
                                query_failed = True
                                consecutive_failures += 1
                                logger.error(f"[STREAM_ERROR] Job {job_id}: Database query failed: {type(db_error).__name__}: {str(db_error)}", exc_info=True)
                                try:
                                    poll_session.close()
                                except:
                                    pass
                                
                                # Only break on non-connection errors if job not found or too many failures
                                if consecutive_failures >= max_consecutive_failures:
                                    error_data = {'type': 'error', 'job_id': job_id, 'message': f'Database error after {consecutive_failures} attempts: {str(db_error)}'}
                                    event_id = sse_store.add_event(job_id, 'error', error_data)
                                    yield f"id: {event_id}\n"
                                    yield f"event: error\n"
                                    yield f"data: {json.dumps(error_data)}\n\n"
                                    flush_buffers()
                                    break  # Exit retry loop
                                else:
                                    await asyncio.sleep(2.0)  # Wait before next poll
                                    break  # Exit retry loop, continue while loop
                        finally:
                            # Ensure session is closed if not already closed
                            try:
                                poll_session.close()
                            except:
                                pass
                    
                    # If query failed, use last known job status and continue polling
                    if query_failed and not fresh_job:
                        # Use last known job status - don't break the stream
                        logger.debug(f"[STREAM_CONTINUE] Job {job_id}: Using last known status={last_status}, continuing to poll...")
                        # Wait a bit longer before next poll attempt
                        await asyncio.sleep(2.0)
                        continue
                    
                    # Check if job was found after retries
                    if not fresh_job:
                        # Job not found - this could be a real issue or temporary connection problem
                        consecutive_failures += 1
                        if consecutive_failures >= max_consecutive_failures:
                            error_data = {'type': 'error', 'job_id': job_id, 'message': 'Job not found in database after multiple attempts'}
                            event_id = sse_store.add_event(job_id, 'error', error_data)
                            yield f"id: {event_id}\n"
                            yield f"event: error\n"
                            yield f"data: {json.dumps(error_data)}\n\n"
                            flush_buffers()
                            logger.error(f"[STREAM_ERROR] Job {job_id}: Job not found in database after {consecutive_failures} attempts")
                            break
                        else:
                            logger.warning(f"[STREAM_WARN] Job {job_id}: Job not found (attempt {consecutive_failures}/{max_consecutive_failures}), continuing to poll...")
                            await asyncio.sleep(2.0)
                            continue
                    
                    # Log every 20 polls (every 10 seconds) to track progress
                    if poll_count % 20 == 0:
                        elapsed = time.time() - stream_start_time
                        artifact_count = -1
                        # Retry logic for artifact count query
                        for count_retry in range(2):  # 2 retries for artifact count
                            count_session = SessionLocal()
                            try:
                                artifact_count = len(count_session.query(ContentArtifact).filter(ContentArtifact.job_id == job_id).all())
                                break  # Success - exit retry loop
                            except (OperationalError, DisconnectionError) as count_error:
                                logger.warning(f"[STREAM_RETRY] Job {job_id}: Artifact count query failed on attempt {count_retry + 1}/2: {count_error}")
                                try:
                                    count_session.close()
                                except:
                                    pass
                                if count_retry < 1:
                                    await asyncio.sleep(0.5)  # Brief delay before retry
                                    continue
                                # If retries exhausted, just use -1 (unknown count)
                                artifact_count = -1
                            except Exception:
                                # Non-connection error - just use -1
                                artifact_count = -1
                            finally:
                                try:
                                    count_session.close()
                                except:
                                    pass
                        logger.info(f"[STREAM_POLL] Job {job_id}: Poll #{poll_count}, status={job.status}, elapsed={elapsed:.1f}s, artifacts={artifact_count}")
                    
                    # Send keep-alive comment if enough time has passed (prevents undici body timeout)
                    current_time = time.time()
                    if current_time - last_keepalive_time >= keepalive_interval:
                        yield ": keep-alive\n\n"
                        flush_buffers()  # Flush keep-alive for immediate delivery
                        last_keepalive_time = current_time
                    
                    # Check for status changes
                    if job.status != last_status:
                        event_type = 'complete' if job.status == JobStatus.COMPLETED.value else 'error' if job.status == JobStatus.FAILED.value else 'status_update'
                        
                        # If job failed, get the actual error details from SSE store
                        if job.status == JobStatus.FAILED.value:
                            # Get recent error events from SSE store
                            recent_events = sse_store.get_events_since(job_id, 0)  # Get all events
                            error_events = [e for e in recent_events if e.get('type') == 'error']
                            if error_events:
                                # Use the most recent error event's data
                                latest_error = error_events[-1]
                                event_data = latest_error.get('data', {})
                                # Ensure type and job_id are set
                                event_data['type'] = 'error'
                                event_data['job_id'] = job_id
                                event_data['status'] = job.status
                                event_id = latest_error.get('id')
                                if not event_id:
                                    event_id = sse_store.add_event(job_id, 'error', event_data)
                            else:
                                # No error event found, create generic one
                                event_data = {'type': 'error', 'job_id': job_id, 'status': job.status, 'message': 'Job failed but no error details available. Check backend logs for details.'}
                                event_id = sse_store.add_event(job_id, 'error', event_data)
                        else:
                            # For other status changes, create standard event
                            event_data = {'type': event_type, 'job_id': job_id, 'status': job.status}
                            event_id = sse_store.add_event(job_id, event_type, event_data)
                        
                        yield f"id: {event_id}\n"
                        yield f"event: {event_type}\n"
                        yield f"data: {json.dumps(event_data)}\n\n"
                        flush_buffers()  # Flush status change events immediately
                        last_sent_event_id = max(last_sent_event_id, event_id)  # Update last sent event ID
                        last_status = job.status
                        
                        # If completed or failed, send final event and exit
                        if job.status in [JobStatus.COMPLETED.value, JobStatus.FAILED.value]:
                            elapsed = time.time() - stream_start_time
                            artifact_count = -1
                            # Retry logic for final artifact count query
                            for final_retry in range(2):  # 2 retries
                                final_session = SessionLocal()
                                try:
                                    artifact_count = len(final_session.query(ContentArtifact).filter(ContentArtifact.job_id == job_id).all())
                                    break  # Success
                                except (OperationalError, DisconnectionError) as final_error:
                                    logger.warning(f"[STREAM_RETRY] Job {job_id}: Final artifact count query failed on attempt {final_retry + 1}/2: {final_error}")
                                    try:
                                        final_session.close()
                                    except:
                                        pass
                                    if final_retry < 1:
                                        await asyncio.sleep(0.5)
                                        continue
                                    artifact_count = -1
                                except Exception:
                                    artifact_count = -1
                                finally:
                                    try:
                                        final_session.close()
                                    except:
                                        pass
                            logger.info(f"[STREAM_COMPLETE] Job {job_id}: Status changed to {job.status} after {elapsed:.1f}s, total polls={poll_count}, artifacts={artifact_count}")
                            
                            # Send artifacts if completed
                            if job.status == JobStatus.COMPLETED.value:
                                artifacts = []
                                # Retry logic for artifacts query
                                for artifacts_retry in range(3):  # 3 retries for artifacts (more important)
                                    artifacts_session = SessionLocal()
                                    try:
                                        artifacts = artifacts_session.query(ContentArtifact).filter(
                                            ContentArtifact.job_id == job_id
                                        ).all()
                                        break  # Success
                                    except (OperationalError, DisconnectionError) as artifacts_error:
                                        logger.warning(f"[STREAM_RETRY] Job {job_id}: Artifacts query failed on attempt {artifacts_retry + 1}/3: {artifacts_error}")
                                        try:
                                            artifacts_session.close()
                                        except:
                                            pass
                                        if artifacts_retry < 2:
                                            await asyncio.sleep(0.5 * (artifacts_retry + 1))  # Increasing delay
                                            continue
                                        # If all retries fail, use empty list
                                        artifacts = []
                                    except Exception as artifacts_error:
                                        logger.error(f"[STREAM_ERROR] Job {job_id}: Non-connection error querying artifacts: {artifacts_error}")
                                        artifacts = []
                                    finally:
                                        try:
                                            artifacts_session.close()
                                        except:
                                            pass
                                
                                # Build complete event with full content from all artifacts
                                artifact_data = {
                                    'type': 'complete',
                                    'job_id': job_id,
                                    'status': JobStatus.COMPLETED.value,
                                    'message': 'Content generation completed successfully'
                                }
                                
                                # Include full content from each artifact type
                                if artifacts:
                                    for artifact in artifacts:
                                        if artifact.content_text:
                                            if artifact.type == 'blog':
                                                artifact_data['content'] = artifact.content_text
                                            elif artifact.type == 'social':
                                                artifact_data['social_media_content'] = artifact.content_text
                                            elif artifact.type == 'audio':
                                                artifact_data['audio_content'] = artifact.content_text
                                            elif artifact.type == 'video':
                                                artifact_data['video_content'] = artifact.content_text
                                    logger.info(f"[STREAM_COMPLETE] Job {job_id}: Prepared complete event with content from {len(artifacts)} artifacts")
                                else:
                                    # Fallback: Try to get content from SSE store events that were already sent
                                    logger.warning(f"[STREAM_WARN] Job {job_id}: No artifacts found - checking SSE store for content events")
                                    try:
                                        all_events = sse_store.get_events_since(job_id, 0)
                                        content_events = [e for e in all_events if e.get('type') == 'content']
                                        for content_event in content_events:
                                            event_data = content_event.get('data', {})
                                            chunk = event_data.get('chunk', '')
                                            artifact_type = event_data.get('artifact_type', '')
                                            if chunk and artifact_type:
                                                if artifact_type == 'blog':
                                                    artifact_data['content'] = chunk
                                                elif artifact_type == 'social':
                                                    artifact_data['social_media_content'] = chunk
                                                elif artifact_type == 'audio':
                                                    artifact_data['audio_content'] = chunk
                                                elif artifact_type == 'video':
                                                    artifact_data['video_content'] = chunk
                                        
                                        if any(key in artifact_data for key in ['content', 'audio_content', 'social_media_content', 'video_content']):
                                            logger.info(f"[STREAM_COMPLETE] Job {job_id}: Found content in SSE store events, including in complete event")
                                        else:
                                            logger.warning(f"[STREAM_WARN] Job {job_id}: No content found in artifacts or SSE store - sending complete event without content")
                                    except Exception as sse_fallback_error:
                                        logger.error(f"[STREAM_ERROR] Job {job_id}: Failed to get content from SSE store: {sse_fallback_error}")
                                        logger.warning(f"[STREAM_WARN] Job {job_id}: Sending complete event without artifact content")
                                
                                # Send complete event
                                event_id = sse_store.add_event(job_id, 'complete', artifact_data)
                                
                                # Log what content is being sent in the complete event
                                content_summary = {
                                    'has_content': 'content' in artifact_data and bool(artifact_data.get('content')),
                                    'content_length': len(artifact_data.get('content', '')),
                                    'has_audio': 'audio_content' in artifact_data and bool(artifact_data.get('audio_content')),
                                    'audio_length': len(artifact_data.get('audio_content', '')),
                                    'has_social': 'social_media_content' in artifact_data and bool(artifact_data.get('social_media_content')),
                                    'has_video': 'video_content' in artifact_data and bool(artifact_data.get('video_content')),
                                }
                                logger.info(f"[STREAM_COMPLETE] Job {job_id}: Sending complete event with content: {content_summary}")
                                print(f"[RAILWAY_DEBUG] Job {job_id}: Complete event content summary: {content_summary}", file=sys.stdout, flush=True)
                                
                                yield f"id: {event_id}\n"
                                yield f"event: complete\n"
                                yield f"data: {json.dumps(artifact_data)}\n\n"
                                flush_buffers()  # Flush completion event immediately
                                last_sent_event_id = max(last_sent_event_id, event_id)  # Update last sent event ID
                                logger.info(f"[STREAM_COMPLETE] Job {job_id}: Sent complete event with {len(artifact_data)} fields")
                            break
                    
                    # Check for new artifacts - use short-lived session with retry logic
                    current_artifacts = []
                    for check_retry in range(2):  # 2 retries for artifact check
                        artifacts_check_session = SessionLocal()
                        try:
                            current_artifacts = artifacts_check_session.query(ContentArtifact).filter(
                                ContentArtifact.job_id == job_id
                            ).all()
                            break  # Success
                        except (OperationalError, DisconnectionError) as check_error:
                            logger.warning(f"[STREAM_RETRY] Job {job_id}: Artifact check query failed on attempt {check_retry + 1}/2: {check_error}")
                            try:
                                artifacts_check_session.close()
                            except:
                                pass
                            if check_retry < 1:
                                await asyncio.sleep(0.5)
                                continue
                            current_artifacts = []
                        except Exception as check_error:
                            logger.warning(f"[STREAM_WARN] Job {job_id}: Artifact check query error: {check_error}")
                            current_artifacts = []
                        finally:
                            try:
                                artifacts_check_session.close()
                            except:
                                pass
                    
                    if current_artifacts and len(current_artifacts) > last_artifact_count:
                        # New artifacts created
                        print(f"[RAILWAY_DEBUG] Job {job_id}: Detected {len(current_artifacts) - last_artifact_count} new artifact(s) in database", file=sys.stdout, flush=True)
                        new_artifacts = current_artifacts[last_artifact_count:]
                        for artifact in new_artifacts:
                            print(f"[RAILWAY_DEBUG] Job {job_id}: Processing artifact type={artifact.type}, has_content={bool(artifact.content_text)}", file=sys.stdout, flush=True)
                            # Send artifact_ready event
                            event_data = {'type': 'artifact_ready', 'job_id': job_id, 'artifact_type': artifact.type}
                            
                            # Include metadata for voiceover_audio artifacts
                            if artifact.type == 'voiceover_audio' and artifact.content_json:
                                event_data['metadata'] = artifact.content_json
                                if artifact.content_json.get('storage_key'):
                                    storage = get_storage_provider()
                                    event_data['url'] = storage.get_url(artifact.content_json['storage_key'])
                            
                            event_id = sse_store.add_event(job_id, 'artifact_ready', event_data)
                            yield f"id: {event_id}\n"
                            yield f"event: artifact_ready\n"
                            yield f"data: {json.dumps(event_data)}\n\n"
                            flush_buffers()  # Flush artifact events immediately
                            last_sent_event_id = max(last_sent_event_id, event_id)  # Update last sent event ID
                            
                            # Send content event if artifact has text content
                            if artifact.content_text and artifact.type in ['blog', 'social', 'audio', 'video']:
                                content_field = {
                                    'blog': 'content',
                                    'social': 'social_media_content',
                                    'audio': 'audio_content',
                                    'video': 'video_content'
                                }.get(artifact.type, 'content')
                                
                                content_event_data = {
                                    'type': 'content',
                                    'job_id': job_id,
                                    'chunk': artifact.content_text,  # Send full content
                                    'progress': 100,  # Content is complete
                                    'artifact_type': artifact.type,
                                    'content_field': content_field
                                }
                                content_event_id = sse_store.add_event(job_id, 'content', content_event_data)
                                print(f"[RAILWAY_DEBUG] Job {job_id}: Yielding content event for {artifact.type}, length={len(artifact.content_text)}", file=sys.stdout, flush=True)
                                yield f"id: {content_event_id}\n"
                                yield f"event: content\n"
                                yield f"data: {json.dumps(content_event_data)}\n\n"
                                flush_buffers()  # Flush content events immediately
                                last_sent_event_id = max(last_sent_event_id, content_event_id)  # Update last sent event ID
                                print(f"[RAILWAY_DEBUG] Job {job_id}: Content event yielded and flushed", file=sys.stdout, flush=True)
                                logger.info(f"[STREAM_CONTENT] Job {job_id}: Sent content event for {artifact.type}, length={len(artifact.content_text)}")
                        
                        last_artifact_count = len(current_artifacts)
                    
                    # Check for new SSE events (like tts_completed, tts_started, etc.) that were added directly to store
                    try:
                        new_events = sse_store.get_events_since(job_id, last_sent_event_id)
                        for event in new_events:
                            # Skip events we've already sent (shouldn't happen, but safety check)
                            if event['id'] > last_sent_event_id:
                                yield f"id: {event['id']}\n"
                                yield f"event: {event['type']}\n"
                                yield f"data: {json.dumps(event['data'])}\n\n"
                                flush_buffers()
                                last_sent_event_id = event['id']
                                logger.info(f"[STREAM_EVENT] Job {job_id}: Sent SSE store event {event['type']} (id: {event['id']})")
                    except Exception as sse_event_error:
                        logger.error(f"[STREAM_ERROR] Job {job_id}: Failed to check SSE events: {type(sse_event_error).__name__}: {str(sse_event_error)}", exc_info=True)
                    
                    # Wait before next poll (reduced to 0.5 seconds for more responsive updates)
                    await asyncio.sleep(0.5)
                except Exception as poll_error:
                    # Handle errors during polling
                    logger.error(f"[STREAM_ERROR] Job {job_id}: Error during poll #{poll_count}: {type(poll_error).__name__}: {str(poll_error)}", exc_info=True)
                    # Send error event but continue polling (client can decide to reconnect)
                    error_data = {'type': 'error', 'job_id': job_id, 'message': f'Polling error: {str(poll_error)}'}
                    try:
                        event_id = sse_store.add_event(job_id, 'error', error_data)
                        yield f"id: {event_id}\n"
                        yield f"event: error\n"
                        yield f"data: {json.dumps(error_data)}\n\n"
                        flush_buffers()  # Flush error events immediately
                    except Exception as yield_error:
                        logger.error(f"[STREAM_ERROR] Job {job_id}: Failed to yield error event: {type(yield_error).__name__}: {str(yield_error)}")
                        # If we can't yield, the connection is likely broken - exit
                        break
                    # Wait before retrying
                    await asyncio.sleep(0.5)
            
            # Before closing stream, check if job failed and send error if not already sent
            try:
                db.refresh(job)
                if job.status == JobStatus.FAILED.value:
                    # Check if we already sent an error event
                    recent_events = sse_store.get_events_since(job_id, 0)
                    error_events = [e for e in recent_events if e.get('type') == 'error']
                    if error_events:
                        # Error already sent, but make sure it's the latest
                        latest_error = error_events[-1]
                        error_data = latest_error.get('data', {})
                        if error_data and error_data.get('message'):
                            # Error already sent with message, we're good
                            logger.info(f"[STREAM_END] Job {job_id}: Error event already sent, stream closing")
                        else:
                            # Error sent but no message, send it again with details
                            error_data = {'type': 'error', 'job_id': job_id, 'status': job.status, 'message': 'Job failed. Check backend logs for details.'}
                            event_id = sse_store.add_event(job_id, 'error', error_data)
                            yield f"id: {event_id}\n"
                            yield f"event: error\n"
                            yield f"data: {json.dumps(error_data)}\n\n"
                            flush_buffers()
                    else:
                        # No error event sent, send one now
                        error_data = {'type': 'error', 'job_id': job_id, 'status': job.status, 'message': 'Job failed. Check backend logs for details.'}
                        event_id = sse_store.add_event(job_id, 'error', error_data)
                        yield f"id: {event_id}\n"
                        yield f"event: error\n"
                        yield f"data: {json.dumps(error_data)}\n\n"
                        flush_buffers()
                        logger.warning(f"[STREAM_END] Job {job_id}: Job failed but no error event was sent, sending now")
            except Exception as final_check_error:
                logger.error(f"[STREAM_ERROR] Job {job_id}: Error checking final job status: {type(final_check_error).__name__}: {str(final_check_error)}")
        except Exception as stream_error:
            # Handle errors in the stream generator itself
            logger.error(f"[STREAM_ERROR] Job {job_id}: Fatal error in stream generator: {type(stream_error).__name__}: {str(stream_error)}", exc_info=True)
            # Try to send a final error event
            try:
                error_data = {'type': 'error', 'job_id': job_id, 'message': f'Stream error: {str(stream_error)}'}
                event_id = sse_store.add_event(job_id, 'error', error_data)
                yield f"id: {event_id}\n"
                yield f"event: error\n"
                yield f"data: {json.dumps(error_data)}\n\n"
                flush_buffers()  # Flush final error event
            except Exception:
                # Can't send error - connection is broken
                pass
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Content-Type": "text/event-stream; charset=utf-8",  # Explicit content type
        }
    )


def _job_to_response(job: ContentJob) -> JobResponse:
    """Convert ContentJob to JobResponse"""
    artifacts = []
    if job.artifacts:
        for artifact in job.artifacts:
            artifact_dict = {
                'id': artifact.id,
                'type': artifact.type,
                'created_at': artifact.created_at.isoformat() if artifact.created_at else None,
                'has_content': bool(artifact.content_text)
            }
            
            # Include metadata for voiceover_audio artifacts
            if artifact.type == 'voiceover_audio' and artifact.content_json:
                artifact_dict['metadata'] = artifact.content_json
                # Include storage URL if available
                if artifact.content_json.get('storage_key'):
                    from .services.storage_provider import get_storage_provider
                    storage = get_storage_provider()
                    artifact_dict['url'] = storage.get_url(artifact.content_json['storage_key'])
            
            # Include metadata for video artifacts
            if artifact.type in ['final_video', 'video_clip', 'storyboard_image'] and artifact.content_json:
                artifact_dict['metadata'] = artifact.content_json
                # Include storage URL if available
                if artifact.content_json.get('storage_key'):
                    storage = get_storage_provider()
                    artifact_dict['url'] = storage.get_url(artifact.content_json['storage_key'])
            
            artifacts.append(artifact_dict)
    
    return JobResponse(
        id=job.id,
        topic=job.topic,
        formats_requested=job.formats_requested,
        status=job.status,
        idempotency_key=job.idempotency_key,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        artifacts=artifacts
    )


async def run_generation_async(
    job_id: int,
    topic: str,
    content_types: List[str],
    plan: str,
    user_id: int
):
    """
    Run content generation asynchronously and persist results
    
    This function runs in the background and updates the job status and artifacts.
    Includes timeout protection to prevent jobs from hanging indefinitely.
    
    NOTE: Only a single content type should be passed. If multiple are provided,
    only the first one will be used.
    """
    from content_creation_crew.crew import ContentCreationCrew
    from content_creation_crew.services.content_service import ContentService
    from content_creation_crew.services.plan_policy import PlanPolicy
    from content_creation_crew.content_validator import validate_and_repair_content
    from content_creation_crew.database import User, SessionLocal
    from content_creation_crew.config import config
    from content_creation_crew.services.sse_store import get_sse_store
    
    # Import extraction functions dynamically to avoid circular imports
    import importlib
    api_server_module = importlib.import_module('api_server')
    
    session = None
    sse_store = get_sse_store()
    timeout_seconds = config.CREWAI_TIMEOUT
    
    # Enforce single content type - use only the first one if multiple provided
    if len(content_types) > 1:
        logger.warning(f"Job {job_id}: Multiple content types provided {content_types}, using only first: {content_types[0]}")
        content_types = [content_types[0]]
    
    # Ensure at least one content type (default to blog)
    if not content_types or len(content_types) == 0:
        logger.info(f"Job {job_id}: No content types provided, defaulting to 'blog'")
        content_types = ['blog']
    
    # Get the single content type being generated
    content_type = content_types[0]
    content_type_display = {
        'blog': 'Blog Post',
        'social': 'Social Media Content',
        'audio': 'Audio Content',
        'video': 'Video Content'
    }.get(content_type, content_type.capitalize())
    
    # Immediate logging with flush for Railway visibility
    # Use print() for critical messages as logger might be buffered
    print(f"[RAILWAY_DEBUG] Job {job_id} started: topic='{topic}', plan='{plan}', content_type='{content_type}'", file=sys.stdout, flush=True)
    logger.info(f"[JOB_START] Job {job_id}: Starting content generation")
    logger.info(f"[JOB_START] Job {job_id}: Topic='{topic}', Plan='{plan}', Content Type='{content_type_display}', User={user_id}")
    # Force flush after logger calls
    sys.stdout.flush()
    sys.stderr.flush()
    
    session = None
    try:
        # Get fresh database session with retry logic for connection errors
        user = None
        max_init_retries = 3
        init_retry_delay = 0.5
        for init_retry in range(max_init_retries):
            session = SessionLocal()
            try:
                user = session.query(User).filter(User.id == user_id).first()
                if user:
                    break  # Success - exit retry loop
                else:
                    # User not found - don't retry
                    logger.error(f"User {user_id} not found for job {job_id}")
                    sys.stdout.flush()
                    sys.stderr.flush()
                    session.close()
                    return
            except (OperationalError, DisconnectionError) as init_error:
                logger.warning(f"[INIT_RETRY] Job {job_id}: Initial database query failed on attempt {init_retry + 1}/{max_init_retries}: {init_error}")
                try:
                    session.close()
                except:
                    pass
                if init_retry < max_init_retries - 1:
                    await asyncio.sleep(init_retry_delay)
                    init_retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    # All retries exhausted - re-raise to be caught by outer handler
                    raise
            except Exception as init_error:
                # Non-connection error - don't retry
                try:
                    session.close()
                except:
                    pass
                raise
        
        if not user:
            logger.error(f"User {user_id} not found for job {job_id} after retries")
            if session:
                session.close()
            return
        
        content_service = ContentService(session, user)
        policy = PlanPolicy(session, user)
        
        # Update job status to running with retry logic
        max_status_retries = 3
        status_retry_delay = 0.5
        for status_retry in range(max_status_retries):
            try:
                content_service.update_job_status(
                    job_id,
                    JobStatus.RUNNING.value,
                    started_at=datetime.utcnow()
                )
                session.commit()
                break  # Success - exit retry loop
            except (OperationalError, DisconnectionError) as status_error:
                logger.warning(f"[STATUS_RETRY] Job {job_id}: Status update failed on attempt {status_retry + 1}/{max_status_retries}: {status_error}")
                session.rollback()
                if status_retry < max_status_retries - 1:
                    await asyncio.sleep(status_retry_delay)
                    status_retry_delay *= 2  # Exponential backoff
                    # Refresh session and user for retry
                    try:
                        session.close()
                    except:
                        pass
                    session = SessionLocal()
                    user = session.query(User).filter(User.id == user_id).first()
                    if not user:
                        logger.error(f"User {user_id} not found during status update retry")
                        session.close()
                        return
                    content_service = ContentService(session, user)
                    continue
                else:
                    # All retries exhausted - re-raise to be caught by outer handler
                    raise
            except Exception as status_error:
                # Non-connection error - don't retry
                session.rollback()
                raise
        
        # Get the single content type being generated (enforced at function start)
        content_type = content_types[0] if content_types else 'blog'
        content_type_display = {
            'blog': 'Blog Post',
            'social': 'Social Media Content',
            'audio': 'Audio Content',
            'video': 'Video Content'
        }.get(content_type, content_type.capitalize())
        
        # Send SSE event for job started with content type notification
        sse_store.add_event(job_id, 'job_started', {
            'job_id': job_id,
            'status': JobStatus.RUNNING.value,
            'message': f'Starting {content_type_display} generation...',
            'content_type': content_type,
            'content_type_display': content_type_display
        })
        
        # Send explicit notification about content type being generated
        sse_store.add_event(job_id, 'status_update', {
            'job_id': job_id,
            'status': 'running',
            'message': f'Generating {content_type_display} for: {topic}',
            'content_type': content_type,
            'content_type_display': content_type_display
        })
        logger.info(f"Job {job_id}: Notified user - generating {content_type_display}")
        print(f"[RAILWAY_DEBUG] Job {job_id}: Notified user - generating {content_type_display}", file=sys.stdout, flush=True)
        
        # Get model name - check for user-specific preference for the content type
        primary_content_type = content_type
        model_name = policy.get_model_name(content_type=primary_content_type) if primary_content_type else policy.get_model_name()
        plan = policy.get_plan()
        # Use print() for critical messages as logger might be buffered
        print(f"[RAILWAY_DEBUG] Job {job_id}: Model='{model_name}' (for {primary_content_type or 'default'}), Timeout={timeout_seconds}s, Content types={content_types}", file=sys.stdout, flush=True)
        logger.info(f"[JOB_START] Job {job_id}: Starting content generation")
        logger.info(f"[JOB_START] Job {job_id}: Topic='{topic}', Plan='{plan}', Model='{model_name}', Timeout={timeout_seconds}s")
        logger.info(f"[JOB_START] Job {job_id}: Content types requested: {content_types}")
        logger.debug(f"[JOB_START] Job {job_id}: User ID={user_id}, Organization ID={policy._get_user_org_id()}")
        sys.stdout.flush()
        sys.stderr.flush()
        
        # Check cache BEFORE running CrewAI (Performance Optimization)
        from .services.content_cache import get_cache
        cache = get_cache()
        cached_content = cache.get(topic, content_types, PROMPT_VERSION, model_name)
        
        # Flag to track if we're using cached content (prevents executor creation)
        using_cached_content = False
        
        if cached_content:
            logger.info(f"Job {job_id}: Cache hit for topic: {topic}, using cached content")
            sse_store.add_event(job_id, 'agent_progress', {
                'job_id': job_id,
                'message': 'Using cached content...',
                'step': 'cache_hit'
            })
            
            # Create artifacts from cache
            if 'blog' in content_types and cached_content.get('content'):
                # Validate cached blog content
                from .content_validator import validate_and_repair_content
                is_valid, validated_model, content, was_repaired = validate_and_repair_content(
                    'blog', cached_content['content'], model_name, allow_repair=False
                )
                if not is_valid:
                    content = cached_content['content']
                
                # Moderate cached content before saving
                if config.ENABLE_CONTENT_MODERATION:
                    from .services.moderation_service import get_moderation_service
                    moderation_service = get_moderation_service()
                    moderation_result = moderation_service.moderate_output(
                        content,
                        'blog',
                        context={"job_id": job_id, "user_id": user_id, "cached": True}
                    )
                    
                    if moderation_result.passed:
                        content_service.create_artifact(
                            job_id,
                            'blog',
                            content,
                            content_json=validated_model.model_dump() if is_valid and validated_model else None,
                            prompt_version=PROMPT_VERSION,
                            model_used=model_name
                        )
                    sse_store.add_event(job_id, 'artifact_ready', {
                        'job_id': job_id,
                        'artifact_type': 'blog',
                        'message': 'Blog content from cache',
                        'cached': True
                    })
                    # Send content event with actual blog content
                    sse_store.add_event(job_id, 'content', {
                        'job_id': job_id,
                        'chunk': content,
                        'progress': 100,
                        'artifact_type': 'blog',
                        'content_field': 'content',
                        'cached': True
                    })
                else:
                    content_service.create_artifact(
                        job_id,
                        'blog',
                        content,
                        content_json=validated_model.model_dump() if is_valid and validated_model else None,
                        prompt_version=PROMPT_VERSION,
                        model_used=model_name
                    )
                    sse_store.add_event(job_id, 'artifact_ready', {
                        'job_id': job_id,
                        'artifact_type': 'blog',
                        'message': 'Blog content from cache',
                        'cached': True
                    })
                    # Send content event with actual blog content
                    sse_store.add_event(job_id, 'content', {
                        'job_id': job_id,
                        'chunk': content,
                        'progress': 100,
                        'artifact_type': 'blog',
                        'content_field': 'content',
                        'cached': True
                    })
            
            # Handle other content types from cache
            for content_type in content_types:
                if content_type == 'blog':
                    continue
                
                cache_key_map = {
                    'social': 'social_media_content',
                    'audio': 'audio_content',
                    'video': 'video_content'
                }
                cache_key = cache_key_map.get(content_type)
                if cache_key and cached_content.get(cache_key):
                    raw_content = cached_content[cache_key]
                    from .content_validator import validate_and_repair_content
                    is_valid, validated_model, validated_content, was_repaired = validate_and_repair_content(
                        content_type, raw_content, model_name, allow_repair=False
                    )
                    if not is_valid:
                        validated_content = raw_content
                    
                    content_service.create_artifact(
                        job_id,
                        content_type,
                        validated_content,
                        content_json=validated_model.model_dump() if is_valid and validated_model else None,
                        prompt_version=PROMPT_VERSION,
                        model_used=model_name
                    )
                    sse_store.add_event(job_id, 'artifact_ready', {
                        'job_id': job_id,
                        'artifact_type': content_type,
                        'message': f'{content_type} content from cache',
                        'cached': True
                    })
                    # Send content event with actual content
                    content_field = {
                        'social': 'social_media_content',
                        'audio': 'audio_content',
                        'video': 'video_content'
                    }.get(content_type, 'content')
                    sse_store.add_event(job_id, 'content', {
                        'job_id': job_id,
                        'chunk': validated_content,
                        'progress': 100,
                        'artifact_type': content_type,
                        'content_field': content_field,
                        'cached': True
                    })
            
            # Verify all requested content types are present in cache
            missing_content_types = []
            cache_key_map = {
                'blog': 'content',
                'social': 'social_media_content',
                'audio': 'audio_content',
                'video': 'video_content'
            }
            for content_type in content_types:
                cache_key = cache_key_map.get(content_type)
                if cache_key and not cached_content.get(cache_key):
                    missing_content_types.append(content_type)
            
            if missing_content_types:
                logger.info(f"Job {job_id}: Partial cache hit - missing types: {missing_content_types}, proceeding with generation for missing types")
                # Don't return - continue with generation for missing content types
                # Store which content types were cached so we can skip them during extraction
                cached_content_types_set = set(content_types) - set(missing_content_types)
                print(f"[RAILWAY_DEBUG] Job {job_id}: Partial cache hit, generating missing types: {missing_content_types}, cached types: {cached_content_types_set}", file=sys.stdout, flush=True)
            else:
                # All content types are cached - mark job as completed and return immediately
                using_cached_content = True
                cached_content_types_set = set(content_types)  # All types cached
                
                # Send complete event with all cached content
                complete_content = {}
                for content_type in content_types:
                    cache_key_map = {
                        'blog': 'content',
                        'social': 'social_media_content',
                        'audio': 'audio_content',
                        'video': 'video_content'
                    }
                    cache_key = cache_key_map.get(content_type)
                    if cache_key and cached_content.get(cache_key):
                        complete_content[content_type] = cached_content[cache_key]
                
                content_service.update_job_status(
                    job_id,
                    JobStatus.COMPLETED.value,
                    finished_at=datetime.utcnow()
                )
                sse_store.add_event(job_id, 'complete', {
                    'job_id': job_id,
                    'status': JobStatus.COMPLETED.value,
                    'message': 'Content generated from cache',
                    'cached': True,
                    'content': complete_content
                })
                logger.info(f"Job {job_id}: Completed using cached content - all {len(content_types)} content types served from cache")
                print(f"[RAILWAY_DEBUG] Job {job_id}: All content types cached, marking as completed and returning (no executor will be created)", file=sys.stdout, flush=True)
                sys.stdout.flush()
                sys.stderr.flush()
                return  # Skip CrewAI execution - this prevents executor from being created
        
        # Cache miss - proceed with CrewAI generation
        logger.info(f"[CACHE] Job {job_id}: Cache miss, running CrewAI generation")
        logger.debug(f"[CACHE] Job {job_id}: Cache key would be: topic='{topic}', types={content_types}, version={PROMPT_VERSION}, model={model_name}")
        
        # Validate LLM configuration before attempting initialization
        print(f"[RAILWAY_DEBUG] Job {job_id}: Validating LLM configuration - OPENAI_API_KEY={'SET' if config.OPENAI_API_KEY else 'NOT SET'}, OLLAMA_BASE_URL={'SET' if config.OLLAMA_BASE_URL else 'NOT SET'}", file=sys.stdout, flush=True)
        logger.info(f"[CREW_INIT] Job {job_id}: Validating LLM configuration before initialization")
        sys.stdout.flush()
        sys.stderr.flush()
        if not config.OPENAI_API_KEY and not config.OLLAMA_BASE_URL:
            error_msg = "LLM provider not configured: OPENAI_API_KEY and OLLAMA_BASE_URL are both missing. Please set OPENAI_API_KEY in backend environment variables."
            logger.error(f"[CREW_INIT] Job {job_id}: {error_msg}")
            sys.stdout.flush()
            sys.stderr.flush()
            content_service.update_job_status(
                job_id,
                JobStatus.FAILED.value,
                finished_at=datetime.utcnow()
            )
            sse_store.add_event(job_id, 'error', {
                'job_id': job_id,
                'message': error_msg,
                'error_type': 'configuration_error',
                'hint': 'Set OPENAI_API_KEY in Railway backend service variables (not frontend .env)'
            })
            return
        
        # Check OpenAI API key format if using OpenAI
        if config.OPENAI_API_KEY:
            if not config.OPENAI_API_KEY.startswith('sk-'):
                error_msg = f"Invalid OPENAI_API_KEY format: API key should start with 'sk-'. Current key starts with '{config.OPENAI_API_KEY[:5]}...'"
                logger.error(f"[CREW_INIT] Job {job_id}: {error_msg}")
                sys.stdout.flush()
                sys.stderr.flush()
                content_service.update_job_status(
                    job_id,
                    JobStatus.FAILED.value,
                    finished_at=datetime.utcnow()
                )
                sse_store.add_event(job_id, 'error', {
                    'job_id': job_id,
                    'message': error_msg,
                    'error_type': 'configuration_error',
                    'hint': 'Verify OPENAI_API_KEY is correct and starts with sk-'
                })
                return
        
        # Run generation
        print(f"[RAILWAY_DEBUG] Job {job_id}: Initializing ContentCreationCrew with tier='{plan}', content_types={content_types}", file=sys.stdout, flush=True)
        logger.info(f"[CREW_INIT] Job {job_id}: Initializing ContentCreationCrew with tier='{plan}', content_types={content_types}")
        sys.stdout.flush()
        sys.stderr.flush()
        crew_init_start = time.time()
        try:
            crew_instance = ContentCreationCrew(tier=plan, content_types=content_types)
            crew_obj = crew_instance._build_crew(content_types=content_types)
            crew_init_duration = time.time() - crew_init_start
            print(f"[RAILWAY_DEBUG] Job {job_id}: Crew initialization completed in {crew_init_duration:.2f}s", file=sys.stdout, flush=True)
            logger.info(f"[CREW_INIT] Job {job_id}: Crew initialization completed in {crew_init_duration:.2f}s")
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception as crew_init_error:
            crew_init_duration = time.time() - crew_init_start
            error_type = type(crew_init_error).__name__
            error_msg = str(crew_init_error) if str(crew_init_error) else f"{error_type} during crew initialization"
            
            # Provide more specific error messages based on error type
            if 'api key' in error_msg.lower() or 'authentication' in error_msg.lower() or 'unauthorized' in error_msg.lower():
                detailed_error = f"LLM authentication failed: {error_msg}. Please verify OPENAI_API_KEY is set correctly in backend environment."
            elif 'connection' in error_msg.lower() or 'connect' in error_msg.lower():
                detailed_error = f"LLM connection failed: {error_msg}. Please check network connectivity and LLM service availability."
            elif 'timeout' in error_msg.lower():
                detailed_error = f"LLM initialization timeout: {error_msg}. The LLM service may be unavailable or slow to respond."
            else:
                detailed_error = f"LLM initialization failed: {error_msg}"
            
            print(f"[RAILWAY_DEBUG] Job {job_id}: CREW_INIT FAILED - {error_type}: {detailed_error}", file=sys.stdout, flush=True)
            logger.error(f"[CREW_INIT] Job {job_id}: FAILED after {crew_init_duration:.2f}s: {detailed_error}", exc_info=True)
            logger.error(f"[CREW_INIT] Job {job_id}: Error type={error_type}, model={model_name}, provider={'OpenAI' if config.OPENAI_API_KEY else 'Ollama'}")
            sys.stdout.flush()
            sys.stderr.flush()
            
            # Update job status and send error event
            content_service.update_job_status(
                job_id,
                JobStatus.FAILED.value,
                finished_at=datetime.utcnow()
            )
            sse_store.add_event(job_id, 'error', {
                'job_id': job_id,
                'message': detailed_error,
                'error_type': error_type,
                'hint': 'Check backend logs for detailed error information. Verify OPENAI_API_KEY is set in backend environment variables.'
            })
            return
        
        # Send progress update
        sse_store.add_event(job_id, 'agent_progress', {
            'job_id': job_id,
            'message': 'Initializing CrewAI agents...',
            'step': 'initialization'
        })
        sys.stdout.flush()
        sys.stderr.flush()
        
        # Run crew synchronously with timeout (we're already in async task)
        loop = asyncio.get_event_loop()
        
        # Track LLM metrics (M7)
        from .services.metrics import LLMMetrics
        llm_start_time = time.time()
        llm_success = False
        
        # Progress tracking for streaming updates
        executor_done = False
        result = None
        executor_error = None
        
        async def run_executor_with_progress():
            """Run executor and send periodic progress updates"""
            nonlocal executor_done, result, executor_error, llm_success
            
            print(f"[RAILWAY_DEBUG] Job {job_id}: Executor function started", file=sys.stdout, flush=True)
            
            try:
                # Send research started
                sse_store.add_event(job_id, 'agent_progress', {
                    'job_id': job_id,
                    'message': 'Starting research phase...',
                    'step': 'research'
                })
                
                print(f"[RAILWAY_DEBUG] Job {job_id}: Starting CrewAI kickoff with topic='{topic}', model='{model_name}'", file=sys.stdout, flush=True)
                logger.info(f"[LLM_EXEC] Job {job_id}: Starting CrewAI kickoff with topic='{topic}'")
                logger.info(f"[LLM_EXEC] Job {job_id}: Using model '{model_name}' with timeout={timeout_seconds}s")
                sys.stdout.flush()
                sys.stderr.flush()
                llm_exec_start = time.time()
                
                # Use timeout from config (default 300s / 5 minutes) for content generation
                # This prevents jobs from hanging while allowing sufficient time for completion
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: crew_obj.kickoff(inputs={'topic': topic})
                    ),
                    timeout=timeout_seconds  # Default 300 seconds from config
                )
                
                llm_exec_duration = time.time() - llm_exec_start
                llm_success = True
                executor_done = True
                print(f"[RAILWAY_DEBUG] Job {job_id}: CrewAI execution completed successfully in {llm_exec_duration:.2f}s", file=sys.stdout, flush=True)
                print(f"[RAILWAY_DEBUG] Job {job_id}: Result stored, executor_done={executor_done}, result is None={result is None}", file=sys.stdout, flush=True)
                logger.info(f"[LLM_EXEC] Job {job_id}: CrewAI execution completed successfully in {llm_exec_duration:.2f}s")
                print(f"[RAILWAY_DEBUG] Job {job_id}: Result type={type(result)}, has tasks_output={hasattr(result, 'tasks_output')}", file=sys.stdout, flush=True)
                logger.debug(f"[LLM_EXEC] Job {job_id}: Result type={type(result)}, has tasks_output={hasattr(result, 'tasks_output')}")
                if hasattr(result, 'tasks_output') and result.tasks_output:
                    print(f"[RAILWAY_DEBUG] Job {job_id}: Number of task outputs: {len(result.tasks_output)}", file=sys.stdout, flush=True)
                    logger.debug(f"[LLM_EXEC] Job {job_id}: Number of task outputs: {len(result.tasks_output)}")
                    # Log task output details
                    for i, task_output in enumerate(result.tasks_output):
                        task_desc = getattr(task_output, 'description', 'unknown')[:50] if hasattr(task_output, 'description') else 'unknown'
                        print(f"[RAILWAY_DEBUG] Job {job_id}: Task {i+1}: {task_desc}", file=sys.stdout, flush=True)
                else:
                    print(f"[RAILWAY_DEBUG] Job {job_id}: No tasks_output found in result", file=sys.stdout, flush=True)
                print(f"[RAILWAY_DEBUG] Job {job_id}: Executor task marked as done, result stored", file=sys.stdout, flush=True)
                sys.stdout.flush()
                sys.stderr.flush()
            except asyncio.TimeoutError:
                llm_exec_duration = time.time() - llm_exec_start if 'llm_exec_start' in locals() else 0
                executor_error = TimeoutError(f"Content generation timed out after {timeout_seconds} seconds")
                executor_done = True
                print(f"[RAILWAY_DEBUG] Job {job_id}: TIMEOUT after {llm_exec_duration:.2f}s (limit: {timeout_seconds}s)", file=sys.stdout, flush=True)
                logger.error(f"[LLM_EXEC] Job {job_id}: TIMEOUT after {llm_exec_duration:.2f}s (limit: {timeout_seconds}s)")
                logger.error(f"[LLM_EXEC] Job {job_id}: Model '{model_name}' exceeded timeout threshold")
                sys.stdout.flush()
                sys.stderr.flush()
            except Exception as e:
                llm_exec_duration = time.time() - llm_exec_start if 'llm_exec_start' in locals() else 0
                executor_error = e
                executor_done = True
                
                # Check for rate limit errors
                error_msg = str(e)
                error_type = type(e).__name__
                
                # Detect rate limit errors from OpenAI
                is_rate_limit = False
                retry_after = None
                error_str_lower = error_msg.lower()
                if ('rate limit' in error_str_lower or 
                    '429' in error_msg or 
                    'rate_limit' in error_str_lower or
                    'rate_limit_exceeded' in error_str_lower or
                    'tokens per min' in error_str_lower or
                    'requests per min' in error_str_lower):
                    is_rate_limit = True
                    print(f"[RAILWAY_DEBUG] Job {job_id}: RATE LIMIT ERROR detected", file=sys.stdout, flush=True)
                    # Try to extract retry-after time from error message
                    import re
                    # Pattern 1: "try again in 3h55m26.4s"
                    retry_match = re.search(r'try again in ([\d.]+[hms]+)', error_msg, re.IGNORECASE)
                    if retry_match:
                        retry_after = retry_match.group(1)
                    # Pattern 2: "Please try again in 3h55m26.4s"
                    if not retry_after:
                        retry_match = re.search(r'Please try again in ([\d.]+[hms]+)', error_msg, re.IGNORECASE)
                        if retry_match:
                            retry_after = retry_match.group(1)
                    # Also check for TPM/RPM limits
                    limit_match = re.search(r'Limit (\d+), Used (\d+), Requested (\d+)', error_msg)
                    if limit_match:
                        limit, used, requested = limit_match.groups()
                        print(f"[RAILWAY_DEBUG] Job {job_id}: Rate limit details - Limit: {limit}, Used: {used}, Requested: {requested}", file=sys.stdout, flush=True)
                
                print(f"[RAILWAY_DEBUG] Job {job_id}: LLM_EXEC ERROR - {error_type}: {error_msg[:200]}", file=sys.stdout, flush=True)
                logger.error(f"[LLM_EXEC] Job {job_id}: ERROR after {llm_exec_duration:.2f}s: {error_type}: {error_msg}", exc_info=True)
                
                # Store rate limit info in executor_error for later handling
                if is_rate_limit:
                    executor_error.rate_limit = True
                    executor_error.retry_after = retry_after
                
                sys.stdout.flush()
                sys.stderr.flush()
        
        # Safety check: Never create executor if using cached content
        if using_cached_content:
            logger.error(f"Job {job_id}: CRITICAL ERROR - Attempted to create executor when using cached content. This should never happen!")
            print(f"[RAILWAY_DEBUG] Job {job_id}: CRITICAL ERROR - Executor creation attempted with cached content flag set. Returning immediately.", file=sys.stdout, flush=True)
            return
        
        # Start executor task (only if not using cached content)
        print(f"[RAILWAY_DEBUG] Job {job_id}: Creating executor task...", file=sys.stdout, flush=True)
        executor_task = asyncio.create_task(run_executor_with_progress())
        print(f"[RAILWAY_DEBUG] Job {job_id}: Executor task created, entering wait loop (timeout={timeout_seconds}s)", file=sys.stdout, flush=True)
        
        # Send periodic progress updates while executor is running
        progress_steps = [
            ('research', 'Researching topic...'),
            ('writing', 'Writing blog post...'),
            ('editing', 'Editing and formatting...'),
        ]
        step_index = 0
        last_progress_time = time.time()
        
        try:
            wait_loop_count = 0
            # Use shorter wait interval (5 seconds instead of 10) for faster response
            wait_interval = 5.0
            while not executor_done:
                wait_loop_count += 1
                # Wait for either executor completion or wait_interval seconds (whichever comes first)
                done, pending = await asyncio.wait(
                    [executor_task],
                    timeout=wait_interval,
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                if done:
                    # Executor completed
                    elapsed_total = wait_loop_count * wait_interval
                    print(f"[RAILWAY_DEBUG] Job {job_id}: Executor task completed, breaking from wait loop (waited {elapsed_total:.1f}s)", file=sys.stdout, flush=True)
                    break
                else:
                    # Timeout - executor still running, send progress update
                    elapsed = time.time() - last_progress_time
                    elapsed_total = wait_loop_count * wait_interval
                    print(f"[RAILWAY_DEBUG] Job {job_id}: Executor still running, elapsed={elapsed_total:.1f}s, executor_done={executor_done}", file=sys.stdout, flush=True)
                    # Send progress update every wait_interval seconds
                    if elapsed >= wait_interval and step_index < len(progress_steps):
                        step, message = progress_steps[step_index]
                        sse_store.add_event(job_id, 'agent_progress', {
                            'job_id': job_id,
                            'message': message,
                            'step': step
                        })
                        step_index = min(step_index + 1, len(progress_steps) - 1)
                        last_progress_time = time.time()
            
            # Ensure executor completed
            print(f"[RAILWAY_DEBUG] Job {job_id}: Waiting for executor task to complete...", file=sys.stdout, flush=True)
            try:
                await executor_task
            except Exception as await_error:
                print(f"[RAILWAY_DEBUG] Job {job_id}: ERROR awaiting executor task: {type(await_error).__name__}: {str(await_error)[:200]}", file=sys.stdout, flush=True)
                logger.error(f"Job {job_id}: Error awaiting executor task: {await_error}", exc_info=True)
                if executor_error is None:
                    executor_error = await_error
            
            print(f"[RAILWAY_DEBUG] Job {job_id}: Executor task awaited, checking for errors...", file=sys.stdout, flush=True)
            print(f"[RAILWAY_DEBUG] Job {job_id}: executor_error={executor_error}, executor_done={executor_done}, result is None={result is None}", file=sys.stdout, flush=True)
            
            if executor_error:
                if isinstance(executor_error, TimeoutError):
                    error_msg = str(executor_error)
                    # Create user-friendly timeout message
                    timeout_msg = f"Content generation timed out after {timeout_seconds} seconds. "
                    timeout_msg += "The generation process took longer than the configured timeout. "
                    timeout_msg += "This may happen when generating multiple content types (blog, social, audio, video). "
                    timeout_msg += "Try generating fewer content types at once or increase the timeout limit."
                    
                    error_event_data = {
                        'type': 'error',  # Ensure type is set for frontend parsing
                        'job_id': job_id,
                        'message': timeout_msg,
                        'error_type': 'timeout',
                        'timeout_seconds': timeout_seconds,
                        'hint': 'Try generating fewer content types at once, or increase CREWAI_TIMEOUT in backend configuration'
                    }
                    
                    print(f"[RAILWAY_DEBUG] Job {job_id}: Sending timeout error to client: {timeout_msg[:100]}", file=sys.stdout, flush=True)
                    logger.error(f"Job {job_id}: {error_msg}")
                    event_id = sse_store.add_event(job_id, 'error', error_event_data)
                    print(f"[RAILWAY_DEBUG] Job {job_id}: Timeout error event added to SSE store with ID {event_id}", file=sys.stdout, flush=True)
                    # Update job status
                    content_service.update_job_status(
                        job_id,
                        JobStatus.FAILED.value,
                        finished_at=datetime.utcnow()
                    )
                    return  # Don't raise, error already sent via SSE
                else:
                    # Check for rate limit errors
                    error_msg = str(executor_error)
                    is_rate_limit = getattr(executor_error, 'rate_limit', False) or 'rate limit' in error_msg.lower() or '429' in error_msg
                    retry_after = getattr(executor_error, 'retry_after', None)
                    
                    if is_rate_limit:
                        # Create user-friendly rate limit error message
                        rate_limit_msg = "OpenAI API rate limit exceeded. "
                        if retry_after:
                            rate_limit_msg += f"Please try again in {retry_after}. "
                        else:
                            rate_limit_msg += "Please try again in a few hours. "
                        rate_limit_msg += "You can increase your rate limit by adding a payment method to your OpenAI account."
                        
                        print(f"[RAILWAY_DEBUG] Job {job_id}: Sending rate limit error to client", file=sys.stdout, flush=True)
                        logger.error(f"Job {job_id}: Rate limit error - {error_msg}")
                        sse_store.add_event(job_id, 'error', {
                            'job_id': job_id,
                            'message': rate_limit_msg,
                            'error_type': 'rate_limit',
                            'retry_after': retry_after,
                            'hint': 'Add a payment method to your OpenAI account to increase rate limits: https://platform.openai.com/account/billing'
                        })
                        # Update job status
                        content_service.update_job_status(
                            job_id,
                            JobStatus.FAILED.value,
                            finished_at=datetime.utcnow()
                        )
                        return  # Don't raise, error already sent via SSE
                    
                    raise executor_error
        except (TimeoutError, asyncio.TimeoutError) as e:
            error_msg = f"Content generation timed out after {timeout_seconds} seconds. The generation process took longer than the configured timeout."
            logger.error(f"Job {job_id}: {error_msg}")
            sse_store.add_event(job_id, 'error', {
                'job_id': job_id,
                'message': error_msg,
                'error_type': 'timeout'
            })
            raise TimeoutError(error_msg)
        finally:
            # Record LLM metrics (M7)
            llm_duration = time.time() - llm_start_time
            LLMMetrics.record_call(model_name, llm_duration, success=llm_success)
        
        # Send progress update
        print(f"[RAILWAY_DEBUG] Job {job_id}: No executor error, proceeding to extraction phase", file=sys.stdout, flush=True)
        print(f"[RAILWAY_DEBUG] Job {job_id}: Pre-extraction check - executor_done={executor_done}, result is None={result is None}, executor_error={executor_error}", file=sys.stdout, flush=True)
        
        # Verify result is available
        if result is None:
            error_msg = "Content generation completed but no result was returned. This may indicate a CrewAI execution issue."
            print(f"[RAILWAY_DEBUG] Job {job_id}: ERROR - result is None, cannot proceed with extraction", file=sys.stdout, flush=True)
            logger.error(f"Job {job_id}: {error_msg}")
            sse_store.add_event(job_id, 'error', {
                'type': 'error',
                'job_id': job_id,
                'message': error_msg,
                'error_type': 'no_result',
                'hint': 'Check backend logs for CrewAI execution details. The crew may have completed without returning a result.'
            })
            content_service.update_job_status(
                job_id,
                JobStatus.FAILED.value,
                finished_at=datetime.utcnow()
            )
            return
        
        sse_store.add_event(job_id, 'agent_progress', {
            'job_id': job_id,
            'message': 'Extracting and validating content...',
            'step': 'extraction'
        })
        
        # Extract and validate other content types
        # Skip content types that were already processed from cache
        cached_content_types_set = locals().get('cached_content_types_set', set())
        
        # Extract and validate blog content (only if blog is requested)
        if 'blog' in content_types and 'blog' not in cached_content_types_set:
            print(f"[RAILWAY_DEBUG] Job {job_id}: Starting blog content extraction from CrewAI result, result type={type(result)}, result={str(result)[:200] if result else 'None'}", file=sys.stdout, flush=True)
            logger.info(f"[EXTRACTION] Job {job_id}: Starting blog content extraction from CrewAI result")
            extraction_start = time.time()
            raw_content = await api_server_module.extract_content_async(result, topic, logger)
            extraction_duration = time.time() - extraction_start
            print(f"[RAILWAY_DEBUG] Job {job_id}: Blog content extraction completed, length={len(raw_content) if raw_content else 0}", file=sys.stdout, flush=True)
            logger.info(f"[EXTRACTION] Job {job_id}: Blog content extraction completed in {extraction_duration:.2f}s, content length={len(raw_content) if raw_content else 0}")
            
            # Validate and create blog artifact
            print(f"[RAILWAY_DEBUG] Job {job_id}: Starting blog content validation", file=sys.stdout, flush=True)
            logger.info(f"[VALIDATION] Job {job_id}: Starting blog content validation")
            validation_start = time.time()
            is_valid, validated_model, content, was_repaired = validate_and_repair_content(
                'blog', raw_content, model_name, allow_repair=True
            )
            validation_duration = time.time() - validation_start
            print(f"[RAILWAY_DEBUG] Job {job_id}: Blog validation completed, valid={is_valid}, content_length={len(content) if content else 0}", file=sys.stdout, flush=True)
            logger.info(f"[VALIDATION] Job {job_id}: Blog validation completed in {validation_duration:.3f}s, valid={is_valid}, repaired={was_repaired}")
            
            if not is_valid:
                logger.warning(f"[VALIDATION] Job {job_id}: Blog content validation failed, using cleaned raw content")
                content = api_server_module.clean_content(raw_content)
                logger.debug(f"[VALIDATION] Job {job_id}: Cleaned content length={len(content) if content else 0}")
            
            if content and len(content.strip()) > 10:
                # OPTIMIZATION (Phase 3): Create artifact and send content immediately, moderate in background
                artifact_start = time.time()
                artifact = content_service.create_artifact(
                    job_id,
                    'blog',
                    content,
                    content_json=validated_model.model_dump() if is_valid and validated_model else None,
                    prompt_version=PROMPT_VERSION,
                    model_used=model_name
                )
                # Commit immediately after artifact creation to avoid long transactions
                try:
                    session.commit()
                except Exception as commit_error:
                    logger.error(f"Job {job_id}: Failed to commit blog artifact: {commit_error}", exc_info=True)
                    session.rollback()
                    # Retry with new session if commit failed
                    try:
                        retry_session = SessionLocal()
                        try:
                            retry_user = retry_session.query(User).filter(User.id == user_id).first()
                            if retry_user:
                                retry_content_service = ContentService(retry_session, retry_user)
                                artifact = retry_content_service.create_artifact(
                                    job_id,
                                    'blog',
                                    content,
                                    content_json=validated_model.model_dump() if is_valid and validated_model else None,
                                    prompt_version=PROMPT_VERSION,
                                    model_used=model_name
                                )
                                retry_session.commit()
                                logger.info(f"Job {job_id}: Successfully created blog artifact with retry session")
                        finally:
                            retry_session.close()
                    except Exception as retry_error:
                        logger.error(f"Job {job_id}: Failed to create blog artifact even with retry: {retry_error}", exc_info=True)
                        raise
                artifact_duration = time.time() - artifact_start
                
                # Send content immediately (early streaming optimization)
                print(f"[RAILWAY_DEBUG] Job {job_id}: Blog artifact created, sending SSE events immediately", file=sys.stdout, flush=True)
                sse_store.add_event(job_id, 'artifact_ready', {
                    'job_id': job_id,
                    'artifact_type': 'blog',
                    'message': 'Blog content generated'
                })
                # Send content event with the actual blog content (early streaming)
                sse_store.add_event(job_id, 'content', {
                    'job_id': job_id,
                    'chunk': content,  # Send full content as a single chunk
                    'progress': 100,  # Blog is complete
                    'artifact_type': 'blog'
                })
                print(f"[RAILWAY_DEBUG] Job {job_id}: Blog artifact SSE events added to store, content_length={len(content)}", file=sys.stdout, flush=True)
                logger.info(f"[ARTIFACT] Job {job_id}: Blog artifact created in {artifact_duration:.3f}s, content_length={len(content)}")
                
                # OPTIMIZATION (Phase 3): Run moderation in background (non-blocking)
                if config.ENABLE_CONTENT_MODERATION:
                    logger.info(f"[MODERATION] Job {job_id}: Starting blog content moderation in background")
                    # Get artifact ID for background moderation
                    artifact_id = artifact.id if hasattr(artifact, 'id') else None
                    if artifact_id:
                        # Run moderation in background task (non-blocking)
                        asyncio.create_task(moderate_content_background(
                            job_id, content, 'blog', user_id, artifact_id
                        ))
                    else:
                        logger.warning(f"Job {job_id}: Could not get artifact ID for background moderation")
        
        for content_type in content_types:
            if content_type == 'blog' or content_type in cached_content_types_set:
                if content_type in cached_content_types_set:
                    print(f"[RAILWAY_DEBUG] Job {job_id}: Skipping {content_type} - already processed from cache", file=sys.stdout, flush=True)
                continue
            
            print(f"[RAILWAY_DEBUG] Job {job_id}: Processing {content_type} content extraction", file=sys.stdout, flush=True)
            logger.info(f"[EXTRACTION] Job {job_id}: Processing {content_type} content extraction")
            
            raw_content_func = {
                'social': api_server_module.extract_social_media_content_async,
                'audio': api_server_module.extract_audio_content_async,
                'video': api_server_module.extract_video_content_async,
            }.get(content_type)
            
            if raw_content_func:
                print(f"[RAILWAY_DEBUG] Job {job_id}: Calling {content_type} extraction function", file=sys.stdout, flush=True)
                extraction_start = time.time()
                raw_content = await raw_content_func(result, topic, logger)
                extraction_duration = time.time() - extraction_start
                print(f"[RAILWAY_DEBUG] Job {job_id}: {content_type} extraction completed in {extraction_duration:.3f}s, length={len(raw_content) if raw_content else 0}", file=sys.stdout, flush=True)
                logger.info(f"[EXTRACTION] Job {job_id}: {content_type} extraction completed in {extraction_duration:.3f}s, content length={len(raw_content) if raw_content else 0}")
                if raw_content:
                    validation_start = time.time()
                    # OPTIMIZATION: Social media uses simpler JSON, fail fast without repair
                    # Blog content may need repair due to complexity
                    allow_repair = content_type != 'social'
                    is_valid, validated_model, validated_content, was_repaired = validate_and_repair_content(
                        content_type, raw_content, model_name, allow_repair=allow_repair
                    )
                    validation_duration = time.time() - validation_start
                    print(f"[RAILWAY_DEBUG] Job {job_id}: {content_type} validation completed, valid={is_valid}, content_length={len(validated_content) if validated_content else 0}", file=sys.stdout, flush=True)
                    logger.info(f"[VALIDATION] Job {job_id}: {content_type} validation completed in {validation_duration:.3f}s, valid={is_valid}, repaired={was_repaired}")
                    
                    # Ensure we have content to work with (use validated_content or fallback to raw_content)
                    if not validated_content or len(validated_content.strip()) < 10:
                        logger.warning(f"[VALIDATION] Job {job_id}: {content_type} content validation failed or empty, using cleaned raw content")
                        validated_content = api_server_module.clean_content(raw_content)
                        logger.debug(f"[VALIDATION] Job {job_id}: Cleaned {content_type} content length={len(validated_content) if validated_content else 0}")
                    
                    # Final check - ensure we have valid content before proceeding
                    if validated_content and len(validated_content.strip()) > 10:
                        # OPTIMIZATION (Phase 3): Create artifact and send content immediately, moderate in background
                        artifact_start = time.time()
                        artifact = content_service.create_artifact(
                            job_id,
                            content_type,
                            validated_content,
                            content_json=validated_model.model_dump() if is_valid and validated_model else None,
                            prompt_version=PROMPT_VERSION,
                            model_used=model_name
                        )
                        # Commit immediately after artifact creation to avoid long transactions
                        # Retry logic for OperationalError (connection failures)
                        max_artifact_retries = 3
                        artifact_retry_delay = 0.5
                        artifact_created = False
                        for artifact_retry in range(max_artifact_retries):
                            try:
                                session.commit()
                                artifact_created = True
                                break  # Success - exit retry loop
                            except (OperationalError, DisconnectionError) as commit_error:
                                logger.warning(f"[ARTIFACT_RETRY] Job {job_id}: Failed to commit {content_type} artifact on attempt {artifact_retry + 1}/{max_artifact_retries}: {commit_error}")
                                session.rollback()
                                if artifact_retry < max_artifact_retries - 1:
                                    await asyncio.sleep(artifact_retry_delay)
                                    artifact_retry_delay *= 2  # Exponential backoff
                                    # Refresh session and recreate artifact
                                    try:
                                        session.close()
                                    except:
                                        pass
                                    session = SessionLocal()
                                    user = session.query(User).filter(User.id == user_id).first()
                                    if not user:
                                        logger.error(f"User {user_id} not found during artifact retry")
                                        session.close()
                                        raise
                                    content_service = ContentService(session, user)
                                    artifact = content_service.create_artifact(
                                        job_id,
                                        content_type,
                                        validated_content,
                                        content_json=validated_model.model_dump() if is_valid and validated_model else None,
                                        prompt_version=PROMPT_VERSION,
                                        model_used=model_name
                                    )
                                    continue
                                else:
                                    # All retries exhausted - re-raise to be caught by outer handler
                                    raise
                            except Exception as commit_error:
                                # Non-connection error - don't retry
                                logger.error(f"Job {job_id}: Failed to commit {content_type} artifact: {commit_error}", exc_info=True)
                                session.rollback()
                                raise
                        
                        if not artifact_created:
                            logger.error(f"Job {job_id}: Failed to create {content_type} artifact after {max_artifact_retries} retries")
                            raise Exception(f"Failed to create {content_type} artifact after retries")
                        artifact_duration = time.time() - artifact_start
                        
                        # Send content immediately (early streaming optimization)
                        print(f"[RAILWAY_DEBUG] Job {job_id}: {content_type} artifact created, sending SSE events immediately", file=sys.stdout, flush=True)
                        sse_store.add_event(job_id, 'artifact_ready', {
                            'job_id': job_id,
                            'artifact_type': content_type,
                            'message': f'{content_type.capitalize()} content generated'
                        })
                        # Send content event with the actual content (early streaming)
                        content_field = {
                            'social': 'social_media_content',
                            'audio': 'audio_content',
                            'video': 'video_content'
                        }.get(content_type, 'content')
                        sse_store.add_event(job_id, 'content', {
                            'job_id': job_id,
                            'chunk': validated_content,  # Send full content as a single chunk
                            'progress': 100,  # Content is complete
                            'artifact_type': content_type,
                            'content_field': content_field  # Help frontend identify which field to use
                        })
                        print(f"[RAILWAY_DEBUG] Job {job_id}: {content_type} artifact SSE events added to store, content_length={len(validated_content)}", file=sys.stdout, flush=True)
                        logger.info(f"[ARTIFACT] Job {job_id}: {content_type} artifact created in {artifact_duration:.3f}s, content_length={len(validated_content)}")
                        logger.info(f"Job {job_id}: {content_type} content event sent (early streaming)")
                        
                        # OPTIMIZATION (Phase 3): Run moderation in background (non-blocking)
                        # Note: Artifact is already created above (line 1773), so we just need to handle moderation
                        if config.ENABLE_CONTENT_MODERATION:
                            logger.info(f"[MODERATION] Job {job_id}: Starting {content_type} content moderation in background")
                            # Get artifact ID for background moderation
                            artifact_id = artifact.id if hasattr(artifact, 'id') else None
                            if artifact_id:
                                # Run moderation in background task (non-blocking)
                                asyncio.create_task(moderate_content_background(
                                    job_id, validated_content, content_type, user_id, artifact_id
                                ))
                            else:
                                logger.warning(f"Job {job_id}: Could not get artifact ID for background moderation")
                        # Note: When moderation is disabled, artifact and SSE events are already sent above
                        # No need to duplicate artifact creation or SSE events
                    else:
                        # Content extraction succeeded but validation/cleaning resulted in empty content
                        error_msg = f"{content_type.capitalize()} content extraction succeeded but resulted in empty content after validation/cleaning"
                        logger.error(f"Job {job_id}: {error_msg}")
                        print(f"[RAILWAY_DEBUG] Job {job_id}: ERROR - {error_msg}", file=sys.stdout, flush=True)
                        sse_store.add_event(job_id, 'error', {
                            'job_id': job_id,
                            'message': error_msg,
                            'error_type': 'empty_content',
                            'artifact_type': content_type
                        })
                else:
                    # Raw content extraction failed
                    error_msg = f"Failed to extract {content_type} content from CrewAI result"
                    logger.error(f"Job {job_id}: {error_msg}")
                    print(f"[RAILWAY_DEBUG] Job {job_id}: ERROR - {error_msg}, raw_content length={len(raw_content) if raw_content else 0}", file=sys.stdout, flush=True)
                    sse_store.add_event(job_id, 'error', {
                        'job_id': job_id,
                        'message': error_msg,
                        'error_type': 'extraction_failed',
                        'artifact_type': content_type,
                        'hint': f'Check backend logs for {content_type} extraction details. The CrewAI result may not contain the expected content.'
                    })
        
        # Update job status to completed - commit immediately with retry logic
        max_completion_retries = 3
        completion_retry_delay = 0.5
        completion_updated = False
        for completion_retry in range(max_completion_retries):
            try:
                content_service.update_job_status(
                    job_id,
                    JobStatus.COMPLETED.value,
                    finished_at=datetime.utcnow()
                )
                session.commit()
                completion_updated = True
                break  # Success - exit retry loop
            except (OperationalError, DisconnectionError) as commit_error:
                logger.warning(f"[COMPLETION_RETRY] Job {job_id}: Failed to commit job completion on attempt {completion_retry + 1}/{max_completion_retries}: {commit_error}")
                session.rollback()
                if completion_retry < max_completion_retries - 1:
                    await asyncio.sleep(completion_retry_delay)
                    completion_retry_delay *= 2  # Exponential backoff
                    # Refresh session and user for retry
                    try:
                        session.close()
                    except:
                        pass
                    session = SessionLocal()
                    user = session.query(User).filter(User.id == user_id).first()
                    if not user:
                        logger.error(f"User {user_id} not found during completion retry")
                        session.close()
                        break  # Continue anyway - we'll still send completion event
                    content_service = ContentService(session, user)
                    continue
                else:
                    # All retries exhausted - log but continue (we'll still send completion event)
                    logger.error(f"Job {job_id}: Failed to update job status after {max_completion_retries} retries: {commit_error}", exc_info=True)
                    break
            except Exception as commit_error:
                # Non-connection error - log but continue (we'll still send completion event)
                logger.error(f"Job {job_id}: Failed to commit job completion: {commit_error}", exc_info=True)
                session.rollback()
                break
        
        # Get all artifacts for completion event - use retry logic for connection errors
        artifacts = []
        max_artifacts_retries = 3
        artifacts_retry_delay = 0.5
        for artifacts_retry in range(max_artifacts_retries):
            try:
                artifacts = session.query(ContentArtifact).filter(ContentArtifact.job_id == job_id).all()
                break  # Success - exit retry loop
            except (OperationalError, DisconnectionError) as query_error:
                logger.warning(f"[ARTIFACTS_QUERY_RETRY] Job {job_id}: Failed to query artifacts on attempt {artifacts_retry + 1}/{max_artifacts_retries}: {query_error}")
                if artifacts_retry < max_artifacts_retries - 1:
                    await asyncio.sleep(artifacts_retry_delay)
                    artifacts_retry_delay *= 2  # Exponential backoff
                    # Use new session for retry
                    try:
                        session.close()
                    except:
                        pass
                    session = SessionLocal()
                    continue
                else:
                    # All retries exhausted - use empty list
                    logger.error(f"Job {job_id}: Failed to query artifacts after {max_artifacts_retries} retries: {query_error}")
                    artifacts = []
                    break
            except Exception as query_error:
                # Non-connection error - use empty list
                logger.warning(f"Job {job_id}: Failed to query artifacts: {query_error}")
                artifacts = []
                break
        artifact_content = {}
        for artifact in artifacts:
            if artifact.content_text:
                if artifact.type == 'blog':
                    artifact_content['content'] = artifact.content_text
                elif artifact.type == 'social':
                    artifact_content['social_media_content'] = artifact.content_text
                elif artifact.type == 'audio':
                    artifact_content['audio_content'] = artifact.content_text
                elif artifact.type == 'video':
                    artifact_content['video_content'] = artifact.content_text
        
        # Send completion event with all content
        sse_store.add_event(job_id, 'complete', {
            'job_id': job_id,
            'status': JobStatus.COMPLETED.value,
            'message': 'Content generation completed successfully',
            **artifact_content  # Include all artifact content
        })
        
        # Increment usage
        for content_type in content_types:
            policy.increment_usage(content_type)
        
        total_duration = time.time() - llm_start_time
        logger.info(f"[JOB_COMPLETE] Job {job_id}: Completed successfully in {total_duration:.2f}s")
        logger.info(f"[JOB_COMPLETE] Job {job_id}: Summary - model={model_name}, topic='{topic}', content_types={content_types}")
        
        # Track job success metric
        try:
            from .services.metrics import increment_counter
            increment_counter("jobs_total", labels={"status": "completed", "plan": plan})
        except ImportError:
            pass
        
    except (TimeoutError, asyncio.TimeoutError) as e:
        error_msg = str(e) if str(e) else f"Content generation timed out after {timeout_seconds} seconds"
        total_duration = time.time() - llm_start_time if 'llm_start_time' in locals() else 0
        logger.error(f"[JOB_FAILED] Job {job_id}: TIMEOUT after {total_duration:.2f}s (limit: {timeout_seconds}s): {error_msg}", exc_info=True)
        logger.error(f"[JOB_FAILED] Job {job_id}: Timeout details - model={model_name if 'model_name' in locals() else 'unknown'}, topic='{topic if 'topic' in locals() else 'unknown'}'")
        if session:
            try:
                # Refresh session if needed
                session.rollback()
                user = session.query(User).filter(User.id == user_id).first()
                if user:
                    content_service = ContentService(session, user)
                    content_service.update_job_status(
                        job_id,
                        JobStatus.FAILED.value,
                        finished_at=datetime.utcnow()
                    )
                    sse_store.add_event(job_id, 'error', {
                        'job_id': job_id,
                        'message': error_msg,
                        'error_type': 'timeout'
                    })
                    
                    # Track job failure metric
                    try:
                        from .services.metrics import increment_counter
                        increment_counter("job_failures_total", labels={"error_type": "timeout", "plan": plan})
                    except ImportError:
                        pass
            except Exception as update_error:
                logger.error(f"Failed to update job status after timeout: {update_error}")
    except Exception as e:
        error_type = type(e).__name__
        error_msg_raw = str(e) if str(e) else f"{error_type} occurred"
        total_duration = time.time() - llm_start_time if 'llm_start_time' in locals() else 0
        
        # Check if this is a database connection error
        is_db_error = (
            'OperationalError' in error_type or 
            'psycopg2' in error_msg_raw.lower() or 
            'connection' in error_msg_raw.lower() and ('reset' in error_msg_raw.lower() or 'closed' in error_msg_raw.lower() or 'lost' in error_msg_raw.lower())
        )
        
        # Build detailed error message with hints based on error content
        if is_db_error:
            error_msg = f"Database connection error: {error_msg_raw}"
            hint = "Database connection was lost during generation. The job may have completed but failed to save. Please try again."
        elif 'OPENAI_API_KEY' in error_msg_raw or 'api key' in error_msg_raw.lower() or 'authentication' in error_msg_raw.lower():
            error_msg = f"LLM authentication failed: {error_msg_raw}"
            hint = "Set OPENAI_API_KEY in Railway backend service variables (not frontend .env). Get your key from https://platform.openai.com/api-keys"
        elif 'Ollama' in error_msg_raw or 'ollama' in error_msg_raw.lower() or ('connection' in error_msg_raw.lower() and 'ollama' in error_msg_raw.lower()):
            error_msg = f"Ollama connection error: {error_msg_raw}"
            hint = "Ensure Ollama is running and accessible, or set OPENAI_API_KEY to use OpenAI instead"
        elif 'timeout' in error_msg_raw.lower():
            error_msg = f"Content generation timeout: {error_msg_raw}"
            hint = f"Generation exceeded {timeout_seconds}s limit. Try a simpler topic or check LLM service availability."
        elif 'configuration' in error_msg_raw.lower() or 'not configured' in error_msg_raw.lower():
            error_msg = f"Configuration error: {error_msg_raw}"
            hint = "Check backend environment variables. Ensure OPENAI_API_KEY is set in Railway backend service variables."
        elif 'ValueError' in error_type and ('required' in error_msg_raw.lower() or 'missing' in error_msg_raw.lower()):
            error_msg = f"Missing configuration: {error_msg_raw}"
            hint = "Verify all required environment variables are set in Railway backend service variables"
        else:
            error_msg = f"Content generation failed: {error_msg_raw}"
            hint = "Check backend logs for detailed error information. Common causes: missing OPENAI_API_KEY, LLM service unavailable, or network issues."
        
        logger.error(f"[JOB_FAILED] Job {job_id}: FAILED after {total_duration:.2f}s: {error_msg}", exc_info=True)
        logger.error(f"[JOB_FAILED] Job {job_id}: Error details - model={model_name if 'model_name' in locals() else 'unknown'}, topic='{topic if 'topic' in locals() else 'unknown'}', error_type={error_type}")
        logger.error(f"[JOB_FAILED] Job {job_id}: Hint for user: {hint}")
        
        # Try to update job status with error handling for database connection issues
        if session:
            try:
                # Try to refresh session - if connection is broken, this will fail
                session.rollback()
                # Test if session is still valid by querying user
                user = session.query(User).filter(User.id == user_id).first()
                if user:
                    content_service = ContentService(session, user)
                    content_service.update_job_status(
                        job_id,
                        JobStatus.FAILED.value,
                        finished_at=datetime.utcnow()
                    )
                    session.commit()
                    sse_store.add_event(job_id, 'error', {
                        'job_id': job_id,
                        'message': error_msg,
                        'error_type': error_type,
                        'hint': hint
                    })
                else:
                    # User not found - session might be stale, create new session
                    raise Exception("Session stale - user not found")
            except Exception as update_error:
                # Session is broken - create a new one
                logger.warning(f"Job {job_id}: Failed to update job status with existing session: {update_error}. Creating new session...")
                try:
                    # Close broken session
                    if session:
                        try:
                            session.close()
                        except:
                            pass
                    
                    # Create new session for error update
                    error_session = SessionLocal()
                    try:
                        error_user = error_session.query(User).filter(User.id == user_id).first()
                        if error_user:
                            error_content_service = ContentService(error_session, error_user)
                            error_content_service.update_job_status(
                                job_id,
                                JobStatus.FAILED.value,
                                finished_at=datetime.utcnow()
                            )
                            error_session.commit()
                            sse_store.add_event(job_id, 'error', {
                                'job_id': job_id,
                                'message': error_msg,
                                'error_type': error_type,
                                'hint': hint
                            })
                            logger.info(f"Job {job_id}: Successfully updated job status with new session")
                        else:
                            logger.error(f"Job {job_id}: User {user_id} not found even with new session")
                            # Still send error event even if we can't update DB
                            sse_store.add_event(job_id, 'error', {
                                'job_id': job_id,
                                'message': error_msg,
                                'error_type': error_type,
                                'hint': hint
                            })
                    finally:
                        error_session.close()
                except Exception as new_session_error:
                    logger.error(f"Job {job_id}: Failed to update job status even with new session: {new_session_error}", exc_info=True)
                    # Last resort - just send error event without DB update
                    sse_store.add_event(job_id, 'error', {
                        'job_id': job_id,
                        'message': error_msg,
                        'error_type': error_type,
                        'hint': hint
                    })
        else:
            # No session available - just send error event
            sse_store.add_event(job_id, 'error', {
                'job_id': job_id,
                'message': error_msg,
                'error_type': error_type,
                'hint': hint
            })
        
        # Track job failure metric (regardless of session status)
        try:
            from .services.metrics import increment_counter
            increment_counter("job_failures_total", labels={"error_type": error_type, "plan": plan if 'plan' in locals() else 'unknown'})
        except ImportError:
            pass
    finally:
        if session:
            try:
                session.close()
            except Exception as close_error:
                logger.warning(f"Error closing session for job {job_id}: {close_error}")


class VoiceoverRequest(BaseModel):
    """Request model for voiceover generation"""
    job_id: Optional[int] = Field(None, description="Job ID to use audio_script from")
    narration_text: Optional[str] = Field(None, description="Narration text (if not using job_id)", max_length=10000)
    voice_id: str = Field(default="default", description="Voice identifier")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speech speed multiplier")
    format: str = Field(default="wav", description="Output format")


@router.post(
    "/voiceover",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate voiceover (TTS)",
    description="""
    Create a voiceover (TTS) for a job's audio script or provided narration text.
    
    Creates a `voiceover_audio` artifact linked to the job and streams progress via SSE.
    
    **Input Options:**
    - `job_id`: Use audio script from existing job
    - `narration_text`: Provide narration text directly
    
    **Progress Events:**
    - `tts_started`: TTS generation started
    - `tts_progress`: Progress updates
    - `artifact_ready`: Voiceover audio ready
    - `tts_completed`: TTS generation completed
    - `tts_failed`: TTS generation failed
    """,
    tags=["content"]
)
async def create_voiceover(
    request: VoiceoverRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a voiceover (TTS) for a job's audio script or provided narration text
    
    Creates a voiceover_audio artifact linked to the job and streams progress via SSE.
    
    Args:
        request: Voiceover request (job_id OR narration_text required)
    
    Returns:
        Job ID and voiceover task info
    
    Raises:
        HTTPException: If plan limit exceeded or feature not available
    """
    try:
        logger.info(f"[VOICEOVER_ENDPOINT] Starting voiceover request for user {current_user.id}, job_id: {request.job_id}, has_narration_text: {bool(request.narration_text)}")
        print(f"[RAILWAY_DEBUG] [VOICEOVER_ENDPOINT] Starting voiceover request", file=sys.stdout, flush=True)
        sys.stdout.flush()
        
        # Check if user can generate voiceover
        logger.info(f"[VOICEOVER_ENDPOINT] Checking plan limits for user {current_user.id}")
        plan_policy = PlanPolicy(db, current_user)
        plan_policy.enforce_media_generation_limit('voiceover_audio')
        logger.info(f"[VOICEOVER_ENDPOINT] Plan limits check passed for user {current_user.id}")
        
        content_service = ContentService(db, current_user)
        sse_store = get_sse_store()
        
        # Determine narration text source
        narration_text = None
        job_id = request.job_id
    
        if job_id:
            # Get job and find audio_script artifact
            job = content_service.get_job(job_id)
            if not job:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Job not found"
                )
            
            # Find audio_script artifact
            audio_script_artifact = None
            for artifact in job.artifacts:
                if artifact.type == 'audio':
                    audio_script_artifact = artifact
                    break
            
            if not audio_script_artifact or not audio_script_artifact.content_text:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Job does not have an audio script. Generate audio content first or provide narration_text."
                )
            
            narration_text = audio_script_artifact.content_text
            logger.info(f"Using audio script from job {job_id} for voiceover")
        
        elif request.narration_text:
            narration_text = request.narration_text.strip()
            if not narration_text:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="narration_text cannot be empty"
                )
            
            # Moderate input (before generation)
            if config.ENABLE_CONTENT_MODERATION:
                from .services.moderation_service import get_moderation_service
                moderation_service = get_moderation_service()
                moderation_result = moderation_service.moderate_input(
                    narration_text,
                    context={"user_id": current_user.id, "type": "voiceover"}
                )
                
                if not moderation_result.passed:
                    from .exceptions import ErrorResponse
                    from .logging_config import get_request_id
                    
                    error_response = ErrorResponse.create(
                        message=f"Content moderation failed: {moderation_result.reason_code.value if moderation_result.reason_code else 'unknown'}",
                        code="CONTENT_BLOCKED",
                        status_code=status.HTTP_403_FORBIDDEN,
                        request_id=get_request_id(),
                        details={
                            "reason_code": moderation_result.reason_code.value if moderation_result.reason_code else None,
                            **moderation_result.details
                        }
                    )
                    
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=error_response
                    )
            
            # Create a new job for standalone voiceover
            # This allows tracking voiceover as a separate job
            job = content_service.create_job(
                topic=f"Voiceover: {narration_text[:50]}...",
                content_types=['audio'],
                idempotency_key=None
            )
            job_id = job.id
            logger.info(f"Created new job {job_id} for standalone voiceover")
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either job_id or narration_text must be provided"
            )
        
        # Start voiceover generation asynchronously
        logger.info(f"Creating async task for voiceover generation, job_id: {job_id}, text_length: {len(narration_text) if narration_text else 0}")
        
        # Wrap the async function to ensure it runs and logs errors
        async def run_voiceover_with_error_handling():
            """Wrapper to ensure async voiceover task errors are logged and handled"""
            try:
                # Force immediate output for Railway visibility
                print(f"[RAILWAY_DEBUG] [VOICEOVER_TASK] Task wrapper started for job {job_id}", file=sys.stdout, flush=True)
                sys.stdout.flush()
                sys.stderr.flush()
                logger.info(f"[VOICEOVER_TASK] Task wrapper started for job {job_id}")
                
                await _generate_voiceover_async(
                    job_id=job_id,
                    narration_text=narration_text,
                    voice_id=request.voice_id,
                    speed=request.speed,
                    format=request.format,
                    user_id=current_user.id
                )
                
                print(f"[RAILWAY_DEBUG] [VOICEOVER_TASK] Task wrapper completed successfully for job {job_id}", file=sys.stdout, flush=True)
                sys.stdout.flush()
                logger.info(f"[VOICEOVER_TASK] Task wrapper completed successfully for job {job_id}")
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e) if str(e) else f"{error_type} occurred"
                
                print(f"[RAILWAY_DEBUG] [VOICEOVER_TASK] Task wrapper caught exception for job {job_id}: {error_type} - {error_msg}", file=sys.stderr, flush=True)
                sys.stdout.flush()
                sys.stderr.flush()
                logger.error(f"[VOICEOVER_TASK] Task wrapper caught exception for job {job_id}: {error_type} - {error_msg}", exc_info=True)
                
                # Send error event to SSE store
                try:
                    error_sse_store = get_sse_store()
                    error_sse_store.add_event(
                        job_id,
                        'tts_failed',
                        {
                            'job_id': job_id,
                            'message': f'Voiceover generation failed: {error_msg}',
                            'error_type': error_type
                        }
                    )
                    logger.info(f"[VOICEOVER_TASK] Error event sent to SSE store for job {job_id}")
                except Exception as sse_error:
                    logger.error(f"[VOICEOVER_TASK] Failed to send error event to SSE store: {sse_error}", exc_info=True)
        
        # Create the task with error handling
        print(f"[RAILWAY_DEBUG] Creating async task for voiceover generation, job_id: {job_id}", file=sys.stdout, flush=True)
        sys.stdout.flush()
        
        try:
            # Use the module-level asyncio import (imported at top of file)
            async_task = asyncio.create_task(run_voiceover_with_error_handling())
            task_state = async_task.done()
            logger.info(f"Async task created for voiceover generation, job_id: {job_id}, task: {async_task}, done: {task_state}")
            print(f"[RAILWAY_DEBUG] Async task created for voiceover generation, job_id: {job_id}, done: {task_state}", file=sys.stdout, flush=True)
            sys.stdout.flush()
        except Exception as task_error:
            error_msg = f"Failed to create async task for voiceover generation: {str(task_error)}"
            logger.error(error_msg, exc_info=True)
            print(f"[RAILWAY_DEBUG] Failed to create async task: {task_error}", file=sys.stderr, flush=True)
            sys.stderr.flush()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
        
        logger.info(f"[VOICEOVER_ENDPOINT] Returning success response, job_id: {job_id}")
        print(f"[RAILWAY_DEBUG] [VOICEOVER_ENDPOINT] Returning success response, job_id: {job_id}", file=sys.stdout, flush=True)
        sys.stdout.flush()
        
        return {
            "job_id": job_id,
            "status": "processing",
            "message": "Voiceover generation started"
        }
    except HTTPException:
        # Re-raise HTTP exceptions (they're already properly formatted)
        raise
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e) if str(e) else f"{error_type} occurred"
        logger.error(f"[VOICEOVER_ENDPOINT] Unexpected error in voiceover endpoint: {error_type} - {error_msg}", exc_info=True)
        print(f"[RAILWAY_DEBUG] [VOICEOVER_ENDPOINT] Unexpected error: {error_type} - {error_msg}", file=sys.stderr, flush=True)
        sys.stderr.flush()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start voiceover generation: {error_msg}"
        )


async def _generate_voiceover_async(
    job_id: int,
    narration_text: str,
    voice_id: str,
    speed: float,
    format: str,
    user_id: int
):
    """
    Generate voiceover asynchronously
    
    Args:
        job_id: Job ID
        narration_text: Text to synthesize
        voice_id: Voice identifier
        speed: Speech speed
        format: Output format
        user_id: User ID for database session
    """
    import time
    from .database import get_db, ContentArtifact, User
    from .services.plan_policy import PlanPolicy
    
    # Force immediate output for Railway visibility
    print(f"[RAILWAY_DEBUG] [VOICEOVER_ASYNC] Starting voiceover generation for job {job_id}, user {user_id}", file=sys.stdout, flush=True)
    sys.stdout.flush()
    logger.info(f"[VOICEOVER_ASYNC] Starting voiceover generation for job {job_id}, user {user_id}")
    logger.info(f"[VOICEOVER_ASYNC] Parameters: voice_id={voice_id}, speed={speed}, format={format}, text_length={len(narration_text) if narration_text else 0}")
    
    # Get database session - use SessionLocal directly for async tasks
    from .database import SessionLocal
    db = None
    try:
        db = SessionLocal()
        print(f"[RAILWAY_DEBUG] [VOICEOVER_ASYNC] Database session obtained for job {job_id}", file=sys.stdout, flush=True)
        sys.stdout.flush()
        logger.info(f"[VOICEOVER_ASYNC] Database session obtained for job {job_id}")
    except Exception as db_error:
        print(f"[RAILWAY_DEBUG] [VOICEOVER_ASYNC] Failed to get database session: {db_error}", file=sys.stderr, flush=True)
        sys.stderr.flush()
        logger.error(f"[VOICEOVER_ASYNC] Failed to get database session for job {job_id}: {db_error}", exc_info=True)
        raise
    
    sse_store = get_sse_store()
    
    try:
        print(f"[RAILWAY_DEBUG] [VOICEOVER_ASYNC] About to send tts_started event for job {job_id}", file=sys.stdout, flush=True)
        sys.stdout.flush()
        logger.info(f"[VOICEOVER_ASYNC] About to send tts_started event for job {job_id}")
        print(f"[RAILWAY_DEBUG] [VOICEOVER_ASYNC] About to send tts_started event for job {job_id}", file=sys.stdout, flush=True)
        sys.stdout.flush()
        
        # Send TTS started event
        try:
            sse_store.add_event(
                job_id,
                'tts_started',
                {
                    'job_id': job_id,
                    'voice_id': voice_id,
                    'text_length': len(narration_text)
                }
            )
            logger.info(f"[VOICEOVER_ASYNC] tts_started event sent successfully for job {job_id}")
            print(f"[RAILWAY_DEBUG] [VOICEOVER_ASYNC] tts_started event sent successfully for job {job_id}", file=sys.stdout, flush=True)
            sys.stdout.flush()
        except Exception as sse_error:
            logger.error(f"[VOICEOVER_ASYNC] Failed to send tts_started event: {sse_error}", exc_info=True)
            print(f"[RAILWAY_DEBUG] [VOICEOVER_ASYNC] Failed to send tts_started event: {sse_error}", file=sys.stderr, flush=True)
            sys.stderr.flush()
            raise
        
        logger.info(f"Starting TTS generation for job {job_id}, voice: {voice_id}, text length: {len(narration_text)}")
        print(f"[RAILWAY_DEBUG] [VOICEOVER_ASYNC] Starting TTS generation for job {job_id}, voice: {voice_id}, text length: {len(narration_text)}", file=sys.stdout, flush=True)
        sys.stdout.flush()
        
        # Get TTS provider
        logger.info(f"[VOICEOVER_ASYNC] Getting TTS provider...")
        print(f"[RAILWAY_DEBUG] [VOICEOVER_ASYNC] Getting TTS provider...", file=sys.stdout, flush=True)
        sys.stdout.flush()
        
        try:
            tts_provider = get_tts_provider()
            logger.info(f"[VOICEOVER_ASYNC] TTS provider obtained: {type(tts_provider).__name__}")
            print(f"[RAILWAY_DEBUG] [VOICEOVER_ASYNC] TTS provider obtained: {type(tts_provider).__name__}", file=sys.stdout, flush=True)
            sys.stdout.flush()
        except Exception as tts_provider_error:
            logger.error(f"[VOICEOVER_ASYNC] Failed to get TTS provider: {tts_provider_error}", exc_info=True)
            print(f"[RAILWAY_DEBUG] [VOICEOVER_ASYNC] Failed to get TTS provider: {tts_provider_error}", file=sys.stderr, flush=True)
            sys.stderr.flush()
            raise
        
        logger.info(f"[VOICEOVER_ASYNC] Checking TTS provider availability...")
        is_available = tts_provider.is_available()
        logger.info(f"[VOICEOVER_ASYNC] TTS provider available: {is_available}")
        
        if not is_available:
            provider_name = type(tts_provider).__name__
            error_msg = (
                f"TTS provider ({provider_name}) is not available. "
                f"To enable voiceover generation, install Piper TTS:\n"
                f"1. Install piper-tts Python package: pip install piper-tts\n"
                f"2. Or install piper binary and set PIPER_BINARY environment variable\n"
                f"3. Download Piper voice models and set PIPER_MODEL_PATH environment variable"
            )
            logger.error(f"[VOICEOVER_ASYNC] {error_msg}")
            print(f"[RAILWAY_DEBUG] [VOICEOVER_ASYNC] {error_msg}", file=sys.stderr, flush=True)
            sys.stderr.flush()
            # Raise RuntimeError - will be caught by exception handler and sent as SSE event
            raise RuntimeError(error_msg)
        
        logger.info(f"[VOICEOVER_ASYNC] TTS provider is available, proceeding with synthesis")
        
        # Send progress event
        sse_store.add_event(
            job_id,
            'tts_progress',
            {
                'job_id': job_id,
                'message': 'Synthesizing speech...',
                'progress': 25
            }
        )
        
        # Synthesize speech with metrics (M7)
        from .services.metrics import TTSMetrics
        provider_name = type(tts_provider).__name__.replace("Provider", "").lower()
        
        tts_start_time = time.time()
        tts_success = False
        try:
            logger.info(f"[VOICEOVER_ASYNC] About to call synthesize for job {job_id}, voice_id: {voice_id}")
            print(f"[RAILWAY_DEBUG] [VOICEOVER_ASYNC] About to call synthesize for job {job_id}, voice_id: {voice_id}", file=sys.stdout, flush=True)
            print(f"[RAILWAY_DEBUG] [VOICEOVER_ASYNC] TTS provider type: {type(tts_provider).__name__}", file=sys.stdout, flush=True)
            
            audio_bytes, metadata = tts_provider.synthesize(
                text=narration_text,
                voice_id=voice_id,
                speed=speed,
                format=format
            )
            tts_success = True
            logger.info(f"[VOICEOVER_ASYNC] TTS synthesis complete for job {job_id}, duration: {metadata.get('duration_sec')}s, audio size: {len(audio_bytes)} bytes")
            print(f"[RAILWAY_DEBUG] [VOICEOVER_ASYNC] TTS synthesis complete, audio size: {len(audio_bytes)} bytes", file=sys.stdout, flush=True)
        except FileNotFoundError as e:
            tts_success = False
            error_msg = f"TTS model file not found: {str(e)}. Please ensure Piper TTS models are installed or downloadable."
            logger.error(f"[VOICEOVER_ASYNC] FileNotFoundError during synthesis: {error_msg}", exc_info=True)
            print(f"[RAILWAY_DEBUG] [VOICEOVER_ASYNC] FileNotFoundError: {error_msg}", file=sys.stderr, flush=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=error_msg
            )
        except Exception as synth_error:
            tts_success = False
            error_type = type(synth_error).__name__
            error_msg = f"TTS synthesis failed: {error_type}: {str(synth_error)}"
            logger.error(f"[VOICEOVER_ASYNC] Exception during synthesis: {error_msg}", exc_info=True)
            print(f"[RAILWAY_DEBUG] [VOICEOVER_ASYNC] Exception traceback:", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
        finally:
            tts_duration = time.time() - tts_start_time
            TTSMetrics.record_synthesis(provider_name, tts_duration, success=tts_success)
        
        # Send progress event
        sse_store.add_event(
            job_id,
            'tts_progress',
            {
                'job_id': job_id,
                'message': 'Saving audio file...',
                'progress': 75
            }
        )
        
        # Store audio file
        storage = get_storage_provider()
        storage_key = storage.generate_key('voiceovers', f'.{format}')
        # Store audio with metrics (M7)
        from .services.metrics import StorageMetrics
        try:
            # Store the file - put() returns relative path, we'll use get_url() for the URL
            storage.put(storage_key, audio_bytes, content_type=f'audio/{format}')
            StorageMetrics.record_put("voiceover", len(audio_bytes), success=True)
            logger.info(f"Audio file stored: {storage_key} for job {job_id}")
        except Exception as e:
            StorageMetrics.record_put("voiceover", len(audio_bytes), success=False)
            raise
        
        # Get the public URL for the stored file (matches FastAPI static mount)
        storage_url = storage.get_url(storage_key)
        logger.info(f"Generated storage URL: {storage_url} for storage_key: {storage_key}")
        
        # Moderate output before saving artifact
        if config.ENABLE_CONTENT_MODERATION:
            from .services.moderation_service import get_moderation_service
            moderation_service = get_moderation_service()
            moderation_result = moderation_service.moderate_output(
                narration_text,
                'voiceover_audio',
                context={"job_id": job_id, "user_id": user_id}
            )
            
            if not moderation_result.passed:
                # Send moderation blocked event
                sse_store.add_event(job_id, 'moderation_blocked', {
                    'job_id': job_id,
                    'artifact_type': 'voiceover_audio',
                    'reason_code': moderation_result.reason_code.value if moderation_result.reason_code else None,
                    'details': moderation_result.details
                })
                logger.warning(f"Job {job_id}: Voiceover content blocked by moderation: {moderation_result.reason_code}")
                # Skip creating artifact for blocked content
                raise RuntimeError(f"Content blocked by moderation: {moderation_result.reason_code}")
            else:
                # Send moderation passed event
                sse_store.add_event(job_id, 'moderation_passed', {
                    'job_id': job_id,
                    'artifact_type': 'voiceover_audio'
                })
        
        # Create voiceover_audio artifact
        user = db.query(User).filter(User.id == user_id).first()
        content_service = ContentService(db, user)
        
        artifact_metadata = {
            'voice_id': metadata.get('voice_id', voice_id),
            'duration_sec': metadata.get('duration_sec'),
            'format': metadata.get('format', format),
            'sample_rate': metadata.get('sample_rate'),
            'text_hash': metadata.get('text_hash'),
            'storage_key': storage_key,
            'storage_url': storage_url,
            'provider': metadata.get('provider', 'piper')
        }
        
        artifact = content_service.create_artifact(
            job_id=job_id,
            artifact_type='voiceover_audio',
            content_text=narration_text[:500],  # Store first 500 chars as reference
            content_json=artifact_metadata,
            prompt_version=None,
            model_used=metadata.get('provider', 'piper')
        )
        
        # Increment voiceover usage counter
        plan_policy = PlanPolicy(db, User(id=user_id))
        plan_policy.increment_usage('voiceover_audio')
        
        # Commit transaction before closing session
        db.commit()
        
        # Track TTS job success metric
        try:
            from .services.metrics import increment_counter
            increment_counter("tts_jobs_total", labels={"status": "success", "voice_id": voice_id})
        except ImportError:
            pass
        
        logger.info(f"Created voiceover_audio artifact {artifact.id} for job {job_id}")
        
        # Send artifact ready event
        sse_store.add_event(
            job_id,
            'artifact_ready',
            {
                'job_id': job_id,
                'artifact_type': 'voiceover_audio',
                'artifact_id': artifact.id,
                'metadata': artifact_metadata
            }
        )
        
        # Send TTS completed event
        logger.info(f"[VOICEOVER_ASYNC] Sending tts_completed event for job {job_id}")
        print(f"[RAILWAY_DEBUG] [VOICEOVER_ASYNC] Sending tts_completed event for job {job_id}", file=sys.stdout, flush=True)
        sys.stdout.flush()
        
        sse_store.add_event(
            job_id,
            'tts_completed',
            {
                'job_id': job_id,
                'artifact_id': artifact.id,
                'duration_sec': metadata.get('duration_sec'),
                'storage_url': storage_url
            }
        )
        
        logger.info(f"[VOICEOVER_ASYNC] Voiceover generation completed successfully for job {job_id}")
        print(f"[RAILWAY_DEBUG] [VOICEOVER_ASYNC] Voiceover generation completed successfully for job {job_id}", file=sys.stdout, flush=True)
        sys.stdout.flush()
        
    except Exception as e:
        error_type = type(e).__name__
        error_message = f"Voiceover generation failed: {str(e)}"
        logger.error(f"Job {job_id} voiceover failed: {error_type} - {error_message}", exc_info=True)
        print(f"[RAILWAY_DEBUG] [VOICEOVER_ASYNC] Exception caught: {error_type} - {error_message}", file=sys.stderr, flush=True)
        print(f"[RAILWAY_DEBUG] [VOICEOVER_ASYNC] Exception traceback:", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        
        # Track TTS job failure metric
        try:
            from .services.metrics import increment_counter
            increment_counter("tts_jobs_total", labels={"status": "failure", "voice_id": voice_id})
        except ImportError:
            pass
        
        # Send error event
        sse_store.add_event(
            job_id,
            'tts_failed',
            {
                'job_id': job_id,
                'message': error_message,
                'error_type': type(e).__name__
            }
        )
    finally:
        if db:
            try:
                db.rollback()  # Rollback any uncommitted transactions before closing
            except Exception:
                pass  # Ignore rollback errors if session is already closed/invalid
            try:
                db.close()
            except Exception as close_error:
                logger.warning(f"Error closing database session for voiceover job {job_id}: {close_error}")


class VideoRenderRequest(BaseModel):
    """Request model for video rendering"""
    job_id: int = Field(..., description="Job ID with video_script artifact")
    resolution: Optional[Tuple[int, int]] = Field(
        default=(1920, 1080),
        description="Video resolution (width, height)"
    )
    fps: int = Field(default=30, ge=24, le=60, description="Frames per second")
    background_type: str = Field(
        default="solid",
        description="Background type: solid, placeholder, or upload"
    )
    background_color: str = Field(
        default="#000000",
        description="Background color (hex) for solid background"
    )
    background_image_path: Optional[str] = Field(
        None,
        description="Path to uploaded background image (for upload type)"
    )
    include_narration: bool = Field(
        default=True,
        description="Include narration audio from voiceover_audio artifact if available"
    )
    renderer: str = Field(
        default="baseline",
        description="Renderer: baseline (CPU) or comfyui (GPU, requires ENABLE_AI_VIDEO=true)"
    )


@router.post(
    "/video/render",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Render video",
    description="""
    Render video from a job's video script.
    
    Creates `final_video` artifact and optionally `storyboard_image`/`video_clip` artifacts.
    Streams progress via SSE.
    
    **Requirements:**
    - Job must have a `video` artifact (video script)
    - Optional: `voiceover_audio` artifact for narration
    
    **Progress Events:**
    - `video_render_started`: Video rendering started
    - `scene_started`: Scene rendering started
    - `scene_completed`: Scene rendering completed
    - `artifact_ready`: Artifact ready (storyboard_image, video_clip, final_video)
    - `video_render_completed`: Video rendering completed
    - `video_render_failed`: Video rendering failed
    """,
    tags=["content"]
)
async def render_video(
    request: VideoRenderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Render video from a job's video script
    
    Creates final_video artifact and optionally storyboard/storyboard_image/video_clip artifacts.
    Streams progress via SSE.
    
    Args:
        request: Video render request
    
    Returns:
        Job ID and render task info
    """
    content_service = ContentService(db, current_user)
    sse_store = get_sse_store()
    
    # Get job and find video_script artifact
    job = content_service.get_job(request.job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Find video_script artifact
    video_script_artifact = None
    for artifact in job.artifacts:
        if artifact.type == 'video':
            video_script_artifact = artifact
            break
    
    if not video_script_artifact or not video_script_artifact.content_json:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job does not have a video script. Generate video content first."
        )
    
    # Find voiceover_audio artifact if include_narration is True
    narration_audio_path = None
    if request.include_narration:
        for artifact in job.artifacts:
            if artifact.type == 'voiceover_audio' and artifact.content_json:
                storage_key = artifact.content_json.get('storage_key')
                if storage_key:
                    from .services.storage_provider import get_storage_provider
                    storage = get_storage_provider()
                    # Get full path to audio file
                    narration_audio_path = storage.base_path / storage_key if hasattr(storage, 'base_path') else None
                    break
    
    # Start video rendering asynchronously
    asyncio.create_task(
        _render_video_async(
            job_id=request.job_id,
            video_script_json=video_script_artifact.content_json,
            resolution=request.resolution,
            fps=request.fps,
            background_type=request.background_type,
            background_color=request.background_color,
            background_image_path=request.background_image_path,
            narration_audio_path=str(narration_audio_path) if narration_audio_path and narration_audio_path.exists() else None,
            include_narration=request.include_narration,
            renderer=request.renderer,
            user_id=current_user.id
        )
    )
    
    return {
        "job_id": request.job_id,
        "status": "processing",
        "message": "Video rendering started"
    }


async def _render_video_async(
    job_id: int,
    video_script_json: Dict[str, Any],
    resolution: Tuple[int, int],
    fps: int,
    background_type: str,
    background_color: str,
    background_image_path: Optional[str],
    narration_audio_path: Optional[str],
    include_narration: bool,
    renderer: str,
    user_id: int
):
    """
    Render video asynchronously
    
    Args:
        job_id: Job ID
        video_script_json: Video script JSON
        resolution: Video resolution
        fps: Frames per second
        background_type: Background type
        background_color: Background color
        background_image_path: Optional background image path
        narration_audio_path: Optional narration audio file path
        include_narration: Whether to include narration
        renderer: Renderer name
        user_id: User ID for database session
    """
    from .database import get_db, User
    from .services.video_provider import get_video_provider
    from typing import Tuple
    
    # Get database session - use SessionLocal directly for async tasks
    from .database import SessionLocal
    db = None
    try:
        db = SessionLocal()
    except Exception as db_error:
        logger.error(f"Failed to get database session for video render job {job_id}: {db_error}", exc_info=True)
        raise
    
    sse_store = get_sse_store()
    
    try:
        # Send video render started event
        sse_store.add_event(
            job_id,
            'video_render_started',
            {
                'job_id': job_id,
                'renderer': renderer,
                'resolution': resolution,
                'fps': fps,
                'scenes_count': len(video_script_json.get('scenes', []))
            }
        )
        
        logger.info(f"Starting video rendering for job {job_id}, renderer: {renderer}")
        
        # Get video provider
        video_provider = get_video_provider(renderer)
        
        if not video_provider.is_available():
            raise RuntimeError(f"Video provider '{renderer}' is not available")
        
        # Prepare render options
        render_options = {
            "resolution": resolution,
            "fps": fps,
            "background_type": background_type,
            "background_color": background_color,
            "background_image_path": background_image_path,
            "include_narration": include_narration,
            "narration_audio_path": narration_audio_path
        }
        
        # Render video
        scenes = video_script_json.get('scenes', [])
        for idx, scene in enumerate(scenes):
            sse_store.add_event(
                job_id,
                'scene_started',
                {
                    'job_id': job_id,
                    'scene_index': idx,
                    'scene_title': scene.get('title', f'Scene {idx + 1}')
                }
            )
        
        result = video_provider.render(video_script_json, render_options)
        
        # Process scene completion events
        for idx, scene in enumerate(scenes):
            sse_store.add_event(
                job_id,
                'scene_completed',
                {
                    'job_id': job_id,
                    'scene_index': idx,
                    'scene_title': scene.get('title', f'Scene {idx + 1}')
                }
            )
        
        # Store assets
        user = db.query(User).filter(User.id == user_id).first()
        content_service = ContentService(db, user)
        storage = get_storage_provider()
        
        # Store storyboard images if any
        for asset in result.get('assets', []):
            if asset['type'] == 'storyboard_image':
                # Read image file
                with open(asset['file_path'], 'rb') as f:
                    image_bytes = f.read()
                
                # Store image
                storage_key = storage.generate_key('storyboard_images', '.png')
                # Store with metrics (M7)
                StorageMetrics.record_put("storyboard_image", len(image_bytes), success=True)
                storage.put(storage_key, image_bytes, content_type='image/png')
                
                # Create artifact
                content_service.create_artifact(
                    job_id=job_id,
                    artifact_type='storyboard_image',
                    content_text=None,
                    content_json={
                        'storage_key': storage_key,
                        'storage_url': storage.get_url(storage_key),
                        'scene_index': asset['metadata'].get('scene_index'),
                        **asset['metadata']
                    }
                )
                
                sse_store.add_event(
                    job_id,
                    'artifact_ready',
                    {
                        'job_id': job_id,
                        'artifact_type': 'storyboard_image',
                        'scene_index': asset['metadata'].get('scene_index')
                    }
                )
            
            elif asset['type'] == 'video_clip':
                # Read clip file
                with open(asset['file_path'], 'rb') as f:
                    clip_bytes = f.read()
                
                # Store clip
                storage_key = storage.generate_key('video_clips', '.mp4')
                # Store with metrics (M7)
                StorageMetrics.record_put("video_clip", len(clip_bytes), success=True)
                storage.put(storage_key, clip_bytes, content_type='video/mp4')
                
                # Create artifact
                content_service.create_artifact(
                    job_id=job_id,
                    artifact_type='video_clip',
                    content_text=None,
                    content_json={
                        'storage_key': storage_key,
                        'storage_url': storage.get_url(storage_key),
                        **asset['metadata']
                    }
                )
                
                sse_store.add_event(
                    job_id,
                    'artifact_ready',
                    {
                        'job_id': job_id,
                        'artifact_type': 'video_clip',
                        'scene_index': asset['metadata'].get('scene_index')
                    }
                )
        
        # Store final video
        video_bytes = result['video_file']
        storage_key = storage.generate_key('videos', '.mp4')
        storage_url = storage.put(storage_key, video_bytes, content_type='video/mp4')
        
        metadata = result['metadata']
        artifact_metadata = {
            'storage_key': storage_key,
            'storage_url': storage_url,
            **metadata
        }
        
        artifact = content_service.create_artifact(
            job_id=job_id,
            artifact_type='final_video',
            content_text=None,
            content_json=artifact_metadata,
            model_used=metadata.get('renderer', 'baseline')
        )
        
        # Increment video render usage counter
        plan_policy = PlanPolicy(db, User(id=user_id))
        plan_policy.increment_usage('final_video')
        
        # Commit transaction before closing session
        db.commit()
        
        # Track video render success metric
        try:
            from .services.metrics import increment_counter
            increment_counter("video_renders_total", labels={"status": "success", "renderer": renderer})
        except ImportError:
            pass
        
        logger.info(f"Created final_video artifact {artifact.id} for job {job_id}")
        
        # Send artifact ready event
        sse_store.add_event(
            job_id,
            'artifact_ready',
            {
                'job_id': job_id,
                'artifact_type': 'final_video',
                'artifact_id': artifact.id,
                'metadata': artifact_metadata
            }
        )
        
        # Send video render completed event
        sse_store.add_event(
            job_id,
            'video_render_completed',
            {
                'job_id': job_id,
                'artifact_id': artifact.id,
                'duration_sec': metadata.get('duration_sec'),
                'resolution': metadata.get('resolution'),
                'storage_url': storage_url
            }
        )
        
    except Exception as e:
        error_message = f"Video rendering failed: {str(e)}"
        logger.error(f"Job {job_id} video rendering failed: {error_message}", exc_info=True)
        
        # Track video render failure metric
        try:
            from .services.metrics import increment_counter
            increment_counter("video_renders_total", labels={"status": "failure", "renderer": renderer})
        except ImportError:
            pass
        
        # Send error event
        sse_store.add_event(
            job_id,
            'video_render_failed',
            {
                'job_id': job_id,
                'message': error_message,
                'error_type': type(e).__name__
            }
        )
    finally:
        if db:
            try:
                db.rollback()  # Rollback any uncommitted transactions before closing
            except Exception:
                pass  # Ignore rollback errors if session is already closed/invalid
            try:
                db.close()
            except Exception as close_error:
                logger.warning(f"Error closing database session for voiceover job {job_id}: {close_error}")

