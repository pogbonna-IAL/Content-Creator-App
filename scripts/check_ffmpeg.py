"""
Check if FFmpeg is installed and available
"""
import subprocess
import sys
import platform

def check_ffmpeg():
    """Check if FFmpeg is available"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            # Extract version from output
            version_line = result.stdout.decode('utf-8').split('\n')[0]
            print(f"[OK] FFmpeg is installed: {version_line}")
            return True
        else:
            print("[ERROR] FFmpeg command failed")
            return False
    except FileNotFoundError:
        print("[ERROR] FFmpeg is not installed or not in PATH")
        return False
    except subprocess.TimeoutExpired:
        print("[ERROR] FFmpeg check timed out")
        return False
    except Exception as e:
        print(f"[ERROR] Error checking FFmpeg: {e}")
        return False

def get_installation_instructions():
    """Get platform-specific installation instructions"""
    system = platform.system().lower()
    
    instructions = {
        'windows': """
Windows Installation:
1. Download FFmpeg from: https://www.gyan.dev/ffmpeg/builds/
2. Extract the zip file
3. Add the 'bin' folder to your system PATH:
   - Open System Properties > Environment Variables
   - Edit PATH variable
   - Add: C:\\path\\to\\ffmpeg\\bin
4. Or use Chocolatey: choco install ffmpeg
5. Or use winget: winget install ffmpeg
""",
        'darwin': """
macOS Installation:
1. Using Homebrew: brew install ffmpeg
2. Or download from: https://evermeet.cx/ffmpeg/
""",
        'linux': """
Linux Installation:
1. Ubuntu/Debian: sudo apt-get update && sudo apt-get install ffmpeg
2. Fedora: sudo dnf install ffmpeg
3. Arch: sudo pacman -S ffmpeg
4. Or compile from source: https://ffmpeg.org/download.html
"""
    }
    
    return instructions.get(system, "Please install FFmpeg from https://ffmpeg.org/download.html")

if __name__ == "__main__":
    print("Checking FFmpeg installation...")
    print()
    
    if check_ffmpeg():
        print()
        print("[OK] FFmpeg is ready to use!")
        sys.exit(0)
    else:
        print()
        print("=" * 60)
        print("FFmpeg Installation Instructions")
        print("=" * 60)
        print(get_installation_instructions())
        print("=" * 60)
        sys.exit(1)

