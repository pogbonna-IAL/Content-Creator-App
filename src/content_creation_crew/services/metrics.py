"""
Prometheus metrics collection service
Provides counters and histograms for monitoring
"""
import time
from typing import Dict, Optional
from collections import defaultdict
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Thread-safe metrics collector for Prometheus format
    Uses in-memory storage (lightweight, no external dependencies)
    """
    
    def __init__(self):
        """Initialize metrics collector"""
        self._lock = Lock()
        
        # Counters (monotonically increasing)
        self._counters: Dict[str, float] = defaultdict(float)
        
        # Histograms (for timing metrics)
        self._histograms: Dict[str, list] = defaultdict(list)
        
        # Labels support: counter_name{label1="value1",label2="value2"} = value
        self._labeled_counters: Dict[str, Dict[tuple, float]] = defaultdict(lambda: defaultdict(float))
    
    def increment_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """
        Increment a counter metric
        
        Args:
            name: Metric name (e.g., "requests_total")
            value: Increment value (default: 1.0)
            labels: Optional labels dict (e.g., {"route": "/api/generate", "status": "200"})
        """
        with self._lock:
            if labels:
                # Create label tuple for hashable key
                label_tuple = tuple(sorted(labels.items()))
                self._labeled_counters[name][label_tuple] += value
            else:
                self._counters[name] += value
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """
        Record a histogram value (for timing metrics)
        
        Args:
            name: Metric name (e.g., "request_duration_seconds")
            value: Value to record (e.g., 0.123 for 123ms)
            labels: Optional labels dict
        """
        with self._lock:
            # Store last 1000 values per metric (lightweight)
            key = name
            if labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
                key = f"{name}{{{label_str}}}"
            
            if len(self._histograms[key]) >= 1000:
                # Keep only last 1000 values
                self._histograms[key] = self._histograms[key][-1000:]
            
            self._histograms[key].append(value)
    
    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current counter value"""
        with self._lock:
            if labels:
                label_tuple = tuple(sorted(labels.items()))
                return self._labeled_counters[name].get(label_tuple, 0.0)
            return self._counters.get(name, 0.0)
    
    def get_histogram_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """
        Get histogram statistics (count, sum, min, max, avg)
        
        Returns:
            Dict with count, sum, min, max, avg
        """
        with self._lock:
            key = name
            if labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
                key = f"{name}{{{label_str}}}"
            
            values = self._histograms.get(key, [])
            if not values:
                return {"count": 0, "sum": 0, "min": 0, "max": 0, "avg": 0}
            
            return {
                "count": len(values),
                "sum": sum(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values) if values else 0
            }
    
    def format_prometheus(self) -> str:
        """
        Format metrics in Prometheus text format
        
        Returns:
            Prometheus-formatted metrics string
        """
        lines = []
        
        with self._lock:
            # Format counters without labels
            for name, value in sorted(self._counters.items()):
                lines.append(f"{name} {value}")
            
            # Format labeled counters
            for name, label_dict in sorted(self._labeled_counters.items()):
                for label_tuple, value in sorted(label_dict.items()):
                    if label_tuple:
                        label_str = ",".join(f'{k}="{v}"' for k, v in label_tuple)
                        lines.append(f"{name}{{{label_str}}} {value}")
                    else:
                        lines.append(f"{name} {value}")
            
            # Format histograms as summaries (lightweight alternative)
            for key, values in sorted(self._histograms.items()):
                if values:
                    count = len(values)
                    sum_val = sum(values)
                    # Calculate quantiles (p50, p95, p99)
                    sorted_values = sorted(values)
                    p50 = sorted_values[int(len(sorted_values) * 0.5)] if sorted_values else 0
                    p95 = sorted_values[int(len(sorted_values) * 0.95)] if len(sorted_values) > 1 else sorted_values[0] if sorted_values else 0
                    p99 = sorted_values[int(len(sorted_values) * 0.99)] if len(sorted_values) > 1 else sorted_values[-1] if sorted_values else 0
                    
                    # Format as summary
                    base_name = key.split("{")[0] if "{" in key else key
                    if "{" in key:
                        label_part = key.split("{", 1)[1]
                        lines.append(f"{base_name}_count{{{label_part}}} {count}")
                        lines.append(f"{base_name}_sum{{{label_part}}} {sum_val}")
                        lines.append(f"{base_name}{{{label_part},quantile=\"0.5\"}} {p50}")
                        lines.append(f"{base_name}{{{label_part},quantile=\"0.95\"}} {p95}")
                        lines.append(f"{base_name}{{{label_part},quantile=\"0.99\"}} {p99}")
                    else:
                        lines.append(f"{base_name}_count {count}")
                        lines.append(f"{base_name}_sum {sum_val}")
                        lines.append(f'{base_name}{{quantile="0.5"}} {p50}')
                        lines.append(f'{base_name}{{quantile="0.95"}} {p95}')
                        lines.append(f'{base_name}{{quantile="0.99"}} {p99}')
        
        return "\n".join(lines) + "\n"


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def increment_counter(name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
    """Convenience function to increment counter"""
    get_metrics_collector().increment_counter(name, value, labels)


def record_histogram(name: str, value: float, labels: Optional[Dict[str, str]] = None):
    """Convenience function to record histogram"""
    get_metrics_collector().record_histogram(name, value, labels)


class RequestTimer:
    """Context manager for timing requests"""
    
    def __init__(self, metric_name: str, labels: Optional[Dict[str, str]] = None):
        self.metric_name = metric_name
        self.labels = labels or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            record_histogram(self.metric_name, duration, self.labels)

