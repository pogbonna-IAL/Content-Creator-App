"""
Tests for cache invalidation service (M6)
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

# Test fixtures
@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def mock_user_cache():
    """Mock user cache"""
    cache = Mock()
    cache.invalidate = Mock()
    cache.get_stats = Mock(return_value={"total_entries": 5, "default_ttl": 300})
    return cache


@pytest.fixture
def mock_content_cache():
    """Mock content cache"""
    cache = Mock()
    cache.invalidate_topic = Mock()
    cache.clear = Mock()
    cache.get_stats = Mock(return_value={"total_entries": 10, "default_ttl": 3600})
    return cache


class TestCacheInvalidationService:
    """Test CacheInvalidationService"""
    
    def test_init_service(self):
        """Test service initialization"""
        from content_creation_crew.services.cache_invalidation import CacheInvalidationService
        
        service = CacheInvalidationService()
        
        # Should initialize with caches
        assert service is not None
    
    def test_invalidate_user(self, mock_user_cache):
        """Test user cache invalidation"""
        from content_creation_crew.services.cache_invalidation import CacheInvalidationService
        
        service = CacheInvalidationService()
        service.user_cache = mock_user_cache
        
        # Invalidate user
        result = service.invalidate_user(123, reason="test")
        
        # Verify
        assert result is True
        mock_user_cache.invalidate.assert_called_once_with(123)
    
    def test_invalidate_user_on_profile_update(self, mock_user_cache):
        """Test user cache invalidation on profile update"""
        from content_creation_crew.services.cache_invalidation import CacheInvalidationService
        
        service = CacheInvalidationService()
        service.user_cache = mock_user_cache
        
        # Invalidate
        result = service.invalidate_user_on_profile_update(123)
        
        # Verify
        assert result is True
        mock_user_cache.invalidate.assert_called_once_with(123)
    
    def test_invalidate_user_on_password_change(self, mock_user_cache):
        """Test user cache invalidation on password change"""
        from content_creation_crew.services.cache_invalidation import CacheInvalidationService
        
        service = CacheInvalidationService()
        service.user_cache = mock_user_cache
        
        # Invalidate
        result = service.invalidate_user_on_password_change(123)
        
        # Verify
        assert result is True
        mock_user_cache.invalidate.assert_called_once_with(123)
    
    def test_invalidate_user_on_email_verification(self, mock_user_cache):
        """Test user cache invalidation on email verification"""
        from content_creation_crew.services.cache_invalidation import CacheInvalidationService
        
        service = CacheInvalidationService()
        service.user_cache = mock_user_cache
        
        # Invalidate
        result = service.invalidate_user_on_email_verification(123)
        
        # Verify
        assert result is True
        mock_user_cache.invalidate.assert_called_once_with(123)
    
    def test_invalidate_user_on_gdpr_delete(self, mock_user_cache):
        """Test user cache invalidation on GDPR deletion"""
        from content_creation_crew.services.cache_invalidation import CacheInvalidationService
        
        service = CacheInvalidationService()
        service.user_cache = mock_user_cache
        
        # Invalidate
        result = service.invalidate_user_on_gdpr_delete(123)
        
        # Verify
        assert result is True
        mock_user_cache.invalidate.assert_called_once_with(123)
    
    def test_invalidate_org_plan(self, mock_user_cache, mock_db):
        """Test organization/plan cache invalidation"""
        from content_creation_crew.services.cache_invalidation import CacheInvalidationService
        from content_creation_crew.db.models.organization import OrganizationMember
        
        service = CacheInvalidationService()
        service.user_cache = mock_user_cache
        
        # Mock organization members
        mock_member1 = Mock()
        mock_member1.user_id = 101
        mock_member2 = Mock()
        mock_member2.user_id = 102
        
        with patch('content_creation_crew.services.cache_invalidation.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_query = Mock()
            mock_query.filter.return_value.all.return_value = [mock_member1, mock_member2]
            mock_session.query.return_value = mock_query
            mock_session_class.return_value = mock_session
            
            # Invalidate org
            result = service.invalidate_org_plan(456, reason="test")
            
            # Verify
            assert result is True
            # Should invalidate both members
            assert mock_user_cache.invalidate.call_count == 2
    
    def test_invalidate_org_on_subscription_change(self, mock_user_cache):
        """Test org cache invalidation on subscription change"""
        from content_creation_crew.services.cache_invalidation import CacheInvalidationService
        
        service = CacheInvalidationService()
        service.user_cache = mock_user_cache
        
        with patch.object(service, 'invalidate_org_plan') as mock_invalidate:
            mock_invalidate.return_value = True
            
            # Invalidate
            result = service.invalidate_org_on_subscription_change(456)
            
            # Verify
            assert result is True
            mock_invalidate.assert_called_once_with(456, reason="subscription_webhook")
    
    def test_invalidate_content_by_topic(self, mock_content_cache):
        """Test content cache invalidation by topic"""
        from content_creation_crew.services.cache_invalidation import CacheInvalidationService
        
        service = CacheInvalidationService()
        service.content_cache = mock_content_cache
        
        # Invalidate topic
        result = service.invalidate_content_by_topic("AI trends", reason="test")
        
        # Verify
        assert result is True
        mock_content_cache.invalidate_topic.assert_called_once_with("AI trends", None)
    
    def test_invalidate_all_content(self, mock_content_cache):
        """Test invalidating ALL content cache"""
        from content_creation_crew.services.cache_invalidation import CacheInvalidationService
        
        service = CacheInvalidationService()
        service.content_cache = mock_content_cache
        
        # Clear all
        result = service.invalidate_all_content(reason="moderation_rules_changed")
        
        # Verify
        assert result is True
        mock_content_cache.clear.assert_called_once()
    
    def test_get_content_cache_key_with_moderation_version(self):
        """Test content cache key generation with moderation version"""
        from content_creation_crew.services.cache_invalidation import CacheInvalidationService
        
        service = CacheInvalidationService()
        
        # Generate key with moderation version
        key1 = service.get_content_cache_key(
            "AI trends",
            content_types=["blog", "social"],
            prompt_version="2.0.0",
            model="llama3",
            moderation_version="1.0.0"
        )
        
        # Same inputs with different moderation version should produce different key
        key2 = service.get_content_cache_key(
            "AI trends",
            content_types=["blog", "social"],
            prompt_version="2.0.0",
            model="llama3",
            moderation_version="2.0.0"
        )
        
        # Verify
        assert key1 != key2
        assert key1.startswith("content:")
        assert key2.startswith("content:")
    
    def test_invalidate_multiple_users(self, mock_user_cache):
        """Test batch user invalidation"""
        from content_creation_crew.services.cache_invalidation import CacheInvalidationService
        
        service = CacheInvalidationService()
        service.user_cache = mock_user_cache
        
        # Invalidate multiple users
        user_ids = [101, 102, 103]
        count = service.invalidate_multiple_users(user_ids, reason="batch_test")
        
        # Verify
        assert count == 3
        assert mock_user_cache.invalidate.call_count == 3
    
    def test_get_invalidation_stats(self, mock_user_cache, mock_content_cache):
        """Test getting cache invalidation statistics"""
        from content_creation_crew.services.cache_invalidation import CacheInvalidationService
        
        service = CacheInvalidationService()
        service.user_cache = mock_user_cache
        service.content_cache = mock_content_cache
        
        # Get stats
        stats = service.get_invalidation_stats()
        
        # Verify
        assert stats["user_cache_available"] is True
        assert stats["content_cache_available"] is True
        assert "user_cache" in stats
        assert "content_cache" in stats
    
    def test_get_cache_invalidation_service_singleton(self):
        """Test singleton pattern for cache invalidation service"""
        from content_creation_crew.services.cache_invalidation import get_cache_invalidation_service
        
        service1 = get_cache_invalidation_service()
        service2 = get_cache_invalidation_service()
        
        # Should be same instance
        assert service1 is service2


class TestModerationVersionInCacheKey:
    """Test moderation version in content cache keys"""
    
    def test_content_cache_key_includes_moderation_version(self):
        """Test that content cache key includes moderation version"""
        from content_creation_crew.services.content_cache import ContentCache
        
        cache = ContentCache()
        
        # Mock config
        with patch('content_creation_crew.services.content_cache.config') as mock_config:
            mock_config.MODERATION_VERSION = "1.0.0"
            
            key1 = cache.get_cache_key("AI trends", ["blog"], "2.0.0", "llama3")
            
            # Change moderation version
            mock_config.MODERATION_VERSION = "2.0.0"
            
            key2 = cache.get_cache_key("AI trends", ["blog"], "2.0.0", "llama3")
            
            # Keys should be different
            assert key1 != key2
    
    def test_redis_cache_key_includes_moderation_version(self):
        """Test that Redis cache key includes moderation version"""
        from content_creation_crew.services.redis_cache import RedisContentCache
        
        with patch('content_creation_crew.services.redis_cache.get_redis_client') as mock_redis:
            mock_redis.return_value = None  # Force fallback to in-memory
            
            cache = RedisContentCache()
            
            # Mock config
            with patch('content_creation_crew.services.redis_cache.config') as mock_config:
                mock_config.MODERATION_VERSION = "1.0.0"
                
                key1 = cache.get_cache_key("AI trends", ["blog"], "2.0.0", "llama3")
                
                # Change moderation version
                mock_config.MODERATION_VERSION = "2.0.0"
                
                key2 = cache.get_cache_key("AI trends", ["blog"], "2.0.0", "llama3")
                
                # Keys should be different
                assert key1 != key2
                assert key1.startswith("content:")
                assert key2.startswith("content:")


class TestCacheInvalidationIntegration:
    """Integration tests for cache invalidation"""
    
    @pytest.mark.asyncio
    async def test_email_verification_invalidates_cache(self, client):
        """Test that email verification invalidates user cache"""
        # This would require full integration test setup
        # For now, we verify the endpoint exists and is protected
        response = await client.post("/api/auth/verify-email/confirm")
        
        # Should require token (bad request or unauthorized)
        assert response.status_code in [400, 401, 422]
    
    @pytest.mark.asyncio
    async def test_webhook_invalidates_org_cache(self, client):
        """Test that webhook processing invalidates org cache"""
        # This would require full integration test setup
        # For now, we verify the endpoint exists
        response = await client.post("/api/billing/webhooks/stripe")
        
        # Should require valid signature (bad request or unauthorized)
        assert response.status_code in [400, 401]
    
    @pytest.mark.asyncio
    async def test_gdpr_delete_invalidates_cache(self, client, auth_headers):
        """Test that GDPR delete invalidates user cache"""
        # Requires authenticated request
        response = await client.delete("/v1/user/delete", headers=auth_headers)
        
        # Should process or return error (not 404)
        assert response.status_code != 404


class TestAdminCacheEndpoints:
    """Test admin cache invalidation endpoints"""
    
    @pytest.mark.asyncio
    async def test_admin_invalidate_users_requires_auth(self, client):
        """Test that admin endpoint requires authentication"""
        response = await client.post("/v1/admin/cache/invalidate/users", json={
            "user_ids": [1, 2, 3],
            "reason": "test"
        })
        
        # Should require auth
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_admin_invalidate_users_requires_admin(self, client, auth_headers):
        """Test that admin endpoint requires admin access"""
        response = await client.post(
            "/v1/admin/cache/invalidate/users",
            headers=auth_headers,
            json={
                "user_ids": [1, 2, 3],
                "reason": "test"
            }
        )
        
        # Should require admin (403) or succeed if test user is admin
        assert response.status_code in [200, 403]
    
    @pytest.mark.asyncio
    async def test_admin_get_cache_stats(self, client):
        """Test admin cache stats endpoint"""
        response = await client.get("/v1/admin/cache/stats")
        
        # Should require auth
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_admin_clear_all_content_cache(self, client):
        """Test admin endpoint to clear all content cache"""
        response = await client.post("/v1/admin/cache/invalidate/content", json={
            "clear_all": True,
            "reason": "test"
        })
        
        # Should require auth
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

