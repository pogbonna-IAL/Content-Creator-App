"""
SSE Event Store - Stores last N SSE events in Redis for replay support
Falls back to in-memory storage if Redis not available
"""
import json
import logging
import time
from typing import List, Optional, Dict
from datetime import datetime

from .redis_cache import get_redis_client

logger = logging.getLogger(__name__)


class SSEEventStore:
    """
    Stores SSE events for job streaming with replay support
    
    Stores last N events per job so clients can reconnect using Last-Event-ID header
    """
    
    def __init__(self, max_events_per_job: int = 100, redis_client=None):
        """
        Initialize SSE event store
        
        Args:
            max_events_per_job: Maximum number of events to store per job (default: 100)
            redis_client: Optional Redis client (auto-created if not provided)
        """
        self.max_events_per_job = max_events_per_job
        self.redis_client = redis_client or get_redis_client()
        self.use_redis = self.redis_client is not None
        
        # In-memory fallback
        self.memory_store: Dict[int, List[Dict]] = {}
        
        if not self.use_redis:
            logger.info("Using in-memory SSE event store (Redis not available)")
        else:
            logger.info("Using Redis SSE event store")
    
    def _get_event_key(self, job_id: int) -> str:
        """Generate Redis key for job events"""
        return f"sse:events:{job_id}"
    
    def _get_event_id_key(self, job_id: int, event_id: int) -> str:
        """Generate Redis key for specific event"""
        return f"sse:event:{job_id}:{event_id}"
    
    def add_event(self, job_id: int, event_type: str, data: Dict, event_id: Optional[int] = None) -> int:
        """
        Add an SSE event for a job
        
        Args:
            job_id: Job ID
            event_type: Event type (e.g., 'job_started', 'artifact_ready', 'complete')
            data: Event data dictionary
            event_id: Optional event ID (auto-generated if not provided)
        
        Returns:
            Event ID
        """
        if event_id is None:
            event_id = int(time.time() * 1000)  # Use timestamp as event ID
        
        event = {
            'id': event_id,
            'type': event_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if not self.use_redis:
            return self._add_event_memory(job_id, event)
        
        try:
            # Store event in Redis list (FIFO)
            key = self._get_event_key(job_id)
            event_json = json.dumps(event, default=str)
            
            # Add to list
            self.redis_client.lpush(key, event_json)
            
            # Trim list to max_events_per_job
            self.redis_client.ltrim(key, 0, self.max_events_per_job - 1)
            
            # Set expiration (24 hours)
            self.redis_client.expire(key, 86400)
            
            return event_id
        except Exception as e:
            logger.warning(f"Redis event store failed: {e}, falling back to in-memory")
            return self._add_event_memory(job_id, event)
    
    def _add_event_memory(self, job_id: int, event: Dict) -> int:
        """Add event to in-memory store"""
        if job_id not in self.memory_store:
            self.memory_store[job_id] = []
        
        self.memory_store[job_id].append(event)
        
        # Trim to max_events_per_job
        if len(self.memory_store[job_id]) > self.max_events_per_job:
            self.memory_store[job_id] = self.memory_store[job_id][-self.max_events_per_job:]
        
        return event['id']
    
    def get_events_since(self, job_id: int, last_event_id: Optional[int] = None) -> List[Dict]:
        """
        Get events since last_event_id
        
        Args:
            job_id: Job ID
            last_event_id: Last event ID received (None for all events)
        
        Returns:
            List of events since last_event_id
        """
        if not self.use_redis:
            return self._get_events_memory(job_id, last_event_id)
        
        try:
            key = self._get_event_key(job_id)
            events_json = self.redis_client.lrange(key, 0, -1)
            
            events = []
            for event_json in reversed(events_json):  # Reverse to get chronological order
                event = json.loads(event_json)
                if last_event_id is None or event['id'] > last_event_id:
                    events.append(event)
            
            return events
        except Exception as e:
            logger.warning(f"Redis event retrieval failed: {e}, falling back to in-memory")
            return self._get_events_memory(job_id, last_event_id)
    
    def _get_events_memory(self, job_id: int, last_event_id: Optional[int]) -> List[Dict]:
        """Get events from in-memory store"""
        if job_id not in self.memory_store:
            return []
        
        events = self.memory_store[job_id]
        
        if last_event_id is None:
            return events
        
        # Filter events after last_event_id
        return [e for e in events if e['id'] > last_event_id]
    
    def get_latest_event_id(self, job_id: int) -> Optional[int]:
        """Get the latest event ID for a job"""
        if not self.use_redis:
            if job_id in self.memory_store and self.memory_store[job_id]:
                return self.memory_store[job_id][-1]['id']
            return None
        
        try:
            key = self._get_event_key(job_id)
            events_json = self.redis_client.lrange(key, 0, 0)  # Get most recent
            
            if events_json:
                event = json.loads(events_json[0])
                return event['id']
            return None
        except Exception as e:
            logger.warning(f"Redis latest event ID failed: {e}")
            return None
    
    def clear_events(self, job_id: int):
        """Clear all events for a job"""
        if not self.use_redis:
            if job_id in self.memory_store:
                del self.memory_store[job_id]
            return
        
        try:
            key = self._get_event_key(job_id)
            self.redis_client.delete(key)
        except Exception as e:
            logger.warning(f"Redis clear events failed: {e}")


# Global SSE event store instance
_sse_store_instance: Optional[SSEEventStore] = None


def get_sse_store() -> SSEEventStore:
    """Get global SSE event store instance"""
    global _sse_store_instance
    if _sse_store_instance is None:
        _sse_store_instance = SSEEventStore()
    return _sse_store_instance

