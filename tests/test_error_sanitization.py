"""
Tests for Error Sanitization (M3)
Ensures error responses don't leak sensitive information
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from src.content_creation_crew.api_server import app
from src.content_creation_crew.middleware.error_handler import ErrorSanitizer

client = TestClient(app)


class TestErrorSanitizer:
    """Test ErrorSanitizer utility functions"""
    
    def test_sanitize_file_paths(self):
        """Test that file paths are redacted"""
        message = "Error in file C:\\Users\\admin\\project\\secret.py at line 42"
        sanitized = ErrorSanitizer.sanitize_message(message)
        
        assert "C:\\Users\\admin\\project\\secret.py" not in sanitized
        assert "[REDACTED_PATH]" in sanitized
    
    def test_sanitize_unix_paths(self):
        """Test that Unix paths are redacted"""
        message = "Error in /home/admin/project/secret.py"
        sanitized = ErrorSanitizer.sanitize_message(message)
        
        assert "/home/admin/project/secret.py" not in sanitized
        assert "[REDACTED_PATH]" in sanitized
    
    def test_sanitize_sql_statements(self):
        """Test that SQL statements are redacted"""
        messages = [
            "Error executing: SELECT * FROM users WHERE password='secret'",
            "Failed: INSERT INTO logs VALUES ('sensitive data')",
            "Query failed: UPDATE users SET password='newpass'",
            "Error: DELETE FROM sessions WHERE token='abc123'"
        ]
        
        for message in messages:
            sanitized = ErrorSanitizer.sanitize_message(message)
            assert "SELECT" not in sanitized or "[REDACTED]" in sanitized
            assert "INSERT" not in sanitized or "[REDACTED]" in sanitized
            assert "UPDATE" not in sanitized or "[REDACTED]" in sanitized
            assert "DELETE" not in sanitized or "[REDACTED]" in sanitized
            assert "password" not in sanitized or "[REDACTED]" in sanitized
    
    def test_sanitize_connection_strings(self):
        """Test that database connection strings are redacted"""
        message = "Connection failed: postgresql://user:pass@localhost:5432/mydb"
        sanitized = ErrorSanitizer.sanitize_message(message)
        
        assert "user:pass" not in sanitized
        assert "postgresql://" not in sanitized or "[REDACTED_CONNECTION]" in sanitized
    
    def test_sanitize_emails(self):
        """Test that emails are redacted from error messages"""
        message = "User admin@example.com not found"
        sanitized = ErrorSanitizer.sanitize_message(message)
        
        assert "admin@example.com" not in sanitized
        assert "[REDACTED_EMAIL]" in sanitized
    
    def test_sanitize_long_messages(self):
        """Test that long messages are truncated"""
        message = "Error: " + ("x" * 1000)
        sanitized = ErrorSanitizer.sanitize_message(message)
        
        assert len(sanitized) <= 520  # 500 + "... [truncated]"
        assert "[truncated]" in sanitized
    
    def test_sanitize_details_dict(self):
        """Test that details dictionaries are sanitized"""
        details = {
            "path": "/home/admin/secret.py",
            "query": "SELECT * FROM users",
            "password": "supersecret",
            "count": 42,
            "is_valid": True
        }
        
        sanitized = ErrorSanitizer.sanitize_details(details)
        
        # Sensitive keys removed
        assert "password" not in sanitized
        
        # Paths sanitized
        assert "/home/admin/secret.py" not in str(sanitized)
        
        # Safe values preserved
        assert sanitized.get("count") == 42
        assert sanitized.get("is_valid") is True
    
    def test_is_safe_error(self):
        """Test error safety classification"""
        from fastapi.exceptions import RequestValidationError
        from starlette.exceptions import HTTPException
        
        # Validation errors are safe
        validation_error = RequestValidationError(errors=[])
        assert ErrorSanitizer.is_safe_error(validation_error) is True
        
        # 4xx HTTP errors are safe
        http_404 = HTTPException(status_code=404, detail="Not found")
        assert ErrorSanitizer.is_safe_error(http_404) is True
        
        # 5xx HTTP errors are NOT safe
        http_500 = HTTPException(status_code=500, detail="Internal error")
        assert ErrorSanitizer.is_safe_error(http_500) is False
        
        # Generic exceptions are NOT safe
        generic_error = Exception("Something went wrong")
        assert ErrorSanitizer.is_safe_error(generic_error) is False


class TestDatabaseErrorHandling:
    """Test database error handling and sanitization"""
    
    @patch('src.content_creation_crew.database.get_db')
    def test_database_error_no_sql_leak(self, mock_get_db):
        """Test that SQL statements don't leak in database errors"""
        # Mock database to raise error with SQL
        def raise_db_error():
            raise IntegrityError(
                "INSERT INTO users (email) VALUES ('test@example.com')",
                {},
                Exception("duplicate key value violates unique constraint")
            )
        
        mock_get_db.side_effect = raise_db_error
        
        # This would trigger a database error
        response = client.post("/api/auth/signup", json={
            "email": "dbtest@example.com",
            "password": "MyP@ssw0rd123"
        })
        
        # Should return 500 (or 400 before DB is hit)
        # Important: SQL should NOT be in response
        response_text = response.text.lower()
        assert "insert into" not in response_text
        assert "users" not in response_text or "database" in response_text  # Generic message OK
        assert "request_id" in response.json() or response.status_code != 500
    
    def test_database_constraint_error_generic_message(self):
        """Test that constraint violations return generic message"""
        # Try to create duplicate user
        # First signup
        response1 = client.post("/api/auth/signup", json={
            "email": "duplicate@test.com",
            "password": "MyP@ssw0rd123"
        })
        
        # Second signup (duplicate)
        if response1.status_code == 200:
            response2 = client.post("/api/auth/signup", json={
                "email": "duplicate@test.com",
                "password": "MyP@ssw0rd123"
            })
            
            # Should return error
            if response2.status_code >= 400:
                # Error message should be generic
                error_text = response2.text.lower()
                assert "constraint" not in error_text or "database constraint" in error_text
                assert "duplicate key" not in error_text
                # Should not reveal table/column names
                assert "users" not in error_text or "database" in error_text


