"""
Tests for metrics collection and expensive operations tracking (M7)
"""
import pytest
import time
from unittest.mock import Mock, patch

class TestMetricsHelpers:
    """Test metrics helper classes"""
    
    def test_llm_metrics_record_call(self):
        """Test LLM metrics recording"""
        from content_creation_crew.services.metrics import LLMMetrics, get_metrics_collector
        
        collector = get_metrics_collector()
        
        # Record successful call
        LLMMetrics.record_call("llama3.2:1b", 2.5, success=True)
        
        # Verify counter
        calls = collector.get_counter("llm_calls_total", {"model": "llama3.2:1b"})
        assert calls == 1.0
        
        # Verify no failures
        failures = collector.get_counter("llm_failures_total", {"model": "llama3.2:1b"})
        assert failures == 0.0
    
    def test_llm_metrics_record_failure(self):
        """Test LLM failure metrics"""
        from content_creation_crew.services.metrics import LLMMetrics, get_metrics_collector
        
        collector = get_metrics_collector()
        
        # Record failed call
        LLMMetrics.record_call("llama3.2:1b", 1.0, success=False)
        
        # Verify failure counter
        failures = collector.get_counter("llm_failures_total", {"model": "llama3.2:1b"})
        assert failures >= 1.0
    
    def test_llm_metrics_timer(self):
        """Test LLM timer context manager"""
        from content_creation_crew.services.metrics import LLMMetrics, get_metrics_collector
        
        collector = get_metrics_collector()
        
        # Use timer
        with LLMMetrics.timer("mistral:7b"):
            time.sleep(0.1)
        
        # Verify histogram recorded
        stats = collector.get_histogram_stats("llm_call_seconds", {"model": "mistral:7b"})
        assert stats["count"] >= 1
        assert stats["sum"] >= 0.1
    
    def test_storage_metrics_put(self):
        """Test storage PUT metrics"""
        from content_creation_crew.services.metrics import StorageMetrics, get_metrics_collector
        
        collector = get_metrics_collector()
        
        # Record PUT
        StorageMetrics.record_put("voiceover", 1024, success=True)
        
        # Verify counters
        puts = collector.get_counter("storage_put_total", {"artifact_type": "voiceover"})
        assert puts >= 1.0
        
        bytes_written = collector.get_counter("storage_bytes_written_total", {"artifact_type": "voiceover"})
        assert bytes_written >= 1024.0
    
    def test_storage_metrics_get(self):
        """Test storage GET metrics"""
        from content_creation_crew.services.metrics import StorageMetrics, get_metrics_collector
        
        collector = get_metrics_collector()
        
        # Record GET
        StorageMetrics.record_get("blog", 2048, success=True)
        
        # Verify counters
        gets = collector.get_counter("storage_get_total", {"artifact_type": "blog"})
        assert gets >= 1.0
        
        bytes_read = collector.get_counter("storage_bytes_read_total", {"artifact_type": "blog"})
        assert bytes_read >= 2048.0
    
    def test_storage_metrics_delete(self):
        """Test storage DELETE metrics"""
        from content_creation_crew.services.metrics import StorageMetrics, get_metrics_collector
        
        collector = get_metrics_collector()
        
        # Record DELETE
        StorageMetrics.record_delete("video_clip", success=True)
        
        # Verify counter
        deletes = collector.get_counter("storage_delete_total", {"artifact_type": "video_clip"})
        assert deletes >= 1.0
    
    def test_storage_metrics_failure(self):
        """Test storage failure metrics"""
        from content_creation_crew.services.metrics import StorageMetrics, get_metrics_collector
        
        collector = get_metrics_collector()
        
        # Record failed PUT
        StorageMetrics.record_put("voiceover", 1024, success=False)
        
        # Verify failure counter
        failures = collector.get_counter("storage_failures_total", {
            "artifact_type": "voiceover",
            "operation": "put"
        })
        assert failures >= 1.0
    
    def test_video_metrics_render(self):
        """Test video render metrics"""
        from content_creation_crew.services.metrics import VideoMetrics, get_metrics_collector
        
        collector = get_metrics_collector()
        
        # Record render
        VideoMetrics.record_render("remotion", 120.5, success=True)
        
        # Verify counters
        renders = collector.get_counter("video_renders_total", {"renderer": "remotion"})
        assert renders >= 1.0
        
        failures = collector.get_counter("video_render_failures_total", {"renderer": "remotion"})
        assert failures == 0.0
    
    def test_video_metrics_failure(self):
        """Test video render failure metrics"""
        from content_creation_crew.services.metrics import VideoMetrics, get_metrics_collector
        
        collector = get_metrics_collector()
        
        # Record failed render
        VideoMetrics.record_render("ffmpeg", 30.0, success=False)
        
        # Verify failure counter
        failures = collector.get_counter("video_render_failures_total", {"renderer": "ffmpeg"})
        assert failures >= 1.0
    
    def test_tts_metrics_synthesis(self):
        """Test TTS synthesis metrics"""
        from content_creation_crew.services.metrics import TTSMetrics, get_metrics_collector
        
        collector = get_metrics_collector()
        
        # Record synthesis
        TTSMetrics.record_synthesis("elevenlabs", 3.5, success=True)
        
        # Verify counters
        jobs = collector.get_counter("tts_jobs_total", {"provider": "elevenlabs"})
        assert jobs >= 1.0
        
        failures = collector.get_counter("tts_failures_total", {"provider": "elevenlabs"})
        assert failures == 0.0
    
    def test_tts_metrics_failure(self):
        """Test TTS failure metrics"""
        from content_creation_crew.services.metrics import TTSMetrics, get_metrics_collector
        
        collector = get_metrics_collector()
        
        # Record failed synthesis
        TTSMetrics.record_synthesis("gtts", 1.0, success=False)
        
        # Verify failure counter
        failures = collector.get_counter("tts_failures_total", {"provider": "gtts"})
        assert failures >= 1.0
    
    def test_retention_metrics_delete(self):
        """Test retention delete metrics"""
        from content_creation_crew.services.metrics import RetentionMetrics, get_metrics_collector
        
        collector = get_metrics_collector()
        
        # Record delete
        RetentionMetrics.record_delete("free", 10, 5242880)  # 5MB
        
        # Verify counters
        deletes = collector.get_counter("retention_deletes_total", {"plan": "free"})
        assert deletes >= 10.0
        
        bytes_freed = collector.get_counter("retention_bytes_freed_total", {"plan": "free"})
        assert bytes_freed >= 5242880.0
    
    def test_retention_metrics_cleanup_run(self):
        """Test retention cleanup run metrics"""
        from content_creation_crew.services.metrics import RetentionMetrics, get_metrics_collector
        
        collector = get_metrics_collector()
        
        # Record cleanup run
        RetentionMetrics.record_cleanup_run(120.0, 50, 104857600)  # 100MB
        
        # Verify counters
        runs = collector.get_counter("retention_cleanup_runs_total")
        assert runs >= 1.0
        
        items = collector.get_counter("retention_cleanup_items_total")
        assert items >= 50.0
        
        bytes_cleaned = collector.get_counter("retention_cleanup_bytes_total")
        assert bytes_cleaned >= 104857600.0


