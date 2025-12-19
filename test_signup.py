#!/usr/bin/env python
"""
Test script for signup endpoint
"""
import requests
import json

API_URL = "http://localhost:8000"

def test_signup():
    """Test the signup endpoint"""
    url = f"{API_URL}/api/auth/signup"
    
    test_data = {
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    }
    
    print(f"Testing signup endpoint: {url}")
    print(f"Data: {json.dumps(test_data, indent=2)}")
    
    try:
        response = requests.post(
            url,
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        try:
            response_data = response.json()
            print(f"Response JSON: {json.dumps(response_data, indent=2)}")
        except:
            print(f"Response Text: {response.text}")
            
        if response.status_code == 200:
            print("\n✓ Signup successful!")
            return True
        else:
            print(f"\n✗ Signup failed with status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"\n✗ Connection error: Could not connect to {API_URL}")
        print("Make sure the API server is running: uv run python api_server.py")
        return False
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        return False

if __name__ == "__main__":
    test_signup()