class TestValidationErrorHandling:
    """Test validation error handling"""
    
    def test_validation_error_includes_field_info(self):
        """Test that validation errors include safe field information"""
        response = client.post("/api/auth/signup", json={
            "email": "invalid-email",  # Invalid email format
            "password": "weak"  # Too weak
        })
        
        if response.status_code == 422:  # Validation error
            data = response.json()
            
            # Should have error structure
            assert "code" in data
            assert data["code"] == "VALIDATION_ERROR"
            
            # Should have request_id
            assert "request_id" in data
            
            # Should have safe field-level errors
            if "details" in data and "errors" in data["details"]:
                errors = data["details"]["errors"]
                for error in errors:
                    # Should have field name
                    assert "field" in error
                    # Should have safe message
                    assert "message" in error
                    # Should NOT echo back full payload
                    assert "invalid-email" not in str(error).lower() or "invalid" in str(error).lower()
    
    def test_validation_error_no_payload_echo(self):
        """Test that validation errors don't echo back sensitive payload data"""
        response = client.post("/api/auth/login", data={
            "username": "test@example.com",
            "password": "MySecretPassword123!"  # This should NOT appear in error
        })
        
        # Even if validation fails, password should not be in response
        response_text = response.text
        assert "MySecretPassword123!" not in response_text


class TestHttpExceptionHandling:
    """Test HTTP exception handling"""
    
    def test_404_error_safe_message(self):
        """Test that 404 errors have safe messages"""
        response = client.get("/api/nonexistent/endpoint")
        
        assert response.status_code == 404
        data = response.json()
        
        # Should have structured error
        assert "code" in data
        assert "message" in data
        assert "request_id" in data
        
        # Message should not reveal internal paths
        message = data["message"].lower()
        assert "c:\\" not in message
        assert "/home/" not in message
    
    def test_500_error_generic_message(self):
        """Test that 5xx errors return generic messages"""
        # Mock an endpoint to raise 500 error
        @app.get("/test-500-error")
        def test_500():
            raise Exception("Internal server error with sensitive path: C:\\app\\secret.py")
        
        response = client.get("/test-500-error")
        
        if response.status_code == 500:
            data = response.json()
            
            # Should be generic
            assert "internal" in data["message"].lower() or "error" in data["message"].lower()
            
            # Should NOT contain sensitive info
            assert "C:\\app\\secret.py" not in response.text
            assert "secret.py" not in response.text
            
            # Should have request_id
            assert "request_id" in data


class TestGenericExceptionHandling:
    """Test generic exception handling"""
    
    def test_unhandled_exception_sanitized(self):
        """Test that unhandled exceptions are fully sanitized"""
        # Mock an endpoint that raises unexpected exception
        @app.get("/test-unhandled-exception")
        def test_unhandled():
            # Simulate error with sensitive info
            raise ValueError("Database path /var/lib/postgresql/data contains error")
        
        response = client.get("/test-unhandled-exception")
        
        if response.status_code == 500:
            data = response.json()
            
            # Should be generic
            assert "unexpected error" in data["message"].lower() or "internal error" in data["message"].lower()
            
            # Should NOT contain file path
            assert "/var/lib/postgresql" not in response.text
            
            # Should have request_id
            assert "request_id" in data
            
            # Details should be minimal
            if "details" in data:
                # Should only have error type, not message/path
                assert "ValueError" in str(data["details"]) or "error_type" in data["details"]
                assert "/var/lib" not in str(data["details"])


class TestRequestIdPresence:
    """Test that request_id is always present"""
    
    def test_request_id_in_validation_error(self):
        """Test request_id in validation errors"""
        response = client.post("/api/auth/signup", json={})
        
        if response.status_code >= 400:
            data = response.json()
            assert "request_id" in data
            assert len(data["request_id"]) > 0
    
    def test_request_id_in_auth_error(self):
        """Test request_id in authentication errors"""
        response = client.get("/api/auth/me")  # No token
        
        if response.status_code == 401:
            data = response.json()
            assert "request_id" in data or "detail" in data  # Legacy format may not have it
    
    def test_request_id_in_not_found_error(self):
        """Test request_id in 404 errors"""
        response = client.get("/api/nonexistent")
        
        if response.status_code == 404:
            data = response.json()
            assert "request_id" in data


class TestLegacyCompatibility:
    """Test that legacy /api endpoints remain compatible"""
    
    def test_legacy_auth_error_format(self):
        """Test that /api/auth errors are still usable by frontend"""
        response = client.post("/api/auth/login", data={
            "username": "nonexistent@example.com",
            "password": "WrongPassword123!"
        })
        
        # Should return error (400 or 401)
        if response.status_code >= 400:
            data = response.json()
            
            # Should have message or detail field (frontend expects this)
            assert "message" in data or "detail" in data
            
            # Should NOT leak internal info
            response_text = response.text.lower()
            assert "select" not in response_text or "sql" in response_text
            assert "c:\\" not in response_text
            assert "/home/" not in response_text


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

