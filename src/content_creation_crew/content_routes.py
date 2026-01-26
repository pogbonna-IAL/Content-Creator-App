"""
Content generation API routes (v1)
Jobs-first persistence with SSE streaming support
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, BackgroundTasks
from fastapi import Request as FastAPIRequest
from sqlalchemy.orm import Session
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
from .schemas import PROMPT_VERSION
from .config import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/content", tags=["content"])


class GenerateRequest(BaseModel):
    """Request model for content generation"""
    topic: str = Field(..., description="Content topic", min_length=1, max_length=5000)
    content_types: Optional[List[str]] = Field(
        default=None,
        description="Content types to generate: blog, social, audio, video",
        max_items=4
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
    
    # Determine content types
    requested_content_types = request.content_types or []
    
    # Validate content type access
    valid_content_types = []
    for content_type in requested_content_types:
        if not policy.check_content_type_access(content_type):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "content_type_not_available",
                    "message": f"{content_type.capitalize()} content is not available on your current plan ({plan}).",
                    "content_type": content_type,
                    "plan": plan
                }
            )
        
        # Enforce monthly limit
        try:
            policy.enforce_monthly_limit(content_type)
            valid_content_types.append(content_type)
        except HTTPException:
            raise
    
    # Use plan defaults if no content types specified
    if not valid_content_types:
        tier_config = policy.get_tier_config()
        if tier_config:
            valid_content_types = tier_config.get('content_types', ['blog'])
        else:
            valid_content_types = ['blog']
    
    # Enforce limits for default content types
    for content_type in valid_content_types:
        try:
            policy.enforce_monthly_limit(content_type)
        except HTTPException:
            raise
    
    # Create job
    try:
        job = content_service.create_job(
            topic=topic,
            content_types=valid_content_types,
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
                error_user = error_session.query(User).filter(User.id == current_user.id).first()
                if error_user:
                    error_content_service = ContentService(error_session, error_user)
                    error_content_service.update_job_status(
                        job.id,
                        JobStatus.FAILED.value,
                        finished_at=datetime.utcnow()
                    )
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
                error_session.close()
            except Exception as update_error:
                logger.error(f"[ASYNC_TASK] Failed to update job status after error: {update_error}", exc_info=True)
                sys.stdout.flush()
                sys.stderr.flush()
    
    # Create the task with error handling
    # Add done callback to log completion/failure
    task = asyncio.create_task(run_with_error_handling())
    
    def task_done_callback(fut):
        """Callback to log task completion or failure"""
        try:
            fut.result()  # This will raise if the task failed
            logger.info(f"[ASYNC_TASK] Task for job {job.id} completed successfully")
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception as e:
            # Error already logged in run_with_error_handling, but log here too for visibility
            logger.error(f"[ASYNC_TASK] Task for job {job.id} failed in callback: {type(e).__name__}: {str(e)}")
            sys.stdout.flush()
            sys.stderr.flush()
    
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
    
    content_service = ContentService(db, current_user)
    job = content_service.get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
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
            if not last_event_id_int:
                event_data = {'type': 'job_started', 'job_id': job_id, 'status': job.status}
                event_id = sse_store.add_event(job_id, 'job_started', event_data)
                yield f"id: {event_id}\n"
                yield f"event: job_started\n"
                yield f"data: {json.dumps(event_data)}\n\n"
                flush_buffers()  # Critical: Flush immediately after initial event
                logger.info(f"[STREAM_GENERATOR] Sent initial job_started event for job {job_id}, status={job.status}")
                
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
            
            logger.info(f"[STREAM_POLL] Starting polling loop for job {job_id}, initial status={job.status}")
            
            while True:
                try:
                    poll_count += 1
                    # Refresh job from database (with error handling)
                    try:
                        db.refresh(job)
                    except Exception as db_error:
                        logger.error(f"[STREAM_ERROR] Job {job_id}: Database refresh failed: {type(db_error).__name__}: {str(db_error)}", exc_info=True)
                        # Try to get a fresh job from database
                        try:
                            fresh_job = db.query(ContentJob).filter(ContentJob.id == job_id).first()
                            if fresh_job:
                                job = fresh_job
                            else:
                                # Job not found - send error and exit
                                error_data = {'type': 'error', 'job_id': job_id, 'message': 'Job not found in database'}
                                event_id = sse_store.add_event(job_id, 'error', error_data)
                                yield f"id: {event_id}\n"
                                yield f"event: error\n"
                                yield f"data: {json.dumps(error_data)}\n\n"
                                flush_buffers()
                                logger.error(f"[STREAM_ERROR] Job {job_id}: Job not found in database")
                                break
                        except Exception as fresh_error:
                            logger.error(f"[STREAM_ERROR] Job {job_id}: Failed to get fresh job: {type(fresh_error).__name__}: {str(fresh_error)}", exc_info=True)
                            # Send error event and exit
                            error_data = {'type': 'error', 'job_id': job_id, 'message': 'Database error occurred'}
                            event_id = sse_store.add_event(job_id, 'error', error_data)
                            yield f"id: {event_id}\n"
                            yield f"event: error\n"
                            yield f"data: {json.dumps(error_data)}\n\n"
                            flush_buffers()
                            break
                    
                    # Log every 20 polls (every 10 seconds) to track progress
                    if poll_count % 20 == 0:
                        elapsed = time.time() - stream_start_time
                        try:
                            artifact_count = len(db.query(ContentArtifact).filter(ContentArtifact.job_id == job_id).all())
                        except Exception:
                            artifact_count = -1  # Error querying artifacts
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
                        last_status = job.status
                        
                        # If completed or failed, send final event and exit
                        if job.status in [JobStatus.COMPLETED.value, JobStatus.FAILED.value]:
                            elapsed = time.time() - stream_start_time
                            try:
                                artifact_count = len(db.query(ContentArtifact).filter(ContentArtifact.job_id == job_id).all())
                            except Exception:
                                artifact_count = -1
                            logger.info(f"[STREAM_COMPLETE] Job {job_id}: Status changed to {job.status} after {elapsed:.1f}s, total polls={poll_count}, artifacts={artifact_count}")
                            
                            # Send artifacts if completed
                            if job.status == JobStatus.COMPLETED.value:
                                try:
                                    artifacts = db.query(ContentArtifact).filter(
                                        ContentArtifact.job_id == job_id
                                    ).all()
                                    # Build complete event with full content from all artifacts
                                    artifact_data = {
                                        'type': 'complete',
                                        'job_id': job_id,
                                        'status': JobStatus.COMPLETED.value,
                                        'message': 'Content generation completed successfully'
                                    }
                                    
                                    # Include full content from each artifact type
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
                                    
                                    event_id = sse_store.add_event(job_id, 'complete', artifact_data)
                                    yield f"id: {event_id}\n"
                                    yield f"event: complete\n"
                                    yield f"data: {json.dumps(artifact_data)}\n\n"
                                    flush_buffers()  # Flush completion event immediately
                                    logger.info(f"[STREAM_COMPLETE] Job {job_id}: Sent complete event with content from {len(artifacts)} artifacts")
                                except Exception as artifact_error:
                                    logger.error(f"[STREAM_ERROR] Job {job_id}: Failed to get artifacts: {type(artifact_error).__name__}: {str(artifact_error)}", exc_info=True)
                            break
                    
                    # Check for new artifacts
                    try:
                        current_artifacts = db.query(ContentArtifact).filter(
                            ContentArtifact.job_id == job_id
                        ).all()
                        
                        if len(current_artifacts) > last_artifact_count:
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
                                    print(f"[RAILWAY_DEBUG] Job {job_id}: Content event yielded and flushed", file=sys.stdout, flush=True)
                                    logger.info(f"[STREAM_CONTENT] Job {job_id}: Sent content event for {artifact.type}, length={len(artifact.content_text)}")
                            
                            last_artifact_count = len(current_artifacts)
                    except Exception as artifact_query_error:
                        logger.error(f"[STREAM_ERROR] Job {job_id}: Failed to query artifacts: {type(artifact_query_error).__name__}: {str(artifact_query_error)}", exc_info=True)
                    
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
    
    # Immediate logging with flush for Railway visibility
    # Use print() for critical messages as logger might be buffered
    print(f"[RAILWAY_DEBUG] Job {job_id} started: topic='{topic}', plan='{plan}'", file=sys.stdout, flush=True)
    logger.info(f"[JOB_START] Job {job_id}: Starting content generation")
    logger.info(f"[JOB_START] Job {job_id}: Topic='{topic}', Plan='{plan}', User={user_id}")
    # Force flush after logger calls
    sys.stdout.flush()
    sys.stderr.flush()
    
    try:
        # Get fresh database session
        session = SessionLocal()
        user = session.query(User).filter(User.id == user_id).first()
        
        if not user:
            logger.error(f"User {user_id} not found for job {job_id}")
            sys.stdout.flush()
            sys.stderr.flush()
            return
        
        content_service = ContentService(session, user)
        policy = PlanPolicy(session, user)
        
        # Update job status to running
        content_service.update_job_status(
            job_id,
            JobStatus.RUNNING.value,
            started_at=datetime.utcnow()
        )
        
        # Send SSE event for job started
        sse_store.add_event(job_id, 'job_started', {
            'job_id': job_id,
            'status': JobStatus.RUNNING.value,
            'message': 'Starting content generation...'
        })
        
        # Get model name
        model_name = policy.get_model_name()
        plan = policy.get_plan()
        # Use print() for critical messages as logger might be buffered
        print(f"[RAILWAY_DEBUG] Job {job_id}: Model='{model_name}', Timeout={timeout_seconds}s, Content types={content_types}", file=sys.stdout, flush=True)
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
            
            # Mark job as completed
            content_service.update_job_status(
                job_id,
                JobStatus.COMPLETED.value,
                finished_at=datetime.utcnow()
            )
            sse_store.add_event(job_id, 'complete', {
                'job_id': job_id,
                'status': JobStatus.COMPLETED.value,
                'message': 'Content generated from cache',
                'cached': True
            })
            logger.info(f"Job {job_id}: Completed using cached content")
            return  # Skip CrewAI execution
        
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
                
                # Phase 1: Use timeout from config (180s) for faster failure detection
                # This prevents jobs from hanging while maintaining reliability
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: crew_obj.kickoff(inputs={'topic': topic})
                    ),
                    timeout=timeout_seconds  # 180 seconds from config
                )
                
                llm_exec_duration = time.time() - llm_exec_start
                llm_success = True
                executor_done = True
                print(f"[RAILWAY_DEBUG] Job {job_id}: CrewAI execution completed successfully in {llm_exec_duration:.2f}s", file=sys.stdout, flush=True)
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
        
        # Start executor task
        executor_task = asyncio.create_task(run_executor_with_progress())
        
        # Send periodic progress updates while executor is running
        progress_steps = [
            ('research', 'Researching topic...'),
            ('writing', 'Writing blog post...'),
            ('editing', 'Editing and formatting...'),
        ]
        step_index = 0
        last_progress_time = time.time()
        
        try:
            while not executor_done:
                # Wait for either executor completion or 10 seconds (whichever comes first)
                done, pending = await asyncio.wait(
                    [executor_task],
                    timeout=10.0,
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                if done:
                    # Executor completed
                    print(f"[RAILWAY_DEBUG] Job {job_id}: Executor task completed, breaking from wait loop", file=sys.stdout, flush=True)
                    break
                else:
                    # Timeout - executor still running, send progress update
                    elapsed = time.time() - last_progress_time
                    if elapsed >= 10.0 and step_index < len(progress_steps):
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
            await executor_task
            print(f"[RAILWAY_DEBUG] Job {job_id}: Executor task awaited, checking for errors...", file=sys.stdout, flush=True)
            
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
        sse_store.add_event(job_id, 'agent_progress', {
            'job_id': job_id,
            'message': 'Extracting and validating content...',
            'step': 'extraction'
        })
        
        # Extract and validate content
        print(f"[RAILWAY_DEBUG] Job {job_id}: Starting content extraction from CrewAI result, result type={type(result)}", file=sys.stdout, flush=True)
        logger.info(f"[EXTRACTION] Job {job_id}: Starting content extraction from CrewAI result")
        extraction_start = time.time()
        raw_content = await api_server_module.extract_content_async(result, topic, logger)
        extraction_duration = time.time() - extraction_start
        print(f"[RAILWAY_DEBUG] Job {job_id}: Content extraction completed, length={len(raw_content) if raw_content else 0}", file=sys.stdout, flush=True)
        logger.info(f"[EXTRACTION] Job {job_id}: Content extraction completed in {extraction_duration:.2f}s, content length={len(raw_content) if raw_content else 0}")
        
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
            # Moderate output before saving artifact
            if config.ENABLE_CONTENT_MODERATION:
                logger.info(f"[MODERATION] Job {job_id}: Starting blog content moderation")
                moderation_start = time.time()
                from .services.moderation_service import get_moderation_service
                moderation_service = get_moderation_service()
                moderation_result = moderation_service.moderate_output(
                    content,
                    'blog',
                    context={"job_id": job_id, "user_id": user_id}
                )
                moderation_duration = time.time() - moderation_start
                logger.info(f"[MODERATION] Job {job_id}: Blog moderation completed in {moderation_duration:.3f}s, passed={moderation_result.passed}")
                
                if not moderation_result.passed:
                    # Send moderation blocked event
                    sse_store.add_event(job_id, 'moderation_blocked', {
                        'job_id': job_id,
                        'artifact_type': 'blog',
                        'reason_code': moderation_result.reason_code.value if moderation_result.reason_code else None,
                        'details': moderation_result.details
                    })
                    logger.warning(f"Job {job_id}: Blog content blocked by moderation: {moderation_result.reason_code}")
                    # Skip creating artifact for blocked content
                else:
                    # Send moderation passed event
                    sse_store.add_event(job_id, 'moderation_passed', {
                        'job_id': job_id,
                        'artifact_type': 'blog'
                    })
                    artifact_start = time.time()
                    content_service.create_artifact(
                        job_id,
                        'blog',
                        content,
                        content_json=validated_model.model_dump() if is_valid and validated_model else None,
                        prompt_version=PROMPT_VERSION,
                        model_used=model_name
                    )
                    artifact_duration = time.time() - artifact_start
                    # Send artifact ready event
                    print(f"[RAILWAY_DEBUG] Job {job_id}: Blog artifact created, sending SSE events", file=sys.stdout, flush=True)
                    sse_store.add_event(job_id, 'artifact_ready', {
                        'job_id': job_id,
                        'artifact_type': 'blog',
                        'message': 'Blog content generated'
                    })
                    # Send content event with the actual blog content
                    sse_store.add_event(job_id, 'content', {
                        'job_id': job_id,
                        'chunk': content,  # Send full content as a single chunk
                        'progress': 100,  # Blog is complete
                        'artifact_type': 'blog'
                    })
                    print(f"[RAILWAY_DEBUG] Job {job_id}: Blog artifact SSE events added to store, content_length={len(content)}", file=sys.stdout, flush=True)
                    logger.info(f"[ARTIFACT] Job {job_id}: Blog artifact created in {artifact_duration:.3f}s, content_length={len(content)}")
            else:
                # Moderation disabled, create artifact directly
                content_service.create_artifact(
                    job_id,
                    'blog',
                    content,
                    content_json=validated_model.model_dump() if is_valid and validated_model else None,
                    prompt_version=PROMPT_VERSION,
                    model_used=model_name
                )
                # Send artifact ready event
                sse_store.add_event(job_id, 'artifact_ready', {
                    'job_id': job_id,
                    'artifact_type': 'blog',
                    'message': 'Blog content generated'
                })
                # Send content event with the actual blog content
                sse_store.add_event(job_id, 'content', {
                    'job_id': job_id,
                    'chunk': content,  # Send full content as a single chunk
                    'progress': 100,  # Blog is complete
                    'artifact_type': 'blog'
                })
                logger.info(f"Job {job_id}: Blog artifact created")
        
        # Extract and validate other content types
        for content_type in content_types:
            if content_type == 'blog':
                continue
            
            raw_content_func = {
                'social': api_server_module.extract_social_media_content_async,
                'audio': api_server_module.extract_audio_content_async,
                'video': api_server_module.extract_video_content_async,
            }.get(content_type)
            
            if raw_content_func:
                raw_content = await raw_content_func(result, topic, logger)
                if raw_content:
                    is_valid, validated_model, validated_content, was_repaired = validate_and_repair_content(
                        content_type, raw_content, model_name, allow_repair=True
                    )
                    if not is_valid:
                        validated_content = api_server_module.clean_content(raw_content)
                    
                    if validated_content and len(validated_content.strip()) > 10:
                        # Moderate output before saving artifact
                        if config.ENABLE_CONTENT_MODERATION:
                            from .services.moderation_service import get_moderation_service
                            moderation_service = get_moderation_service()
                            moderation_result = moderation_service.moderate_output(
                                validated_content,
                                content_type,
                                context={"job_id": job_id, "user_id": user_id}
                            )
                            
                            if not moderation_result.passed:
                                # Send moderation blocked event
                                sse_store.add_event(job_id, 'moderation_blocked', {
                                    'job_id': job_id,
                                    'artifact_type': content_type,
                                    'reason_code': moderation_result.reason_code.value if moderation_result.reason_code else None,
                                    'details': moderation_result.details
                                })
                                logger.warning(f"Job {job_id}: {content_type} content blocked by moderation: {moderation_result.reason_code}")
                                # Skip creating artifact for blocked content
                            else:
                                # Send moderation passed event
                                sse_store.add_event(job_id, 'moderation_passed', {
                                    'job_id': job_id,
                                    'artifact_type': content_type
                                })
                                content_service.create_artifact(
                                    job_id,
                                    content_type,
                                    validated_content,
                                    content_json=validated_model.model_dump() if is_valid and validated_model else None,
                                    prompt_version=PROMPT_VERSION,
                                    model_used=model_name
                                )
                                # Send artifact ready event
                                sse_store.add_event(job_id, 'artifact_ready', {
                                    'job_id': job_id,
                                    'artifact_type': content_type,
                                    'message': f'{content_type.capitalize()} content generated'
                                })
                                logger.info(f"Job {job_id}: {content_type} artifact created")
                        else:
                            # Moderation disabled, create artifact directly
                            content_service.create_artifact(
                                job_id,
                                content_type,
                                validated_content,
                                content_json=validated_model.model_dump() if is_valid and validated_model else None,
                                prompt_version=PROMPT_VERSION,
                                model_used=model_name
                            )
                            # Send artifact ready event
                            sse_store.add_event(job_id, 'artifact_ready', {
                                'job_id': job_id,
                                'artifact_type': content_type,
                                'message': f'{content_type.capitalize()} content generated'
                            })
                            # Send content event with the actual content
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
                            logger.info(f"Job {job_id}: {content_type} artifact created")
        
        # Update job status to completed
        content_service.update_job_status(
            job_id,
            JobStatus.COMPLETED.value,
            finished_at=datetime.utcnow()
        )
        
        # Get all artifacts for completion event
        artifacts = session.query(ContentArtifact).filter(ContentArtifact.job_id == job_id).all()
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
        
        # Build detailed error message with hints based on error content
        if 'OPENAI_API_KEY' in error_msg_raw or 'api key' in error_msg_raw.lower() or 'authentication' in error_msg_raw.lower():
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
                        'error_type': error_type,
                        'hint': hint
                    })
                    
                    # Track job failure metric
                    try:
                        from .services.metrics import increment_counter
                        increment_counter("job_failures_total", labels={"error_type": type(e).__name__, "plan": plan})
                    except ImportError:
                        pass
            except Exception as update_error:
                logger.error(f"Failed to update job status: {update_error}")
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
    # Check if user can generate voiceover
    plan_policy = PlanPolicy(db, current_user)
    plan_policy.enforce_media_generation_limit('voiceover_audio')
    
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
    asyncio.create_task(
        _generate_voiceover_async(
            job_id=job_id,
            narration_text=narration_text,
            voice_id=request.voice_id,
            speed=request.speed,
            format=request.format,
            user_id=current_user.id
        )
    )
    
    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Voiceover generation started"
    }


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
    from .database import get_db, ContentArtifact, User
    from .services.plan_policy import PlanPolicy
    
    # Get database session
    db = next(get_db())
    sse_store = get_sse_store()
    
    try:
        # Send TTS started event
        sse_store.add_event(
            job_id,
            'tts_started',
            {
                'job_id': job_id,
                'voice_id': voice_id,
                'text_length': len(narration_text)
            }
        )
        
        logger.info(f"Starting TTS generation for job {job_id}, voice: {voice_id}, text length: {len(narration_text)}")
        
        # Get TTS provider
        tts_provider = get_tts_provider()
        
        if not tts_provider.is_available():
            raise RuntimeError("TTS provider is not available")
        
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
            audio_bytes, metadata = tts_provider.synthesize(
                text=narration_text,
                voice_id=voice_id,
                speed=speed,
                format=format
            )
            tts_success = True
            logger.info(f"TTS synthesis complete for job {job_id}, duration: {metadata.get('duration_sec')}s")
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
            storage_url = storage.put(storage_key, audio_bytes, content_type=f'audio/{format}')
            StorageMetrics.record_put("voiceover", len(audio_bytes), success=True)
            logger.info(f"Audio file stored: {storage_key} for job {job_id}")
        except Exception as e:
            StorageMetrics.record_put("voiceover", len(audio_bytes), success=False)
            raise
        
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
        
    except Exception as e:
        error_message = f"Voiceover generation failed: {str(e)}"
        logger.error(f"Job {job_id} voiceover failed: {error_message}", exc_info=True)
        
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
        db.close()


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
    
    # Get database session
    db = next(get_db())
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
        db.close()

