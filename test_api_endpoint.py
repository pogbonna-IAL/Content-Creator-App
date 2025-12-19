#!/usr/bin/env python
"""Test the API endpoint directly"""
import requests
import json
import time

API_URL = "http://localhost:8000"

def test_api():
    print("Testing API endpoint...")
    print(f"API URL: {API_URL}\n")
    
    # Test health first
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        print(f"✓ Health check: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        print("Make sure the API server is running: uv run python api_server.py")
        return
    
    # Test generate endpoint
    print("\nTesting /api/generate endpoint...")
    test_topic = "Benefits of meditation"
    
    try:
        print(f"Sending request for topic: '{test_topic}'")
        response = requests.post(
            f"{API_URL}/api/generate",
            json={"topic": test_topic},
            timeout=600  # 10 minute timeout
        )
        
        print(f"\nResponse status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response keys: {list(data.keys())}")
            print(f"Topic: {data.get('topic')}")
            print(f"Content length: {len(data.get('content', ''))}")
            print(f"\nContent preview (first 300 chars):")
            print("-" * 60)
            print(data.get('content', '')[:300])
            print("-" * 60)
            print("\n✓ API is working correctly!")
        else:
            print(f"✗ Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Error text: {response.text}")
    except requests.exceptions.Timeout:
        print("✗ Request timed out")
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    test_api()

