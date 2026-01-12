"""
Test script for TTS provider
"""
import sys
import os
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from content_creation_crew.services.tts_provider import PiperTTSProvider
from content_creation_crew.services.storage_provider import LocalDiskStorageProvider

def test_tts():
    """Test TTS synthesis"""
    print("Testing Piper TTS Provider...")
    
    # Initialize provider
    provider = PiperTTSProvider()
    
    if not provider.is_available():
        print("[ERROR] Piper TTS is not available")
        print("Available voices:", provider.get_available_voices())
        return False
    
    print("[OK] Piper TTS is available")
    print(f"Available voices: {provider.get_available_voices()}")
    
    # Test synthesis
    test_text = "Hello, this is a test of the text to speech system."
    print(f"\nSynthesizing: '{test_text}'")
    
    try:
        audio_bytes, metadata = provider.synthesize(
            text=test_text,
            voice_id="en_US-lessac-medium",
            speed=1.0,
            format="wav"
        )
        
        print(f"[OK] Synthesis successful!")
        print(f"  Duration: {metadata['duration_sec']:.2f} seconds")
        print(f"  Sample rate: {metadata['sample_rate']} Hz")
        print(f"  Format: {metadata['format']}")
        print(f"  Audio size: {len(audio_bytes)} bytes")
        
        # Test storage
        print("\nTesting storage...")
        storage = LocalDiskStorageProvider()
        storage_key = storage.generate_key('voiceovers', '.wav')
        storage_url = storage.put(storage_key, audio_bytes, content_type='audio/wav')
        
        print(f"[OK] Storage successful!")
        print(f"  Storage key: {storage_key}")
        print(f"  Storage URL: {storage_url}")
        print(f"  File path: {storage.base_path / storage_key}")
        
        # Verify file exists
        file_path = storage.base_path / storage_key
        if file_path.exists():
            file_size = file_path.stat().st_size
            print(f"  File size: {file_size} bytes")
            print(f"[OK] File saved successfully!")
            return True
        else:
            print("[ERROR] File not found after saving")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_tts()
    sys.exit(0 if success else 1)

