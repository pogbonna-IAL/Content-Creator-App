#!/usr/bin/env python3
"""
Download Piper TTS voice models from HuggingFace
This script downloads default voice models for use in production
"""
import os
import sys
import urllib.request
import urllib.error

# Set UTF-8 encoding for stdout to handle Unicode characters
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

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
    # The repository structure uses hyphens in directory names
    # Voice IDs like "en_US-lessac-medium" become "en-US-lessac-medium" in URLs
    base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
    
    # Local path always uses voice_id format (underscores) for consistency
    local_path = os.path.join(output_dir, f"{voice_id}.onnx")
    
    # Convert voice_id to HuggingFace format (underscores to hyphens)
    # en_US-lessac-medium -> en-US-lessac-medium
    voice_id_hyphen = voice_id.replace('_', '-')
    
    # Try different possible paths based on actual HuggingFace structure
    # The repository uses directory structure: en-US-lessac-medium/model.onnx
    possible_paths = [
        f"{voice_id_hyphen}/model.onnx",  # Directory format (most common)
        f"{voice_id_hyphen}/en_US-lessac-medium.onnx",  # Alternative directory format
        f"{voice_id_hyphen}.onnx",  # Direct file format
    ]
    
    # Also try using piper-tts library download function first (most reliable)
    try:
        from piper import download_voice
        print(f"[INFO] Attempting to download {voice_id} using piper-tts library...")
        try:
            voice_path = download_voice(voice_id, output_dir)
            if voice_path and os.path.exists(voice_path):
                file_size = os.path.getsize(voice_path)
                if file_size > 1000:
                    # Copy to expected location if different
                    if voice_path != local_path:
                        import shutil
                        if os.path.exists(local_path):
                            os.remove(local_path)
                        shutil.copy2(voice_path, local_path)
                    if os.path.exists(local_path):
                        final_size = os.path.getsize(local_path)
                        print(f"[OK] Successfully downloaded {voice_id} ({final_size:,} bytes) via piper-tts")
                        return True
        except Exception as lib_error:
            print(f"[INFO] piper-tts library download failed: {lib_error}")
            print(f"[INFO] Falling back to direct HuggingFace download...")
    except ImportError:
        print(f"[INFO] piper-tts library not available, using direct download...")
    
    # Skip if already exists
    if os.path.exists(local_path) and os.path.getsize(local_path) > 1000:
        file_size = os.path.getsize(local_path)
        print(f"[OK] Model already exists: {local_path} ({file_size:,} bytes)")
        return True
    
    for model_path in possible_paths:
        model_url = f"{base_url}/{model_path}"
        
        try:
            print(f"Attempting to download {voice_id} from {model_url}...")
            
            # Download to temporary file first
            temp_path = local_path + '.tmp'
            
            def show_progress(block_num, block_size, total_size):
                if total_size > 0:
                    percent = min(100, (block_num * block_size * 100) // total_size)
                    if block_num % 100 == 0:  # Show progress every 100 blocks
                        print(f"  Progress: {percent}%", end='\r', flush=True)
            
            urllib.request.urlretrieve(model_url, temp_path, show_progress)
            print()  # New line after progress
            
            # Verify download
            if os.path.exists(temp_path):
                file_size = os.path.getsize(temp_path)
                if file_size > 1000:  # At least 1KB
                    # Move temp file to final location
                    if os.path.exists(local_path):
                        os.remove(local_path)
                    os.rename(temp_path, local_path)
                    
                    # Verify final file
                    if os.path.exists(local_path):
                        final_size = os.path.getsize(local_path)
                        print(f"[OK] Successfully downloaded {voice_id} ({final_size:,} bytes) to {local_path}")
                        return True
                    else:
                        print(f"[ERROR] Failed to move temp file to final location")
                else:
                    print(f"[ERROR] Downloaded file too small ({file_size} bytes), removing...")
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            else:
                print(f"[ERROR] Download completed but file not found at temp path")
                
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"[WARN] Model not found at {model_url} (404)")
            else:
                print(f"[ERROR] HTTP error {e.code}: {e.reason}")
            # Clean up temp file if exists
            temp_path = local_path + '.tmp'
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
        except Exception as e:
            print(f"[ERROR] Error downloading {model_url}: {e}")
            # Clean up temp file if exists
            temp_path = local_path + '.tmp'
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
    
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
        print(f"\n[SUCCESS] Model download completed successfully!")
        sys.exit(0)
    else:
        print(f"\n[FAILED] Failed to download model {voice_id}")
        print("[INFO] Note: Models will be downloaded automatically on first use if download fails here.")
        sys.exit(1)
