"""
Test script for voiceover generation endpoint
Tests: job creation, voiceover generation, SSE events, and file download
"""
import sys
import os
import requests
import json
import time
from pathlib import Path

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpassword123"

def get_auth_token():
    """Get authentication token"""
    print("Getting auth token...")
    try:
        # Try login first
        response = requests.post(
            f"{API_BASE_URL}/api/auth/login",
            data={"username": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code == 200:
            data = response.json()
            # Token might be in cookie, try to get from response
            token = data.get("access_token")
            if token:
                return token
            # Or get from cookies
            cookies = response.cookies
            if "auth_token" in cookies:
                return cookies["auth_token"]
    except Exception as e:
        print(f"Login failed: {e}")
    
    # Try signup
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/auth/signup",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "full_name": "Test User"
            }
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                return token
    except Exception as e:
        print(f"Signup failed: {e}")
    
    return None

def test_voiceover_generation(token):
    """Test voiceover generation endpoint"""
    print("\n=== Testing Voiceover Generation ===")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Step 1: Create a job with audio content
    print("\n1. Creating job with audio content...")
    response = requests.post(
        f"{API_BASE_URL}/v1/content/generate",
        json={
            "topic": "Introduction to artificial intelligence",
            "content_types": ["audio"]
        },
        headers=headers
    )
    
    if response.status_code != 201:
        print(f"[ERROR] Failed to create job: {response.status_code}")
        print(response.text)
        return None
    
    job_data = response.json()
    job_id = job_data["id"]
    print(f"[OK] Job created: {job_id}")
    
    # Step 2: Wait for job to complete (or at least have audio artifact)
    print("\n2. Waiting for audio script generation...")
    max_wait = 300  # 5 minutes
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        response = requests.get(
            f"{API_BASE_URL}/v1/content/jobs/{job_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            job_data = response.json()
            status = job_data["status"]
            artifacts = job_data.get("artifacts", [])
            
            # Check if audio artifact exists
            audio_artifact = next((a for a in artifacts if a["type"] == "audio"), None)
            
            if audio_artifact:
                print(f"[OK] Audio script generated!")
                break
            
            if status == "failed":
                print(f"[ERROR] Job failed")
                return None
            
            print(f"  Status: {status}, Artifacts: {len(artifacts)}")
            time.sleep(2)
        else:
            print(f"[ERROR] Failed to get job status: {response.status_code}")
            return None
    
    if not audio_artifact:
        print("[ERROR] Audio script not generated in time")
        return None
    
    # Step 3: Generate voiceover
    print("\n3. Generating voiceover...")
    response = requests.post(
        f"{API_BASE_URL}/v1/content/voiceover",
        json={
            "job_id": job_id,
            "voice_id": "en_US-lessac-medium",
            "speed": 1.0
        },
        headers=headers
    )
    
    if response.status_code != 202:
        print(f"[ERROR] Failed to create voiceover: {response.status_code}")
        print(response.text)
        return None
    
    voiceover_data = response.json()
    voiceover_job_id = voiceover_data.get("job_id", job_id)
    print(f"[OK] Voiceover generation started: {voiceover_job_id}")
    
    # Step 4: Monitor SSE events
    print("\n4. Monitoring SSE events...")
    events_received = []
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/v1/content/jobs/{voiceover_job_id}/stream",
            headers=headers,
            stream=True,
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"[ERROR] Failed to connect to SSE stream: {response.status_code}")
            return None
        
        print("  Connected to SSE stream...")
        buffer = ""
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                buffer += line_str + "\n"
                
                if line_str.startswith("data:"):
                    try:
                        data_str = line_str[5:].strip()
                        event_data = json.loads(data_str)
                        event_type = event_data.get("type", "unknown")
                        events_received.append(event_type)
                        print(f"  Event: {event_type}")
                        
                        if event_type == "tts_completed":
                            print("[OK] TTS completed!")
                            break
                        elif event_type == "tts_failed":
                            print(f"[ERROR] TTS failed: {event_data.get('message')}")
                            return None
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        print(f"[ERROR] SSE stream error: {e}")
    
    # Step 5: Check for voiceover artifact
    print("\n5. Checking for voiceover artifact...")
    response = requests.get(
        f"{API_BASE_URL}/v1/content/jobs/{voiceover_job_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        job_data = response.json()
        artifacts = job_data.get("artifacts", [])
        voiceover_artifact = next((a for a in artifacts if a["type"] == "voiceover_audio"), None)
        
        if voiceover_artifact:
            print("[OK] Voiceover artifact found!")
            print(f"  Artifact ID: {voiceover_artifact['id']}")
            metadata = voiceover_artifact.get("metadata", {})
            print(f"  Duration: {metadata.get('duration_sec', 'N/A')}s")
            print(f"  Format: {metadata.get('format', 'N/A')}")
            print(f"  Storage URL: {voiceover_artifact.get('url', 'N/A')}")
            
            # Step 6: Test file download
            storage_url = voiceover_artifact.get("url")
            if storage_url:
                print("\n6. Testing file download...")
                download_url = f"{API_BASE_URL}{storage_url}"
                print(f"  Download URL: {download_url}")
                
                response = requests.get(download_url, headers=headers)
                
                if response.status_code == 200:
                    file_size = len(response.content)
                    print(f"[OK] File downloaded successfully!")
                    print(f"  File size: {file_size} bytes")
                    
                    # Save test file
                    test_file = Path("test_voiceover.wav")
                    test_file.write_bytes(response.content)
                    print(f"  Saved to: {test_file}")
                    
                    return True
                else:
                    print(f"[ERROR] Download failed: {response.status_code}")
                    return False
            else:
                print("[WARNING] No storage URL in artifact")
                return True
        else:
            print("[ERROR] Voiceover artifact not found")
            return False
    else:
        print(f"[ERROR] Failed to get job: {response.status_code}")
        return False

def main():
    print("=== Voiceover Endpoint Test ===")
    print(f"API URL: {API_BASE_URL}")
    
    # Get auth token
    token = get_auth_token()
    if not token:
        print("[ERROR] Failed to get authentication token")
        print("Make sure the API server is running and test user exists")
        sys.exit(1)
    
    print("[OK] Authentication successful")
    
    # Test voiceover generation
    success = test_voiceover_generation(token)
    
    if success:
        print("\n=== All Tests Passed! ===")
        sys.exit(0)
    else:
        print("\n=== Tests Failed ===")
        sys.exit(1)

if __name__ == "__main__":
    main()

