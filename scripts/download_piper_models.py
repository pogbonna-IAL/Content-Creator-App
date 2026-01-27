#!/usr/bin/env python3
"""
Download Piper TTS voice models from HuggingFace
This script downloads default voice models for use in production
"""
import os
import sys
import urllib.request
import urllib.error

def download_piper_model(voice_id: str, output_dir: str) -> bool:
    """
    Download a Piper voice model from HuggingFace
    
    Args:
        voice_id: Voice identifier (e.g., 'en_US-lessac-medium')
        output_dir: Directory to save the model
    
    Returns:
        True if download succeeded, False otherwise
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Piper voices are hosted on HuggingFace
    base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
    
    # Try different possible paths
    possible_paths = [
        f"{voice_id}/model.onnx",  # Directory format
        f"{voice_id}.onnx",  # Direct file format
    ]
    
    for model_path in possible_paths:
        model_url = f"{base_url}/{model_path}"
        
        # Determine local path
        if '/' in model_path:
            voice_dir = os.path.join(output_dir, voice_id)
            os.makedirs(voice_dir, exist_ok=True)
            local_path = os.path.join(voice_dir, "model.onnx")
        else:
            local_path = os.path.join(output_dir, f"{voice_id}.onnx")
        
        # Skip if already exists
        if os.path.exists(local_path) and os.path.getsize(local_path) > 1000:
            print(f"✓ Model already exists: {local_path}")
            return True
        
        try:
            print(f"Downloading {voice_id} from {model_url}...")
            
            def show_progress(block_num, block_size, total_size):
                if total_size > 0:
                    percent = min(100, (block_num * block_size * 100) // total_size)
                    if block_num % 100 == 0:  # Show progress every 100 blocks
                        print(f"  Progress: {percent}%", end='\r')
            
            urllib.request.urlretrieve(model_url, local_path, show_progress)
            print()  # New line after progress
            
            # Verify download
            if os.path.exists(local_path) and os.path.getsize(local_path) > 1000:
                file_size = os.path.getsize(local_path)
                print(f"✓ Successfully downloaded {voice_id} ({file_size:,} bytes) to {local_path}")
                return True
            else:
                print(f"✗ Downloaded file too small, removing...")
                if os.path.exists(local_path):
                    os.remove(local_path)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"✗ Model not found at {model_url} (404)")
            else:
                print(f"✗ HTTP error {e.code}: {e.reason}")
        except Exception as e:
            print(f"✗ Error downloading {model_url}: {e}")
    
    return False


if __name__ == "__main__":
    # Default voice model to download
    default_voice = "en_US-lessac-medium"
    output_dir = os.getenv("PIPER_MODEL_PATH", "/app/models/piper")
    
    # Allow voice ID from command line
    voice_id = sys.argv[1] if len(sys.argv) > 1 else default_voice
    
    print(f"Downloading Piper TTS model: {voice_id}")
    print(f"Output directory: {output_dir}")
    
    success = download_piper_model(voice_id, output_dir)
    
    if success:
        print(f"\n✓ Model download completed successfully!")
        sys.exit(0)
    else:
        print(f"\n✗ Failed to download model {voice_id}")
        print("Note: Models will be downloaded automatically on first use if download fails here.")
        sys.exit(1)