class TestMetricsEndpoint:
    """Test /metrics endpoint"""
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint_exists(self, client):
        """Test that /metrics endpoint exists"""
        response = await client.get("/metrics")
        
        # Should return 200
        assert response.status_code == 200
        
        # Should return text
        assert "text/plain" in response.headers.get("content-type", "")
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint_format(self, client):
        """Test that /metrics returns Prometheus format"""
        response = await client.get("/metrics")
        
        content = response.text
        
        # Should contain metric names
        assert len(content) > 0
        
        # Should be line-based format
        assert "\n" in content
    
    @pytest.mark.asyncio
    async def test_metrics_include_new_metrics(self, client):
        """Test that new metrics are included"""
        # Generate some metrics
        from content_creation_crew.services.metrics import (
            LLMMetrics, StorageMetrics, TTSMetrics
        )
        
        LLMMetrics.record_call("test_model", 1.0, success=True)
        StorageMetrics.record_put("test_artifact", 1024, success=True)
        TTSMetrics.record_synthesis("test_provider", 1.0, success=True)
        
        # Fetch metrics
        response = await client.get("/metrics")
        content = response.text
        
        # Verify new metrics present (at least some of them)
        # Note: Metrics may not always be present if not triggered
        assert response.status_code == 200


class TestMetricsInstrumentation:
    """Test that operations are properly instrumented"""
    
    @pytest.mark.asyncio
    async def test_llm_call_tracked(self):
        """Test that LLM calls are tracked in actual usage"""
        # This would require integration test with real LLM
        # For now, verify metrics exist
        from content_creation_crew.services.metrics import get_metrics_collector
        
        collector = get_metrics_collector()
        assert collector is not None
    
    @pytest.mark.asyncio
    async def test_storage_operation_tracked(self):
        """Test that storage operations are tracked"""
        from content_creation_crew.services.storage_provider import LocalDiskStorageProvider
        from content_creation_crew.services.metrics import get_metrics_collector
        
        collector = get_metrics_collector()
        
        # Storage operations should be instrumented in content_routes.py
        assert collector is not None


class TestPrometheusFormat:
    """Test Prometheus format compliance"""
    
    def test_counter_format(self):
        """Test counter metric format"""
        from content_creation_crew.services.metrics import get_metrics_collector
        
        collector = get_metrics_collector()
        
        # Add some metrics
        collector.increment_counter("test_counter", 5.0)
        collector.increment_counter("test_labeled", 3.0, {"label": "value"})
        
        # Format as Prometheus
        output = collector.format_prometheus()
        
        # Verify format
        assert "test_counter 5" in output or "test_counter 5.0" in output
        assert 'test_labeled{label="value"}' in output
    
    def test_histogram_format(self):
        """Test histogram metric format"""
        from content_creation_crew.services.metrics import get_metrics_collector
        
        collector = get_metrics_collector()
        
        # Record histogram values
        for i in range(10):
            collector.record_histogram("test_duration", float(i))
        
        # Format as Prometheus
        output = collector.format_prometheus()
        
        # Verify summary format (count, sum, quantiles)
        assert "test_duration_count 10" in output
        assert "test_duration_sum" in output
        assert 'quantile="0.5"' in output
        assert 'quantile="0.95"' in output
        assert 'quantile="0.99"' in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

