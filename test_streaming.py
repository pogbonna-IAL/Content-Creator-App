#!/usr/bin/env python
"""Test the streaming endpoint directly"""
import requests
import json

API_URL = "http://localhost:8000"

def test_streaming():
    print("Testing streaming endpoint...")
    print(f"API URL: {API_URL}\n")
    
    topic = "Benefits of exercise"
    
    try:
        response = requests.post(
            f"{API_URL}/api/generate",
            json={"topic": topic},
            stream=True,
            timeout=600
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        print("\nStreaming data:\n" + "="*60)
        
        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    print(decoded)
                    if decoded.startswith('data: '):
                        try:
                            data = json.loads(decoded[6:])
                            if data.get('type') == 'complete':
                                print(f"\n✓ Complete! Content length: {len(data.get('content', ''))}")
                                print(f"Content preview: {data.get('content', '')[:200]}")
                                break
                        except:
                            pass
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_streaming()

