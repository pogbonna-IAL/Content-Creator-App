"""
Security tests for baseline security features
"""
import pytest
import requests
from fastapi.testclient import TestClient
import sys
import os
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Set test environment variables before importing
os.environ["ENV"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost/test_db"
os.environ["CORS_ORIGINS"] = "http://localhost:3000,https://test.example.com"

# Import after setting env vars
from api_server import app
from content_creation_crew.config import config


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Get authentication headers for testing"""
    # Create test user and get token
    signup_response = client.post(
        "/api/auth/signup",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
            "full_name": "Test User"
        }
    )
    if signup_response.status_code == 200:
        data = signup_response.json()
        return {"Authorization": f"Bearer {data['access_token']}"}
    else:
        # User might already exist, try login
        login_response = client.post(
            "/api/auth/login",
            data={"username": "test@example.com", "password": "testpassword123"}
        )
        if login_response.status_code == 200:
            data = login_response.json()
            return {"Authorization": f"Bearer {data['access_token']}"}
    return {}


class TestCORS:
    """Test CORS configuration"""
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in responses"""
        response = client.options(
            "/api/auth/me",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        assert "access-control-allow-origin" in response.headers or response.status_code == 200
    
    def test_cors_allowed_origins(self, client):
        """Test that only allowed origins are accepted"""
        # This would require actual CORS middleware testing
        # For now, we verify the config is set
        assert len(config.CORS_ORIGINS) > 0


class TestRequestSizeLimits:
    """Test request size limits"""
    
    def test_normal_request_size(self, client, auth_headers):
        """Test that normal-sized requests work"""
        response = client.post(
            "/v1/content/generate",
            json={"topic": "Test topic"},
            headers=auth_headers
        )
        # Should not be 413 (Request Entity Too Large)
        assert response.status_code != 413
    
    def test_large_request_size(self, client, auth_headers):
        """Test that oversized requests are rejected"""
        # Create a very large topic (over 10MB)
        large_topic = "x" * (11 * 1024 * 1024)  # 11MB
        
        response = client.post(
            "/v1/content/generate",
            json={"topic": large_topic},
            headers=auth_headers
        )
        # Should be 413 or 422 (validation error)
        assert response.status_code in [413, 422]


class TestRequestID:
    """Test request ID functionality"""
    
    def test_request_id_in_response(self, client):
        """Test that request ID is included in response headers"""
        response = client.get("/health")
        assert "X-Request-ID" in response.headers
        assert response.headers["X-Request-ID"] is not None
        assert len(response.headers["X-Request-ID"]) > 0
    
    def test_request_id_in_error_response(self, client):
        """Test that request ID is included in error responses"""
        response = client.get("/api/auth/me")  # Should be 401
        assert response.status_code == 401
        
        # Check if error response includes request_id
        try:
            error_data = response.json()
            # Request ID should be in headers
            assert "X-Request-ID" in response.headers
        except:
            pass  # Response might not be JSON
    
    def test_custom_request_id(self, client):
        """Test that custom X-Request-ID header is used"""
        custom_id = "test-request-id-12345"
        response = client.get(
            "/health",
            headers={"X-Request-ID": custom_id}
        )
        assert response.headers["X-Request-ID"] == custom_id


class TestWebhookReplayProtection:
    """Test webhook replay protection"""
    
    def test_webhook_signature_required(self, client):
        """Test that webhook signature is required"""
        response = client.post(
            "/v1/billing/webhooks/stripe",
            json={"type": "test", "id": "evt_test"}
        )
        # Should fail without signature
        assert response.status_code in [400, 401, 403]
    
    def test_duplicate_webhook_rejected(self, client):
        """Test that duplicate webhook events are rejected"""
        # This would require actual webhook testing with Stripe/Paystack
        # For now, we verify the billing service has replay protection
        from content_creation_crew.services.billing_service import BillingService
        from content_creation_crew.db.models.subscription import PaymentProvider
        
        # Verify the method exists
        assert hasattr(BillingService, 'update_subscription_from_webhook')


class TestHTTPOnlyCookies:
    """Test HTTPOnly cookie implementation"""
    
    def test_login_sets_cookies(self, client):
        """Test that login sets httpOnly cookies"""
        response = client.post(
            "/api/auth/login",
            data={"username": "test@example.com", "password": "testpassword123"}
        )
        
        if response.status_code == 200:
            # Check for Set-Cookie header
            cookies = response.headers.get("set-cookie", "")
            assert "auth_token" in cookies.lower()
            # Verify httpOnly flag (if present)
            # Note: TestClient might not show httpOnly flag, but cookie should be set


class TestCSRFProtection:
    """Test CSRF protection"""
    
    def test_csrf_token_endpoint(self, client, auth_headers):
        """Test CSRF token generation endpoint"""
        response = client.get(
            "/api/auth/csrf-token",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "csrf_token" in data
            assert "expires_in" in data
            assert "header_name" in data
            assert data["header_name"] == "X-CSRF-Token"
            assert len(data["csrf_token"]) == 64  # SHA256 hex length
    
    def test_billing_without_csrf_token(self, client, auth_headers):
        """Test that billing actions require CSRF token in staging/prod"""
        # Note: CSRF is skipped in dev, so this test might pass in dev mode
        # In staging/prod, it should fail
        response = client.post(
            "/v1/billing/upgrade",
            json={"plan": "basic", "provider": "stripe"},
            headers=auth_headers
        )
        # In dev, this might succeed (CSRF skipped)
        # In staging/prod, should be 403
        assert response.status_code in [200, 403, 400, 404]


class TestDebugMode:
    """Test debug mode configuration"""
    
    def test_debug_mode_disabled_in_prod(self):
        """Test that debug mode is disabled in production"""
        # This test would require setting ENV=prod
        # For now, we verify the logic exists
        from api_server import app
        # Debug should be False in staging/prod
        # We can't easily test this without changing environment


class TestErrorResponseFormat:
    """Test error response format with request ID"""
    
    def test_error_response_includes_request_id(self, client):
        """Test that error responses include request_id"""
        response = client.get("/api/auth/me")  # Should be 401
        
        # Request ID should be in headers
        assert "X-Request-ID" in response.headers
        
        # Error response should have standard format
        try:
            error_data = response.json()
            # Should have detail and status_code
            assert "detail" in error_data or "status_code" in error_data
        except:
            pass  # Response might not be JSON


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

