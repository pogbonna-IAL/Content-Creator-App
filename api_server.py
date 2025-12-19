#!/usr/bin/env python
"""
FastAPI server for Content Creation Crew
Provides REST API endpoint for the web UI
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, skip loading .env file
    pass

# Prevent LiteLLM from importing proxy modules we don't need
os.environ['LITELLM_DISABLE_PROXY'] = '1'
# Set LiteLLM timeout to 30 minutes (1800 seconds) for long-running content generation
# These must be set before importing/using LiteLLM
os.environ['LITELLM_REQUEST_TIMEOUT'] = '1800'
os.environ['LITELLM_TIMEOUT'] = '1800'
os.environ['LITELLM_CONNECTION_TIMEOUT'] = '1800'

# Also configure litellm directly if available
try:
    import litellm
    litellm.request_timeout = 1800
    litellm.timeout = 1800
    litellm.drop_params = True  # Don't drop timeout params
    
    # Configure httpx timeout for Ollama connections
    # httpx has a default timeout of 600 seconds, we need to override it
    try:
        import httpx
        # Patch httpx.Client to use extended timeout by default
        # LiteLLM creates httpx clients internally, so we need to patch the Client class
        _original_client_init = httpx.Client.__init__
        def _patched_client_init(self, *args, timeout=None, **kwargs):
            # If timeout is not provided or is <= 600 seconds (httpx default), use 1800 seconds
            if timeout is None:
                timeout = httpx.Timeout(1800.0, connect=60.0)
            elif isinstance(timeout, (int, float)):
                if timeout <= 600:
                    # Extend timeout to 1800 seconds
                    timeout = httpx.Timeout(1800.0, connect=60.0)
                else:
                    # Use provided timeout but ensure connect timeout is reasonable
                    timeout = httpx.Timeout(timeout, connect=60.0)
            elif isinstance(timeout, httpx.Timeout):
                # If it's already a Timeout object, check if read timeout is <= 600
                read_timeout = getattr(timeout, 'read', None) or getattr(timeout, 'timeout', None)
                if read_timeout is None or read_timeout <= 600:
                    # Extend timeout to 1800 seconds
                    timeout = httpx.Timeout(1800.0, connect=60.0)
            return _original_client_init(self, *args, timeout=timeout, **kwargs)
        httpx.Client.__init__ = _patched_client_init
        
        # Also patch AsyncClient for async operations
        _original_async_client_init = httpx.AsyncClient.__init__
        def _patched_async_client_init(self, *args, timeout=None, **kwargs):
            if timeout is None:
                timeout = httpx.Timeout(1800.0, connect=60.0)
            elif isinstance(timeout, (int, float)):
                if timeout <= 600:
                    timeout = httpx.Timeout(1800.0, connect=60.0)
                else:
                    timeout = httpx.Timeout(timeout, connect=60.0)
            elif isinstance(timeout, httpx.Timeout):
                read_timeout = getattr(timeout, 'read', None) or getattr(timeout, 'timeout', None)
                if read_timeout is None or read_timeout <= 600:
                    timeout = httpx.Timeout(1800.0, connect=60.0)
            return _original_async_client_init(self, *args, timeout=timeout, **kwargs)
        httpx.AsyncClient.__init__ = _patched_async_client_init
    except (ImportError, AttributeError):
        pass
except ImportError:
    pass

# Handle missing fastapi-sso gracefully
try:
    import fastapi_sso
except ImportError:
    # Create a dummy module to prevent ImportError when LiteLLM tries to import it
    import types
    fastapi_sso = types.ModuleType('fastapi_sso')
    fastapi_sso.sso = types.ModuleType('fastapi_sso.sso')
    fastapi_sso.sso.base = types.ModuleType('fastapi_sso.sso.base')
    fastapi_sso.sso.base.OpenID = type('OpenID', (), {})
    sys.modules['fastapi_sso'] = fastapi_sso
    sys.modules['fastapi_sso.sso'] = fastapi_sso.sso
    sys.modules['fastapi_sso.sso.base'] = fastapi_sso.sso.base

# Windows signal compatibility patch
if sys.platform == 'win32':
    import signal
    for sig_name, sig_value in [('SIGHUP', 1), ('SIGTSTP', 20), ('SIGCONT', 18), 
                                  ('SIGQUIT', 3), ('SIGUSR1', 10), ('SIGUSR2', 12)]:
        if not hasattr(signal, sig_name):
            setattr(signal, sig_name, sig_value)

# Import the package __init__ first to ensure its patch runs
# Ensure src directory is in Python path for Railway/Docker deployments
# PYTHONPATH should be set to /app/src:/app in Dockerfile, but add fallbacks

# Add src to Python path (relative to api_server.py)
src_path = os.path.join(os.path.dirname(__file__), "src")
if os.path.exists(src_path) and src_path not in sys.path:
    sys.path.insert(0, src_path)

# Add /app/src if we're in Docker/Railway (should already be in PYTHONPATH, but ensure it)
docker_src_path = "/app/src"
if os.path.exists(docker_src_path) and docker_src_path not in sys.path:
    sys.path.insert(0, docker_src_path)

# Import content_creation_crew package - CRITICAL: this must succeed
# The package __init__.py contains important patches that must run before other imports
import content_creation_crew  # noqa: F401

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from content_creation_crew.crew import ContentCreationCrew
from content_creation_crew.auth_routes import router as auth_router
from content_creation_crew.oauth_routes import router as oauth_router
from content_creation_crew.subscription_routes import router as subscription_router
from content_creation_crew.auth import get_current_user
from content_creation_crew.database import init_db, User, get_db, Session
from content_creation_crew.services.subscription_service import SubscriptionService
from content_creation_crew.services.content_cache import get_cache
import asyncio
import json
from typing import AsyncGenerator

# Initialize database with error handling
try:
    init_db()
except Exception as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Database initialization failed: {e}", exc_info=True)
    # Continue anyway - app might work for read-only operations
    # Database will be initialized on first request if needed

app = FastAPI(title="Content Creation Crew API")

# Enable CORS for Next.js frontend
# Allow both localhost and Docker network origins
cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://frontend:3000",  # Docker network
]
# Add environment variable override if set
if os.getenv("CORS_ORIGINS"):
    cors_origins.extend(os.getenv("CORS_ORIGINS").split(","))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication routes
app.include_router(auth_router)
app.include_router(oauth_router)
app.include_router(subscription_router)


class TopicRequest(BaseModel):
    topic: str
    content_types: list[str] = None  # Optional: ['blog', 'social', 'audio', 'video']


class ContentResponse(BaseModel):
    content: str
    topic: str
    generated_at: str


@app.get("/")
async def root():
    return {"message": "Content Creation Crew API", "status": "running"}


@app.get("/health")
async def health():
    """Health check endpoint for Railway and monitoring"""
    try:
        # Simple health check - just verify the server is running
        return {"status": "healthy", "service": "content-creation-crew"}
    except Exception as e:
        # If there's any error, return unhealthy status
        return {"status": "unhealthy", "error": str(e)}, 503


async def run_crew_async(topic: str, tier: str = 'free', content_types: list = None, use_cache: bool = True) -> AsyncGenerator[str, None]:
    """
    Run the crew asynchronously and stream progress updates
    
    Args:
        topic: Content topic
        tier: User subscription tier
        content_types: List of content types to generate
        use_cache: Whether to use content cache (default: True)
    """
    import logging
    import sys
    logger = logging.getLogger(__name__)
    
    def flush_buffers():
        """Flush stdout and stderr buffers to ensure immediate output"""
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:
            pass
    
    try:
        # Check cache first (if enabled)
        if use_cache:
            cache = get_cache()
            cached_content = cache.get(topic, content_types)
            if cached_content:
                logger.info(f"Cache hit for topic: {topic}")
                # Stream cached content immediately
                status_msg = json.dumps({'type': 'status', 'message': 'Retrieved from cache'})
                yield f"data: {status_msg}\n\n"
                flush_buffers()
                
                # Stream cached content
                completion_data = {
                    'type': 'complete',
                    'content': cached_content.get('content', ''),
                    'social_media_content': cached_content.get('social_media_content', ''),
                    'audio_content': cached_content.get('audio_content', ''),
                    'video_content': cached_content.get('video_content', ''),
                    'topic': topic,
                    'generated_at': cached_content.get('generated_at', datetime.now().isoformat()),
                    'cached': True
                }
                completion_json = json.dumps(completion_data, ensure_ascii=False)
                yield f"data: {completion_json}\n\n"
                flush_buffers()
                return
        
        # Send initial status
        status_msg = json.dumps({'type': 'status', 'message': 'Initializing crew...'})
        yield f"data: {status_msg}\n\n"
        flush_buffers()
        logger.info("Sent initial status")
        
        # Check if Ollama is accessible before starting
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:11434/api/tags")
                if response.status_code != 200:
                    raise Exception("Ollama is not responding correctly")
            logger.info("Ollama connection verified")
        except Exception as ollama_error:
            error_msg = json.dumps({
                'type': 'error',
                'message': f'Ollama is not accessible at http://localhost:11434. Please ensure Ollama is running. Error: {str(ollama_error)}',
                'error_type': 'OllamaConnectionError'
            })
            yield f"data: {error_msg}\n\n"
            flush_buffers()
            logger.error(f"Ollama connection check failed: {ollama_error}")
            return
        
        # Initialize crew with tier-appropriate configuration
        crew_instance = ContentCreationCrew(tier=tier, content_types=content_types)
        crew_obj = crew_instance._build_crew(content_types=content_types)
        status_msg = json.dumps({'type': 'status', 'message': f'Crew initialized with {tier} tier. Starting research...'})
        yield f"data: {status_msg}\n\n"
        flush_buffers()
        logger.info(f"Sent crew initialized status for tier: {tier}")
        
        # Run crew in executor to avoid blocking
        # Send periodic keep-alive messages during execution to prevent Node.js timeout
        loop = asyncio.get_event_loop()
        logger.info("Starting crew execution (this may take several minutes)...")
        
        # Send initial keep-alive
        yield ": keep-alive\n\n"
        flush_buffers()
        
        # Create a wrapper that runs executor and sends keep-alive during execution
        executor_done = False
        result = None
        executor_error = None
        
        async def run_executor():
            nonlocal executor_done, result, executor_error
            try:
                logger.info(f"Starting crew kickoff for topic: {topic}")
                result = await loop.run_in_executor(
                    None,
                    lambda: crew_obj.kickoff(inputs={'topic': topic})
                )
                logger.info("Crew kickoff completed successfully")
                executor_done = True
            except KeyboardInterrupt:
                logger.warning("Crew execution interrupted by user")
                executor_error = Exception("Content generation was interrupted")
                executor_done = True
            except Exception as e:
                logger.error(f"Crew execution failed: {type(e).__name__} - {str(e)}", exc_info=True)
                executor_error = e
                executor_done = True
        
        # Start the executor task
        executor_task = asyncio.create_task(run_executor())
        
        # Send keep-alive messages every 15 seconds while executor is running
        keep_alive_count = 0
        while not executor_done:
            # Wait for either executor completion or 15 seconds (whichever comes first)
            done, pending = await asyncio.wait(
                [executor_task],
                timeout=15.0,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            if done:
                # Executor completed
                break
            else:
                # Timeout - executor still running, send keep-alive
                keep_alive_count += 1
                yield ": keep-alive\n\n"
                flush_buffers()
                logger.debug(f"Sent keep-alive #{keep_alive_count} during crew execution")
        
        # Ensure executor completed and get result
        await executor_task
        
        if executor_error:
            raise executor_error
        
        status_msg = json.dumps({'type': 'status', 'message': 'Content generation completed. Extracting content...'})
        yield f"data: {status_msg}\n\n"
        flush_buffers()
        logger.info(f"Crew execution completed. Result type: {type(result)}")
        
        # Extract content asynchronously
        content = await extract_content_async(result, topic, logger)
        
        # If extraction failed, try one more time with longer wait
        if not content or len(content.strip()) < 10:
            logger.warning("First extraction attempt failed, waiting longer and retrying...")
            await asyncio.sleep(2)
            content = await extract_content_async(result, topic, logger)
        
        # Clean up the content
        content = clean_content(content)
        
        # Extract social media content
        social_media_content = await extract_social_media_content_async(result, topic, logger)
        social_media_content = clean_content(social_media_content) if social_media_content else ""
        
        # Extract audio content
        audio_content = await extract_audio_content_async(result, topic, logger)
        audio_content = clean_content(audio_content) if audio_content else ""
        
        # Extract video content
        video_content = await extract_video_content_async(result, topic, logger)
        video_content = clean_content(video_content) if video_content else ""
        
        if not content or len(content.strip()) < 10:
            # Last resort: try to get content from result directly
            logger.warning("Content extraction still failed, trying direct result extraction...")
            if hasattr(result, 'tasks_output') and result.tasks_output:
                last_task = result.tasks_output[-1]
                if hasattr(last_task, 'raw') and last_task.raw:
                    content = str(last_task.raw)
                elif hasattr(last_task, 'output') and last_task.output:
                    content = str(last_task.output)
                else:
                    content = str(last_task)
            
            if not content or len(content.strip()) < 10:
                content = str(result)
            
            content = clean_content(content)
        
        if not content or len(content.strip()) < 10:
            error_msg = json.dumps({
                'type': 'error', 
                'message': f'Content extraction failed - no valid content found. Content length: {len(content) if content else 0}. Check server logs for details.'
            })
            yield f"data: {error_msg}\n\n"
            logger.error(f"Content extraction failed - content too short or empty. Content: {content[:200] if content else 'None'}")
            return
        
        logger.info(f"Content extracted successfully, length: {len(content)}")
        logger.info(f"Content preview: {content[:200]}")
        
        # Stream content in chunks for real-time display
        chunk_size = 100  # characters per chunk
        total_length = len(content)
        
        logger.info(f"Starting to stream {total_length} characters in chunks of {chunk_size}")
        
        # Send content chunks with keep-alive comments to prevent timeout
        chunk_count = 0
        for i in range(0, total_length, chunk_size):
            chunk = content[i:i + chunk_size]
            progress = min(100, int((i + len(chunk)) / total_length * 100))
            chunk_data = {
                'type': 'content',
                'chunk': chunk,
                'progress': progress
            }
            sse_message = f"data: {json.dumps(chunk_data)}\n\n"
            yield sse_message
            chunk_count += 1
            
            # Flush buffers every chunk to ensure immediate delivery
            if chunk_count % 5 == 0:  # Flush every 5 chunks to balance performance
                flush_buffers()
            
            # Send keep-alive comment every 10 chunks (approximately every 0.5 seconds)
            # This prevents Node.js undici from timing out
            if chunk_count % 10 == 0:
                yield ": keep-alive\n\n"
                flush_buffers()
            
            if i % 500 == 0:  # Log every 5 chunks
                logger.debug(f"Sent chunk {chunk_count}, progress: {progress}%")
            await asyncio.sleep(0.05)  # Small delay for smooth streaming
        
        # Cache the generated content for future requests
        if use_cache:
            cache = get_cache()
            cache_data = {
                'content': content,
                'social_media_content': social_media_content,
                'audio_content': audio_content,
                'video_content': video_content,
                'generated_at': datetime.now().isoformat()
            }
            cache.set(topic, cache_data)
            logger.info(f"Cached content for topic: {topic}")
        
        # Send completion message with full content (CRITICAL - this ensures full content is delivered)
        # Ensure JSON encoding doesn't truncate large content
        completion_data = {
            'type': 'complete',
            'content': content,  # Full content - this is the source of truth
            'social_media_content': social_media_content,  # Social media content
            'audio_content': audio_content,  # Audio content
            'video_content': video_content,  # Video content
            'topic': topic,
            'generated_at': datetime.now().isoformat(),
            'total_length': len(content),  # Include length for verification
            'social_media_length': len(social_media_content) if social_media_content else 0,
            'audio_length': len(audio_content) if audio_content else 0,
            'video_length': len(video_content) if video_content else 0,
            'cached': False
        }
        
        # Use ensure_ascii=False to preserve all characters and ensure no truncation
        completion_json = json.dumps(completion_data, ensure_ascii=False)
        completion_msg = f"data: {completion_json}\n\n"
        
        logger.info(f"Sending completion message with FULL content, length: {len(content)}")
        logger.info(f"Completion JSON length: {len(completion_json)}")
        logger.info(f"Completion message content preview: {content[:300]}")
        
        # Verify the content wasn't truncated during JSON encoding
        decoded_check = json.loads(completion_json)
        if len(decoded_check.get('content', '')) != len(content):
            logger.error(f"Content truncation detected! Original: {len(content)}, Encoded: {len(decoded_check.get('content', ''))}")
        else:
            logger.info("✓ Content verified - no truncation in JSON encoding")
        
        yield completion_msg
        flush_buffers()
        
        # Send a final flush to ensure the message is sent
        yield "\n"  # Extra newline to ensure message is complete
        flush_buffers()
        
        logger.info("Streaming completed successfully - full content sent in completion message")
        
    except Exception as e:
        # Provide more detailed error information
        error_type = type(e).__name__
        error_message = str(e) if str(e) else "Unknown error occurred"
        
        # Check for common error types and provide helpful messages
        if "terminated" in error_message.lower() or error_type == "Terminated":
            error_message = "Content generation was terminated. This may be due to a timeout or connection issue. Please check if Ollama is running and try again."
        elif "connection" in error_message.lower() or "connect" in error_message.lower():
            error_message = f"Connection error: {error_message}. Please ensure Ollama is running at http://localhost:11434"
        elif "timeout" in error_message.lower():
            error_message = f"Request timeout: {error_message}. The content generation took too long. Please try with a simpler topic or check server logs."
        
        error_detail = {
            'type': 'error',
            'message': error_message,
            'error_type': error_type
        }
        
        error_msg = json.dumps(error_detail)
        logger.error(f"Error in async crew execution: {error_type} - {error_message}", exc_info=True)
        yield f"data: {error_msg}\n\n"
        flush_buffers()


def extract_content_from_result(result, task_name: str = None) -> str:
    """
    Extract content directly from CrewAI result object without file I/O.
    This is faster and more reliable than waiting for files.
    
    Args:
        result: CrewAI result object
        task_name: Optional task name to look for (e.g., 'editing_task')
        
    Returns:
        Extracted content string
    """
    content = ""
    
    # Try to extract from result object directly (fastest method)
    if hasattr(result, 'tasks_output') and result.tasks_output:
        # Look for editing task (contains main blog content)
        for task in reversed(result.tasks_output):
            # Check if this is the task we're looking for
            if task_name and hasattr(task, 'description'):
                task_desc = str(task.description).lower()
                if task_name.lower() not in task_desc:
                    continue
            
            # Try different attributes in order of preference
            if hasattr(task, 'raw') and task.raw:
                content = str(task.raw)
                if len(content.strip()) > 10:
                    return content
            elif hasattr(task, 'output') and task.output:
                content = str(task.output)
                if len(content.strip()) > 10:
                    return content
            elif hasattr(task, 'content') and task.content:
                content = str(task.content)
                if len(content.strip()) > 10:
                    return content
    
    # Fallback to result object directly
    if not content or len(content.strip()) < 10:
        if hasattr(result, 'raw') and result.raw:
            content = str(result.raw)
        elif hasattr(result, 'content') and result.content:
            content = str(result.content)
        elif hasattr(result, 'output') and result.output:
            content = str(result.output)
        else:
            content = str(result)
    
    return content


async def extract_content_async(result, topic: str, logger) -> str:
    """Extract content from result asynchronously - optimized to use result objects first"""
    content = ""
    
    # First, try extracting directly from result object (fastest, no I/O)
    logger.info("Attempting direct extraction from result object...")
    content = extract_content_from_result(result, 'editing')
    
    if content and len(content.strip()) > 10:
        logger.info(f"Successfully extracted content from result object, length: {len(content)}")
        return content
    
    # Fallback to file-based extraction (slower, but more reliable for some cases)
    logger.info("Direct extraction failed, trying file-based extraction...")
    await asyncio.sleep(1)  # Reduced wait time since we tried result first
    
    # Try reading the file multiple times
    output_file = Path("content_output.md")
    for attempt in range(5):  # Reduced attempts since we prioritize result objects
        if output_file.exists():
            try:
                file_content = output_file.read_text(encoding='utf-8')
                if file_content and len(file_content.strip()) > 10:
                    logger.info(f"File read attempt {attempt + 1}, file length: {len(file_content)}")
                    
                    # First try: look for separator
                    if "---" in file_content:
                        parts = file_content.split("---", 1)
                        if len(parts) > 1:
                            content = parts[1].strip()
                            logger.info(f"Extracted from file after separator, length: {len(content)}")
                            if len(content) > 10:
                                break
                    
                    # Second try: skip metadata lines and get actual content
                    lines = file_content.split('\n')
                    content_lines = []
                    skip_patterns = [
                        '# Content Creation:',
                        '**Generated on:**',
                        '---',
                        'I now can give a great answer',  # Common prefix
                    ]
                    
                    skip_until_content = True
                    for i, line in enumerate(lines):
                        line_stripped = line.strip()
                        
                        # Skip empty lines at the start
                        if skip_until_content and not line_stripped:
                            continue
                        
                        # Check if this is a skip pattern
                        should_skip = False
                        for pattern in skip_patterns:
                            if pattern.lower() in line_stripped.lower():
                                should_skip = True
                                skip_until_content = True
                                break
                        
                        if should_skip:
                            continue
                        
                        # Found content - start collecting
                        skip_until_content = False
                        content_lines.append(line)
                    
                    if content_lines:
                        content = '\n'.join(content_lines).strip()
                        logger.info(f"Extracted from file (skipping metadata), length: {len(content)}")
                        if len(content) > 10:
                            break
                    
                    # Fallback: use entire file if it's substantial
                    if len(file_content.strip()) > 100:
                        content = file_content.strip()
                        logger.info(f"Using entire file content, length: {len(content)}")
                        break
                        
            except Exception as e:
                logger.warning(f"Error reading file (attempt {attempt + 1}): {e}")
        await asyncio.sleep(0.5)
    
    # Final fallback: extract from result object (should have been tried first, but just in case)
    if not content or len(content.strip()) < 10:
        logger.info("File content empty or too short, using result object extraction")
        content = extract_content_from_result(result, 'editing')
    
    logger.info(f"Final extracted content length: {len(content) if content else 0}")
    if content:
        logger.info(f"Content preview: {content[:300]}")
    
    return content


async def extract_social_media_content_async(result, topic: str, logger) -> str:
    """Extract social media content from result asynchronously - optimized"""
    # First try direct extraction from result object
    content = extract_content_from_result(result, 'social')
    
    if content and len(content.strip()) > 10:
        logger.info(f"Successfully extracted social media content from result object, length: {len(content)}")
        return content
    
    # Fallback to file-based extraction
    await asyncio.sleep(1)
    
    # Try reading the social media output file
    output_file = Path("social_media_output.md")
    for attempt in range(10):
        if output_file.exists():
            try:
                file_content = output_file.read_text(encoding='utf-8')
                if file_content and len(file_content.strip()) > 10:
                    logger.info(f"Social media file read attempt {attempt + 1}, file length: {len(file_content)}")
                    
                    # First try: look for separator
                    if "---" in file_content:
                        parts = file_content.split("---", 1)
                        if len(parts) > 1:
                            content = parts[1].strip()
                            logger.info(f"Extracted social media from file after separator, length: {len(content)}")
                            if len(content) > 10:
                                break
                    
                    # Second try: skip metadata lines and get actual content
                    lines = file_content.split('\n')
                    content_lines = []
                    skip_patterns = [
                        '# Social Media',
                        '**Generated on:**',
                        '---',
                        'I now can give a great answer',
                    ]
                    
                    skip_until_content = True
                    for i, line in enumerate(lines):
                        line_stripped = line.strip()
                        
                        # Skip empty lines at the start
                        if skip_until_content and not line_stripped:
                            continue
                        
                        # Check if this is a skip pattern
                        should_skip = False
                        for pattern in skip_patterns:
                            if pattern.lower() in line_stripped.lower():
                                should_skip = True
                                skip_until_content = True
                                break
                        
                        if should_skip:
                            continue
                        
                        # Found content - start collecting
                        skip_until_content = False
                        content_lines.append(line)
                    
                    if content_lines:
                        content = '\n'.join(content_lines).strip()
                        logger.info(f"Extracted social media from file (skipping metadata), length: {len(content)}")
                        if len(content) > 10:
                            break
                    
                    # Fallback: use entire file if it's substantial
                    if len(file_content.strip()) > 50:
                        content = file_content.strip()
                        logger.info(f"Using entire social media file content, length: {len(content)}")
                        break
                        
            except Exception as e:
                logger.warning(f"Error reading social media file (attempt {attempt + 1}): {e}")
        await asyncio.sleep(0.5)
    
    # Final fallback: extract from result object
    if not content or len(content.strip()) < 10:
        logger.info("Social media file content empty, using result object extraction")
        content = extract_content_from_result(result, 'social')
    
    logger.info(f"Final extracted social media content length: {len(content) if content else 0}")
    if content:
        logger.info(f"Social media content preview: {content[:200]}")
    
    return content


async def extract_audio_content_async(result, topic: str, logger) -> str:
    """Extract audio content from result asynchronously - optimized"""
    # First try direct extraction from result object
    content = extract_content_from_result(result, 'audio')
    
    if content and len(content.strip()) > 10:
        logger.info(f"Successfully extracted audio content from result object, length: {len(content)}")
        return content
    
    # Fallback to file-based extraction
    await asyncio.sleep(1)
    
    # Try reading the audio output file
    output_file = Path("audio_output.md")
    for attempt in range(10):
        if output_file.exists():
            try:
                file_content = output_file.read_text(encoding='utf-8')
                if file_content and len(file_content.strip()) > 10:
                    logger.info(f"Audio file read attempt {attempt + 1}, file length: {len(file_content)}")
                    
                    # First try: look for separator
                    if "---" in file_content:
                        parts = file_content.split("---", 1)
                        if len(parts) > 1:
                            content = parts[1].strip()
                            logger.info(f"Extracted audio from file after separator, length: {len(content)}")
                            if len(content) > 10:
                                break
                    
                    # Second try: skip metadata lines and get actual content
                    lines = file_content.split('\n')
                    content_lines = []
                    skip_patterns = [
                        '# Audio',
                        '**Generated on:**',
                        '---',
                        'I now can give a great answer',
                    ]
                    
                    skip_until_content = True
                    for i, line in enumerate(lines):
                        line_stripped = line.strip()
                        
                        # Skip empty lines at the start
                        if skip_until_content and not line_stripped:
                            continue
                        
                        # Check if this is a skip pattern
                        should_skip = False
                        for pattern in skip_patterns:
                            if pattern.lower() in line_stripped.lower():
                                should_skip = True
                                skip_until_content = True
                                break
                        
                        if should_skip:
                            continue
                        
                        # Found content - start collecting
                        skip_until_content = False
                        content_lines.append(line)
                    
                    if content_lines:
                        content = '\n'.join(content_lines).strip()
                        logger.info(f"Extracted audio from file (skipping metadata), length: {len(content)}")
                        if len(content) > 10:
                            break
                    
                    # Fallback: use entire file if it's substantial
                    if len(file_content.strip()) > 50:
                        content = file_content.strip()
                        logger.info(f"Using entire audio file content, length: {len(content)}")
                        break
                        
            except Exception as e:
                logger.warning(f"Error reading audio file (attempt {attempt + 1}): {e}")
        await asyncio.sleep(0.5)
    
    # Final fallback: extract from result object
    if not content or len(content.strip()) < 10:
        logger.info("Audio file content empty, using result object extraction")
        content = extract_content_from_result(result, 'audio')
    
    logger.info(f"Final extracted audio content length: {len(content) if content else 0}")
    if content:
        logger.info(f"Audio content preview: {content[:200]}")
    
    return content


async def extract_video_content_async(result, topic: str, logger) -> str:
    """Extract video content from result asynchronously - optimized"""
    # First try direct extraction from result object
    content = extract_content_from_result(result, 'video')
    
    if content and len(content.strip()) > 10:
        logger.info(f"Successfully extracted video content from result object, length: {len(content)}")
        return content
    
    # Fallback to file-based extraction
    await asyncio.sleep(1)
    
    # Try reading the video output file
    output_file = Path("video_output.md")
    for attempt in range(10):
        if output_file.exists():
            try:
                file_content = output_file.read_text(encoding='utf-8')
                if file_content and len(file_content.strip()) > 10:
                    logger.info(f"Video file read attempt {attempt + 1}, file length: {len(file_content)}")
                    
                    # First try: look for separator
                    if "---" in file_content:
                        parts = file_content.split("---", 1)
                        if len(parts) > 1:
                            content = parts[1].strip()
                            logger.info(f"Extracted video from file after separator, length: {len(content)}")
                            if len(content) > 10:
                                break
                    
                    # Second try: skip metadata lines and get actual content
                    lines = file_content.split('\n')
                    content_lines = []
                    skip_patterns = [
                        '# Video',
                        '**Generated on:**',
                        '---',
                        'I now can give a great answer',
                    ]
                    
                    skip_until_content = True
                    for i, line in enumerate(lines):
                        line_stripped = line.strip()
                        
                        # Skip empty lines at the start
                        if skip_until_content and not line_stripped:
                            continue
                        
                        # Check if this is a skip pattern
                        should_skip = False
                        for pattern in skip_patterns:
                            if pattern.lower() in line_stripped.lower():
                                should_skip = True
                                skip_until_content = True
                                break
                        
                        if should_skip:
                            continue
                        
                        # Found content - start collecting
                        skip_until_content = False
                        content_lines.append(line)
                    
                    if content_lines:
                        content = '\n'.join(content_lines).strip()
                        logger.info(f"Extracted video from file (skipping metadata), length: {len(content)}")
                        if len(content) > 10:
                            break
                    
                    # Fallback: use entire file if it's substantial
                    if len(file_content.strip()) > 50:
                        content = file_content.strip()
                        logger.info(f"Using entire video file content, length: {len(content)}")
                        break
                        
            except Exception as e:
                logger.warning(f"Error reading video file (attempt {attempt + 1}): {e}")
        await asyncio.sleep(0.5)
    
    # Final fallback: extract from result object
    if not content or len(content.strip()) < 10:
        logger.info("Video file content empty, using result object extraction")
        content = extract_content_from_result(result, 'video')
    
    logger.info(f"Final extracted video content length: {len(content) if content else 0}")
    if content:
        logger.info(f"Video content preview: {content[:200]}")
    
    return content


def clean_content(content: str) -> str:
    """Clean up content by removing common prefixes"""
    if not content:
        return ""
    
    lines = content.split('\n')
    cleaned_lines = []
    skip_prefixes = [
        "your final answer must be",
        "i now can give a great answer",
        "here is the",
    ]
    skip_next = False
    for line in lines:
        line_lower = line.strip().lower()
        if any(line_lower.startswith(prefix) for prefix in skip_prefixes):
            skip_next = True
            continue
        if skip_next and not line.strip():
            skip_next = False
            continue
        skip_next = False
        cleaned_lines.append(line)
    return '\n'.join(cleaned_lines).strip()


@app.post("/api/generate")
async def generate_content(
    request: TopicRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate content for a given topic using the Content Creation Crew
    Returns a streaming response with progress updates
    
    Tier-based access control:
    - Free tier: Blog content only, limited generations
    - Basic tier: Blog + Social media, more generations
    - Pro tier: All content types, unlimited generations
    - Enterprise: All features + priority processing
    """
    import logging
    from content_creation_crew.streaming_utils import FlushingAsyncGenerator
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    if not request.topic or not request.topic.strip():
        raise HTTPException(status_code=400, detail="Topic is required")
    
    topic = request.topic.strip()
    logger.info(f"Received streaming request for topic: {topic} from user {current_user.id}")
    
    # Initialize subscription service
    subscription_service = SubscriptionService(db)
    
    # Get user's tier
    user_tier = subscription_service.get_user_tier(current_user.id)
    logger.info(f"User {current_user.id} is on {user_tier} tier")
    
    # Determine content types based on tier and request
    requested_content_types = request.content_types or []
    
    # Validate content type access for each requested type
    valid_content_types = []
    for content_type in requested_content_types:
        if subscription_service.check_content_type_access(current_user.id, content_type):
            # Check usage limit
            has_remaining, remaining = subscription_service.check_usage_limit(current_user.id, content_type)
            if has_remaining:
                valid_content_types.append(content_type)
            else:
                logger.warning(f"User {current_user.id} has reached limit for {content_type}")
                raise HTTPException(
                    status_code=403,
                    detail=f"You have reached your {content_type} generation limit."
                )
        else:
            logger.warning(f"User {current_user.id} does not have access to {content_type} on {user_tier} tier")
            raise HTTPException(
                status_code=403,
                detail=f"{content_type.capitalize()} content is not available on your current plan ({user_tier})."
            )
    
    # If no content types specified, use tier defaults
    if not valid_content_types:
        tier_config = subscription_service.get_tier_config(user_tier)
        if tier_config:
            valid_content_types = tier_config.get('content_types', ['blog'])
        else:
            valid_content_types = ['blog']  # Default to blog only
    
    # Check usage for default content types if none specified
    for content_type in valid_content_types:
        has_remaining, remaining = subscription_service.check_usage_limit(current_user.id, content_type)
        if not has_remaining:
            raise HTTPException(
                status_code=403,
                detail=f"You have reached your {content_type} generation limit."
            )
    
    # Create a wrapper to track usage after successful generation
    async def track_usage_wrapper():
        """Wrapper to track usage after successful generation"""
        try:
            async for chunk in run_crew_async(topic, tier=user_tier, content_types=valid_content_types):
                yield chunk
                # Check if this is the completion message
                if chunk.startswith("data: ") and '"type":"complete"' in chunk:
                    # Parse the completion message to verify it succeeded
                    try:
                        import re
                        json_match = re.search(r'data: ({.*})', chunk)
                        if json_match:
                            completion_data = json.loads(json_match.group(1))
                            if completion_data.get('type') == 'complete' and completion_data.get('content'):
                                # Generation succeeded - record usage for each content type
                                for content_type in valid_content_types:
                                    subscription_service.record_usage(current_user.id, content_type)
                                logger.info(f"Recorded usage for user {current_user.id}: {valid_content_types}")
                    except Exception as e:
                        logger.error(f"Error tracking usage: {e}")
        except Exception as e:
            logger.error(f"Error in usage tracking wrapper: {e}")
            raise
    
    # Wrap the generator with flushing capability for better real-time streaming
    streaming_generator = FlushingAsyncGenerator(
        track_usage_wrapper(),
        flush_interval=5
    )
    
    return StreamingResponse(
        streaming_generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "X-Content-Type-Options": "nosniff",
        }
    )


