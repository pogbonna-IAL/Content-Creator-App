#!/usr/bin/env python
"""
Test script to verify the API server is working correctly
"""
import requests
import json

API_URL = "http://localhost:8000"

def test_api():
    print("Testing Content Creation Crew API...")
    print(f"API URL: {API_URL}\n")
    
    # Test health endpoint
    print("1. Testing health endpoint...")
    try:
        response = requests.get(f"{API_URL}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}\n")
    except Exception as e:
        print(f"   Error: {e}\n")
        return
    
    # Test generate endpoint
    print("2. Testing generate endpoint...")
    test_topic = "Benefits of exercise"
    
    try:
        response = requests.post(
            f"{API_URL}/api/generate",
            json={"topic": test_topic},
            timeout=600  # 10 minute timeout
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Topic: {data.get('topic')}")
            print(f"   Content length: {len(data.get('content', ''))}")
            print(f"   Content preview (first 200 chars):")
            print(f"   {data.get('content', '')[:200]}...")
            print("\n✅ API is working correctly!")
        else:
            print(f"   Error: {response.text}")
    except requests.exceptions.Timeout:
        print("   Error: Request timed out (content generation took too long)")
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    test_api()

