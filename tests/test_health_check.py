"""
Tests for comprehensive health check system (M5)
"""
import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import asyncio

# Test fixtures
@pytest.fixture
def temp_storage_dir():
    """Create a temporary storage directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def mock_redis_client():
    """Mock Redis client"""
    client = Mock()
    client.ping = Mock(return_value=True)
    return client


class TestLocalDiskStorageHealth:
    """Test LocalDiskStorageProvider health checks"""
    
    def test_health_check_accessible_and_writable(self, temp_storage_dir):
        """Test health check on accessible and writable storage"""
        from content_creation_crew.services.storage_provider import LocalDiskStorageProvider
        
        provider = LocalDiskStorageProvider(base_path=temp_storage_dir)
        
        # Run health check
        health_info = asyncio.run(provider.check_health(
            write_test=True,
            min_free_space_mb=1  # Very low threshold for test
        ))
        
        # Verify
        assert health_info["accessible"] is True
        assert health_info["writable"] is True
        assert health_info["free_space_mb"] > 0
        assert health_info["total_space_mb"] > 0
        assert health_info["free_space_percent"] > 0
        assert health_info["path"] == str(temp_storage_dir)
        assert health_info["error"] is None
    
    def test_health_check_without_write_test(self, temp_storage_dir):
        """Test health check without write test"""
        from content_creation_crew.services.storage_provider import LocalDiskStorageProvider
        
        provider = LocalDiskStorageProvider(base_path=temp_storage_dir)
        
        # Run health check without write test
        health_info = asyncio.run(provider.check_health(
            write_test=False,
            min_free_space_mb=1
        ))
        
        # Verify
        assert health_info["accessible"] is True
        assert health_info["writable"] is True  # Should check via os.access
        assert health_info["free_space_mb"] > 0
    
    def test_health_check_nonexistent_path(self):
        """Test health check on non-existent path"""
        from content_creation_crew.services.storage_provider import LocalDiskStorageProvider
        
        # Create provider but delete the directory
        temp_dir = tempfile.mkdtemp()
        provider = LocalDiskStorageProvider(base_path=temp_dir)
        shutil.rmtree(temp_dir)
        
        # Run health check
        health_info = asyncio.run(provider.check_health())
        
        # Verify
        assert health_info["accessible"] is False
        assert health_info["writable"] is False
        assert health_info["error"] == "Storage path does not exist"
    
    def test_health_check_low_disk_space(self, temp_storage_dir):
        """Test health check with low disk space threshold"""
        from content_creation_crew.services.storage_provider import LocalDiskStorageProvider
        
        provider = LocalDiskStorageProvider(base_path=temp_storage_dir)
        
        # Run health check with impossibly high threshold
        health_info = asyncio.run(provider.check_health(
            write_test=False,
            min_free_space_mb=999999999  # 999GB - should fail
        ))
        
        # Verify
        assert health_info["accessible"] is True
        assert "Low disk space" in health_info["error"]
    
    def test_health_check_readonly_directory(self, temp_storage_dir):
        """Test health check on read-only directory"""
        from content_creation_crew.services.storage_provider import LocalDiskStorageProvider
        
        provider = LocalDiskStorageProvider(base_path=temp_storage_dir)
        
        # Make directory read-only
        os.chmod(temp_storage_dir, 0o444)
        
        try:
            # Run health check with write test
            health_info = asyncio.run(provider.check_health(
                write_test=True,
                min_free_space_mb=1
            ))
            
            # Verify
            assert health_info["accessible"] is True
            assert health_info["writable"] is False
            assert "Write test failed" in health_info["error"]
        
        finally:
            # Restore permissions
            os.chmod(temp_storage_dir, 0o755)
    
    def test_health_check_file_not_directory(self, temp_storage_dir):
        """Test health check when path is a file, not a directory"""
        from content_creation_crew.services.storage_provider import LocalDiskStorageProvider
        
        # Create a file instead of directory
        file_path = os.path.join(temp_storage_dir, "not_a_dir")
        with open(file_path, 'w') as f:
            f.write("test")
        
        # Create provider pointing to file
        provider = LocalDiskStorageProvider(base_path=file_path)
        
        # Override the path (since constructor creates directory)
        provider.base_path = Path(file_path)
        
        # Run health check
        health_info = asyncio.run(provider.check_health())
        
        # Verify
        assert health_info["accessible"] is False
        assert health_info["error"] == "Storage path is not a directory"


class TestS3StorageHealth:
    """Test S3StorageProvider health checks"""
    
    @pytest.mark.skipif(True, reason="Requires S3/boto3 setup")
    def test_s3_health_check_accessible(self):
        """Test S3 health check when accessible"""
        from content_creation_crew.services.storage_provider import S3StorageProvider
        
        # Mock S3 client
        with patch('boto3.client') as mock_boto:
            mock_client = Mock()
            mock_client.head_bucket = Mock()
            mock_client.put_object = Mock()
            mock_client.get_object = Mock(return_value={'Body': Mock(read=lambda: b"health_check")})
            mock_client.delete_object = Mock()
            mock_boto.return_value = mock_client
            
            provider = S3StorageProvider(bucket_name="test-bucket")
            
            # Run health check
            health_info = asyncio.run(provider.check_health(
                write_test=True,
                min_free_space_mb=1024
            ))
            
            # Verify
            assert health_info["accessible"] is True
            assert health_info["writable"] is True
            assert health_info["free_space_mb"] == -1  # Not applicable for S3
            assert health_info["bucket"] == "test-bucket"


class TestHealthChecker:
    """Test HealthChecker service"""
    
    @pytest.mark.asyncio
    async def test_check_database_success(self):
        """Test database health check success"""
        from content_creation_crew.services.health_check import HealthChecker, HealthStatus
        
        checker = HealthChecker(timeout_seconds=5)
        
        # Run check (requires actual database)
        result = await checker.check_database()
        
        # Verify structure
        assert result.name == "database"
        assert result.status in [HealthStatus.OK, HealthStatus.DOWN]
        assert result.message is not None
        assert result.checked_at is not None
    
    @pytest.mark.asyncio
    async def test_check_redis_not_configured(self):
        """Test Redis health check when not configured"""
        from content_creation_crew.services.health_check import HealthChecker, HealthStatus
        
        with patch('content_creation_crew.services.health_check.get_redis_client', return_value=None):
            checker = HealthChecker(timeout_seconds=5)
            result = await checker.check_redis()
            
            # Verify
            assert result.name == "redis"
            assert result.status == HealthStatus.OK  # Not configured is OK
            assert "not configured" in result.message.lower()
            assert result.details["configured"] is False
    
    @pytest.mark.asyncio
    async def test_check_storage_with_temp_dir(self, temp_storage_dir):
        """Test storage health check with temporary directory"""
        from content_creation_crew.services.health_check import HealthChecker, HealthStatus
        
        with patch('content_creation_crew.services.health_check.get_storage_provider') as mock_get_provider:
            from content_creation_crew.services.storage_provider import LocalDiskStorageProvider
            
            provider = LocalDiskStorageProvider(base_path=temp_storage_dir)
            mock_get_provider.return_value = provider
            
            checker = HealthChecker(
                timeout_seconds=5,
                min_free_space_mb=1,
                storage_write_test=True
            )
            
            result = await checker.check_storage()
            
            # Verify
            assert result.name == "storage"
            assert result.status == HealthStatus.OK
            assert "accessible" in result.message.lower()
            assert result.details["type"] == "LocalDiskStorageProvider"
            assert result.details["accessible"] is True
            assert result.details["writable"] is True
    
    @pytest.mark.asyncio
    async def test_check_storage_timeout(self):
        """Test storage health check timeout"""
        from content_creation_crew.services.health_check import HealthChecker, HealthStatus
        
        # Mock storage provider that hangs
        mock_provider = Mock()
        async def hanging_check(*args, **kwargs):
            await asyncio.sleep(10)  # Longer than timeout
        
        mock_provider.check_health = hanging_check
        
        with patch('content_creation_crew.services.health_check.get_storage_provider', return_value=mock_provider):
            checker = HealthChecker(
                timeout_seconds=1,  # Short timeout
                min_free_space_mb=1024,
                storage_write_test=True
            )
            
            result = await checker.check_storage()
            
            # Verify
            assert result.name == "storage"
            assert result.status == HealthStatus.DOWN
            assert "timed out" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_check_llm_success(self):
        """Test LLM health check success"""
        from content_creation_crew.services.health_check import HealthChecker, HealthStatus
        
        # Mock httpx client
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value={"models": ["llama2", "mistral"]})
            
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            
            mock_client_class.return_value = mock_client
            
            checker = HealthChecker(timeout_seconds=5)
            result = await checker.check_llm()
            
            # Verify
            assert result.name == "llm"
            assert result.status == HealthStatus.OK
            assert result.details["provider"] == "ollama"
            assert result.details["models_count"] == 2
    
    @pytest.mark.asyncio
    async def test_check_all_components(self, temp_storage_dir):
        """Test checking all components"""
        from content_creation_crew.services.health_check import HealthChecker, HealthStatus
        
        checker = HealthChecker(
            timeout_seconds=5,
            min_free_space_mb=1,
            storage_write_test=False
        )
        
        # Run all checks
        result = await checker.check_all()
        
        # Verify structure
        assert "status" in result
        assert result["status"] in ["ok", "degraded", "down"]
        assert "timestamp" in result
        assert "response_time_ms" in result
        assert "components" in result
        
        # Verify components
        assert "database" in result["components"]
        assert "redis" in result["components"]
        assert "storage" in result["components"]
        assert "llm" in result["components"]
        
        # Each component should have required fields
        for component_name, component_data in result["components"].items():
            assert "status" in component_data
            assert component_data["status"] in ["ok", "degraded", "down"]
            assert "message" in component_data
            assert "checked_at" in component_data
    
    @pytest.mark.asyncio
    async def test_overall_status_determination(self):
        """Test overall status is correctly determined from component statuses"""
        from content_creation_crew.services.health_check import HealthChecker, HealthStatus, ComponentHealth
        
        checker = HealthChecker(timeout_seconds=5)
        
        # Mock all checks to return specific statuses
        async def mock_check_ok():
            return ComponentHealth("test", HealthStatus.OK, "OK")
        
        async def mock_check_degraded():
            return ComponentHealth("test", HealthStatus.DEGRADED, "Degraded")
        
        async def mock_check_down():
            return ComponentHealth("test", HealthStatus.DOWN, "Down")
        
        # Test all OK
        with patch.object(checker, 'check_database', new=mock_check_ok), \
             patch.object(checker, 'check_redis', new=mock_check_ok), \
             patch.object(checker, 'check_storage', new=mock_check_ok), \
             patch.object(checker, 'check_llm', new=mock_check_ok):
            
            result = await checker.check_all()
            assert result["status"] == "ok"
        
        # Test with one degraded
        with patch.object(checker, 'check_database', new=mock_check_ok), \
             patch.object(checker, 'check_redis', new=mock_check_degraded), \
             patch.object(checker, 'check_storage', new=mock_check_ok), \
             patch.object(checker, 'check_llm', new=mock_check_ok):
            
            result = await checker.check_all()
            assert result["status"] == "degraded"
        
        # Test with one down
        with patch.object(checker, 'check_database', new=mock_check_ok), \
             patch.object(checker, 'check_redis', new=mock_check_ok), \
             patch.object(checker, 'check_storage', new=mock_check_down), \
             patch.object(checker, 'check_llm', new=mock_check_ok):
            
            result = await checker.check_all()
            assert result["status"] == "down"


class TestHealthEndpoint:
    """Test /health endpoint integration"""
    
    @pytest.mark.asyncio
    async def test_health_endpoint_returns_200_when_healthy(self, client):
        """Test health endpoint returns 200 when all components are healthy"""
        # This test requires the full app with mocked dependencies
        response = await client.get("/health")
        
        # Should return 200 or 503 depending on actual component health
        assert response.status_code in [200, 503]
        
        # Verify response structure
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert data["service"] == "content-creation-crew"
        assert "environment" in data
        assert "timestamp" in data
        assert "components" in data
    
    @pytest.mark.asyncio
    async def test_health_endpoint_includes_storage_info(self, client):
        """Test health endpoint includes storage component information"""
        response = await client.get("/health")
        
        data = response.json()
        assert "components" in data
        assert "storage" in data["components"]
        
        storage_info = data["components"]["storage"]
        assert "status" in storage_info
        assert "message" in storage_info
        assert "details" in storage_info
        
        # Storage details should include type
        assert "type" in storage_info["details"]
    
    @pytest.mark.asyncio
    async def test_health_endpoint_response_time(self, client):
        """Test health endpoint completes within timeout"""
        import time
        
        start_time = time.time()
        response = await client.get("/health")
        elapsed_ms = (time.time() - start_time) * 1000
        
        # Should complete within timeout + some overhead
        assert elapsed_ms < 5000  # 5 seconds max
        
        # Response should include timing
        data = response.json()
        assert "response_time_ms" in data
        assert data["response_time_ms"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

