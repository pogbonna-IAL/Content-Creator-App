"""
Task Registry for tracking and canceling running async tasks
Allows cancellation of content generation jobs to save API tokens and compute resources
"""
import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TaskRegistry:
    """Registry to track running async tasks by job_id"""
    
    def __init__(self):
        self._tasks: Dict[int, asyncio.Task] = {}
        self._lock = asyncio.Lock()
    
    async def register(self, job_id: int, task: asyncio.Task):
        """Register a task for a job_id"""
        async with self._lock:
            self._tasks[job_id] = task
            logger.info(f"Registered task for job {job_id}")
    
    async def unregister(self, job_id: int):
        """Unregister a task for a job_id"""
        async with self._lock:
            if job_id in self._tasks:
                del self._tasks[job_id]
                logger.info(f"Unregistered task for job {job_id}")
    
    async def cancel(self, job_id: int) -> bool:
        """
        Cancel a running task for a job_id
        
        Returns:
            True if task was found and cancelled, False otherwise
        """
        async with self._lock:
            if job_id not in self._tasks:
                logger.warning(f"Task for job {job_id} not found in registry")
                return False
            
            task = self._tasks[job_id]
            
            if task.done():
                logger.info(f"Task for job {job_id} already completed")
                await self.unregister(job_id)
                return False
            
            logger.info(f"Cancelling task for job {job_id}")
            cancelled = task.cancel()
            
            if cancelled:
                logger.info(f"Task for job {job_id} cancellation requested")
                # Don't unregister immediately - let the task handle cleanup
                return True
            else:
                logger.warning(f"Failed to cancel task for job {job_id}")
                return False
    
    async def get_task(self, job_id: int) -> Optional[asyncio.Task]:
        """Get the task for a job_id"""
        async with self._lock:
            return self._tasks.get(job_id)
    
    async def is_running(self, job_id: int) -> bool:
        """Check if a task is running for a job_id"""
        async with self._lock:
            if job_id not in self._tasks:
                return False
            task = self._tasks[job_id]
            return not task.done()


# Global singleton instance
_registry: Optional[TaskRegistry] = None


def get_task_registry() -> TaskRegistry:
    """Get the global task registry instance"""
    global _registry
    if _registry is None:
        _registry = TaskRegistry()
    return _registry
