#!/usr/bin/env python
"""
Quick script to check if API server is running and accessible
"""
import requests
import sys

API_URL = "http://localhost:8000"

def check_server():
    """Check if the API server is running"""
    try:
        print(f"Checking API server at {API_URL}...")
        
        # Check health endpoint
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✓ API server is running and accessible")
            print(f"  Response: {response.json()}")
            return True
        else:
            print(f"✗ API server returned status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to API server at {API_URL}")
        print("  The server is not running or not accessible.")
        print("\n  To start the server, run:")
        print("    uv run python api_server.py")
        return False
    except Exception as e:
        print(f"✗ Error checking server: {e}")
        return False

def test_signup_endpoint():
    """Test if signup endpoint is accessible"""
    try:
        print(f"\nTesting signup endpoint at {API_URL}/api/auth/signup...")
        response = requests.options(
            f"{API_URL}/api/auth/signup",
            headers={
                'Origin': 'http://localhost:3000',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type',
            },
            timeout=5
        )
        print(f"  CORS preflight status: {response.status_code}")
        print(f"  CORS headers: {dict(response.headers)}")
        return True
    except Exception as e:
        print(f"  Error testing endpoint: {e}")
        return False

if __name__ == "__main__":
    if check_server():
        test_signup_endpoint()
    sys.exit(0 if check_server() else 1)