if __name__ == "__main__":
    import uvicorn
    import sys
    import logging
    
    # Set up basic logging for startup
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Log startup information for debugging
    logger.info("=" * 50)
    logger.info("Content Creation Crew API - Starting Up")
    logger.info("=" * 50)
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"PYTHONPATH: {os.getenv('PYTHONPATH', 'NOT SET')}")
    logger.info(f"PORT: {os.getenv('PORT', 'NOT SET (using default 8000)')}")
    logger.info(f"DATABASE_URL: {'SET' if os.getenv('DATABASE_URL') else 'NOT SET (using SQLite)'}")
    
    # Configure Python to use unbuffered output for better streaming
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(line_buffering=True)
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(line_buffering=True)
    
    # Test critical imports
    try:
        logger.info("Testing critical imports...")
        import content_creation_crew
        logger.info("✓ content_creation_crew imported successfully")
    except Exception as e:
        logger.error(f"✗ Failed to import content_creation_crew: {e}", exc_info=True)
        sys.exit(1)
    
    # Get port from environment variable (Railway provides PORT)
    # Default to 8000 for local development
    try:
        port = int(os.getenv("PORT", 8000))
    except ValueError:
        logger.warning(f"Invalid PORT value: {os.getenv('PORT')}, using default 8000")
        port = 8000
    
    logger.info(f"Starting Content Creation Crew API server on port {port}")
    logger.info(f"Health check endpoint: http://0.0.0.0:{port}/health")
    logger.info("=" * 50)
    
    # Configure uvicorn to disable buffering for streaming
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",  # Listen on all interfaces (required for Railway)
            port=port,
            log_config=None,  # Use default logging
            access_log=True,
            loop="asyncio",
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        sys.exit(1)

