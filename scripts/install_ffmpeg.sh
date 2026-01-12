#!/bin/bash
# FFmpeg installation script for Linux/macOS

set -e

echo "FFmpeg Installation Script"
echo "========================="
echo ""

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Detected: Linux"
    
    # Check for package manager
    if command -v apt-get &> /dev/null; then
        echo "Installing FFmpeg using apt-get..."
        sudo apt-get update
        sudo apt-get install -y ffmpeg
    elif command -v dnf &> /dev/null; then
        echo "Installing FFmpeg using dnf..."
        sudo dnf install -y ffmpeg
    elif command -v pacman &> /dev/null; then
        echo "Installing FFmpeg using pacman..."
        sudo pacman -S --noconfirm ffmpeg
    elif command -v yum &> /dev/null; then
        echo "Installing FFmpeg using yum..."
        sudo yum install -y ffmpeg
    else
        echo "ERROR: Could not detect package manager"
        echo "Please install FFmpeg manually: https://ffmpeg.org/download.html"
        exit 1
    fi
    
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Detected: macOS"
    
    if command -v brew &> /dev/null; then
        echo "Installing FFmpeg using Homebrew..."
        brew install ffmpeg
    else
        echo "ERROR: Homebrew not found"
        echo "Install Homebrew: https://brew.sh/"
        echo "Or download FFmpeg from: https://evermeet.cx/ffmpeg/"
        exit 1
    fi
    
else
    echo "ERROR: Unsupported OS: $OSTYPE"
    echo "Please install FFmpeg manually: https://ffmpeg.org/download.html"
    exit 1
fi

echo ""
echo "Verifying installation..."
if command -v ffmpeg &> /dev/null; then
    ffmpeg -version | head -n 1
    echo ""
    echo "[OK] FFmpeg installed successfully!"
else
    echo "[ERROR] FFmpeg installation failed"
    exit 1
fi

