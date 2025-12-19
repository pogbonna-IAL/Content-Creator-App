"""
Streaming utilities for buffer management
"""
import sys
import asyncio
from typing import AsyncGenerator


def flush_buffers():
    """Flush stdout and stderr buffers to ensure immediate output"""
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass


async def flush_async():
    """Async version of buffer flushing"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, flush_buffers)


class FlushingAsyncGenerator:
    """
    Wrapper for async generators that flushes buffers after each yield
    """
    def __init__(self, generator: AsyncGenerator[str, None], flush_interval: int = 5):
        self.generator = generator
        self.flush_interval = flush_interval
        self.count = 0
    
    def __aiter__(self):
        """Return self as the async iterator - must be synchronous"""
        return self
    
    async def __anext__(self):
        """Get next value from wrapped generator and flush buffers periodically"""
        try:
            value = await self.generator.__anext__()
            self.count += 1
            
            # Flush buffers periodically
            if self.count % self.flush_interval == 0:
                await flush_async()
            
            return value
        except StopAsyncIteration:
            # Final flush before stopping
            await flush_async()
            raise

