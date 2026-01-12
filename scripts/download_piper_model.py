"""
Download Piper TTS voice model from HuggingFace
"""
import os
import sys
import requests
from pathlib import Path

def download_file(url: str, output_path: Path):
    """Download a file with progress"""
    print(f"Downloading {url}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))
    downloaded = 0
    
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    print(f"\rProgress: {percent:.1f}%", end='', flush=True)
    
    print(f"\nDownloaded: {output_path}")

def main():
    # Model to download (en_US-lessac-medium)
    model_name = "en_US-lessac-medium"
    base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/"
    
    # Output directory
    output_dir = Path("models/piper")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Files to download
    files = [
        f"{model_name}.onnx",
        f"{model_name}.onnx.json"
    ]
    
    print(f"Downloading Piper voice model: {model_name}")
    print(f"Output directory: {output_dir}")
    
    for filename in files:
        url = base_url + filename
        output_path = output_dir / filename
        
        if output_path.exists():
            print(f"Skipping {filename} (already exists)")
            continue
        
        try:
            download_file(url, output_path)
        except Exception as e:
            print(f"Error downloading {filename}: {e}")
            sys.exit(1)
    
    print(f"\n✓ Model downloaded successfully!")
    print(f"Model files:")
    for filename in files:
        file_path = output_dir / filename
        if file_path.exists():
            size = file_path.stat().st_size / (1024 * 1024)  # MB
            print(f"  - {filename} ({size:.1f} MB)")

if __name__ == "__main__":
    main()

