"""
Database Connection Pool Monitoring
Provides utilities to monitor and report on connection pool health
"""
import logging
from typing import Dict, Any
from .engine import engine

logger = logging.getLogger(__name__)


def get_pool_stats() -> Dict[str, Any]:
    """
    Get current connection pool statistics
    
    Returns:
        Dictionary with pool metrics
    """
    try:
        pool = engine.pool
        
        # Get pool status string and parse it
        status_str = pool.status()
        
        # Parse status string (format: "Pool size: X  Connections in pool: Y  Current Overflow: Z  Current Checked out connections: W")
        stats = {
            "pool_size": pool.size(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total_connections": pool.size() + pool.overflow(),
            "available": pool.size() - pool.checkedout(),
            "status": status_str
        }
        
        # Calculate pool utilization
        max_connections = pool.size() + getattr(pool, '_max_overflow', 0)
        current_usage = pool.checkedout() + pool.overflow()
        stats["utilization_percent"] = (current_usage / max_connections * 100) if max_connections > 0 else 0
        
        return stats
    except Exception as e:
        logger.error(f"Failed to get pool stats: {e}")
        return {
            "error": str(e),
            "status": "unknown"
        }


def log_pool_stats():
    """Log current pool statistics"""
    stats = get_pool_stats()
    
    if "error" in stats:
        logger.warning(f"Pool stats unavailable: {stats['error']}")
        return
    
    logger.info("=" * 60)
    logger.info("DATABASE CONNECTION POOL STATISTICS")
    logger.info("=" * 60)
    logger.info(f"Pool size (base):        {stats['pool_size']}")
    logger.info(f"Checked out:             {stats['checked_out']}")
    logger.info(f"Overflow (extra):        {stats['overflow']}")
    logger.info(f"Total connections:       {stats['total_connections']}")
    logger.info(f"Available:               {stats['available']}")
    logger.info(f"Utilization:             {stats['utilization_percent']:.1f}%")
    logger.info("=" * 60)


def check_pool_health() -> tuple[bool, str]:
    """
    Check connection pool health
    
    Returns:
        Tuple of (is_healthy, message)
    """
    stats = get_pool_stats()
    
    if "error" in stats:
        return False, f"Pool stats unavailable: {stats['error']}"
    
    # Check if pool is nearly exhausted
    if stats["utilization_percent"] > 90:
        return False, f"Pool utilization critical: {stats['utilization_percent']:.1f}% (checked out: {stats['checked_out']}, overflow: {stats['overflow']})"
    
    # Check if we're using overflow connections excessively
    if stats["overflow"] > stats["pool_size"]:
        return False, f"Excessive overflow usage: {stats['overflow']} overflow connections (pool size: {stats['pool_size']})"
    
    # All checks passed
    return True, "Pool healthy"


def get_pool_metrics_for_prometheus() -> Dict[str, float]:
    """
    Get pool metrics in Prometheus format
    
    Returns:
        Dictionary of metric name -> value
    """
    stats = get_pool_stats()
    
    if "error" in stats:
        return {}
    
    return {
        "db_pool_size": float(stats.get("pool_size", 0)),
        "db_pool_checked_out": float(stats.get("checked_out", 0)),
        "db_pool_overflow": float(stats.get("overflow", 0)),
        "db_pool_available": float(stats.get("available", 0)),
        "db_pool_utilization_percent": float(stats.get("utilization_percent", 0)),
    }

