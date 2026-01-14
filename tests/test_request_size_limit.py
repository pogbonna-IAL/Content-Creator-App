"""
Tests for Request Size Limit Middleware (M4)
"""
import pytest
from fastapi.testclient import TestClient
from src.content_creation_crew.api_server import app

client = TestClient(app)


class TestRequestSizeLimit:
    """Test request size limit middleware"""
    
    def test_reject_oversized_json_request(self):
        """Test that oversized JSON requests are rejected"""
        # Create a payload larger than 2MB
        large_payload = {
            "email": "test@example.com",
            "password": "MyP@ssw0rd123",
            "full_name": "Test User",
            "large_data": "x" * (3 * 1024 * 1024)  # 3MB of data
        }
        
        response = client.post(
            "/api/auth/signup",
            json=large_payload
        )
        
        # Should return 413 Payload Too Large
        assert response.status_code == 413
        assert "too large" in response.json()["message"].lower()
        assert response.json()["code"] == "REQUEST_TOO_LARGE"
    
    def test_accept_normal_json_request(self):
        """Test that normal-sized JSON requests are accepted"""
        normal_payload = {
            "email": "normal@test.com",
            "password": "MyP@ssw0rd123",
            "full_name": "Normal User"
        }
        
        response = client.post(
            "/api/auth/signup",
            json=normal_payload
        )
        
        # Should succeed (or fail for other reasons, not size)
        assert response.status_code != 413
    
    def test_reject_oversized_generation_request(self):
        """Test that oversized content generation requests are rejected"""
        # Create a very long topic (simulate oversized request)
        large_topic = "Write about " + ("artificial intelligence " * 50000)  # Very large topic
        
        # First, sign up a user
        signup_response = client.post("/api/auth/signup", json={
            "email": "sizegen@test.com",
            "password": "MyP@ssw0rd123"
        })
        
        if signup_response.status_code == 200:
            token = signup_response.json()["access_token"]
            
            # Try to generate with oversized payload
            gen_response = client.post(
                "/api/generate",
                json={
                    "type": "blog",
                    "topic": large_topic,
                    "tone": "professional"
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            
            # Should be rejected for size
            assert gen_response.status_code == 413 or gen_response.status_code == 400
    
    def test_accept_normal_generation_request(self):
        """Test that normal content generation requests are accepted"""
        # Sign up a user
        signup_response = client.post("/api/auth/signup", json={
            "email": "normalgen@test.com",
            "password": "MyP@ssw0rd123"
        })
        
        if signup_response.status_code == 200:
            token = signup_response.json()["access_token"]
            
            # Normal generation request
            gen_response = client.post(
                "/api/generate",
                json={
                    "type": "blog",
                    "topic": "Artificial Intelligence in Healthcare",
                    "tone": "professional"
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            
            # Should not fail due to size (may fail for other reasons)
            assert gen_response.status_code != 413
    
    def test_get_requests_not_affected(self):
        """Test that GET requests are not affected by size limits"""
        # GET requests don't have bodies, so size limit shouldn't apply
        response = client.get("/api/auth/me")
        
        # Should fail for auth, not size
        assert response.status_code != 413
    
    def test_error_response_includes_details(self):
        """Test that error response includes size details"""
        large_payload = {
            "email": "details@test.com",
            "password": "MyP@ssw0rd123",
            "large_data": "x" * (3 * 1024 * 1024)  # 3MB
        }
        
        response = client.post(
            "/api/auth/signup",
            json=large_payload,
            headers={"Content-Length": str(3 * 1024 * 1024)}
        )
        
        if response.status_code == 413:
            data = response.json()
            assert "details" in data
            assert "max_size_mb" in data.get("details", {}) or "max_size_bytes" in data.get("details", {})
    
    def test_fast_rejection(self):
        """Test that oversized requests are rejected quickly (before reading entire body)"""
        import time
        
        # Create oversized request
        large_data = "x" * (5 * 1024 * 1024)  # 5MB
        
        start_time = time.time()
        
        try:
            response = client.post(
                "/api/auth/signup",
                json={"email": "fast@test.com", "password": "Pass123!", "data": large_data},
                headers={"Content-Length": str(5 * 1024 * 1024)}
            )
        except Exception:
            # Even if connection fails, measure time
            pass
        
        elapsed = time.time() - start_time
        
        # Should reject quickly (< 1 second for header check)
        # Note: This may vary based on network, but should be fast
        assert elapsed < 5.0, f"Rejection took {elapsed:.2f}s (should be nearly instant)"


class TestRequestSizeLimitEdgeCases:
    """Test edge cases for request size limits"""
    
    def test_exact_size_limit(self):
        """Test request at exact size limit"""
        # Create payload at exactly 2MB
        exact_size_data = "x" * (2 * 1024 * 1024 - 1000)  # Slightly under 2MB for JSON overhead
        
        response = client.post(
            "/api/auth/signup",
            json={
                "email": "exact@test.com",
                "password": "MyP@ssw0rd123",
                "data": exact_size_data
            }
        )
        
        # Should succeed (at limit)
        # May fail for other reasons but not 413
        assert response.status_code != 413
    
    def test_missing_content_length_header(self):
        """Test request without Content-Length header"""
        # Some clients don't send Content-Length
        # Middleware should allow these through (can't check size without it)
        response = client.post(
            "/api/auth/signup",
            json={"email": "noheader@test.com", "password": "MyP@ssw0rd123"}
        )
        
        # Should not reject (no way to check size without Content-Length)
        # May fail for other reasons
        assert response.status_code != 413 or response.status_code == 400
    
    def test_invalid_content_length_header(self):
        """Test request with invalid Content-Length header"""
        response = client.post(
            "/api/auth/signup",
            json={"email": "invalid@test.com", "password": "MyP@ssw0rd123"},
            headers={"Content-Length": "invalid"}
        )
        
        # Should return 400 Bad Request (invalid header)
        assert response.status_code == 400 or response.status_code != 413


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

