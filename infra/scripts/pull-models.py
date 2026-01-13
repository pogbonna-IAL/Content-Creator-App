#!/usr/bin/env python3
"""
Pull Ollama models and verify availability
Reads MODEL_NAMES from environment (comma-separated) or extracts from tiers.yaml
"""
import os
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import List, Tuple

# Colors for terminal output
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_colored(message: str, color: str = Colors.NC):
    """Print colored message"""
    print(f"{color}{message}{Colors.NC}")

def check_ollama_available() -> bool:
    """Check if Ollama command is available"""
    try:
        subprocess.run(["ollama", "--version"], 
                     capture_output=True, 
                     check=True,
                     timeout=5)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False

def check_ollama_running() -> bool:
    """Check if Ollama service is running"""
    try:
        result = subprocess.run(["ollama", "list"],
                              capture_output=True,
                              timeout=10)
        return result.returncode == 0
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False

def extract_models_from_tiers(tiers_file: str = None) -> List[str]:
    """Extract model names from tiers.yaml"""
    if tiers_file is None:
        # Try to find tiers.yaml relative to script location
        script_dir = Path(__file__).parent.parent.parent
        tiers_file = script_dir / "src" / "content_creation_crew" / "config" / "tiers.yaml"
    
    if not Path(tiers_file).exists():
        return []
    
    try:
        import yaml
        with open(tiers_file, 'r') as f:
            config = yaml.safe_load(f)
        
        models = set()
        tiers = config.get('tiers', {})
        for tier_name, tier_config in tiers.items():
            model = tier_config.get('model', '')
            if model:
                # Remove "ollama/" prefix if present
                model = model.replace('ollama/', '').strip()
                if model:
                    models.add(model)
        
        return sorted(list(models))
    except Exception as e:
        print_colored(f"⚠️  Error extracting models from tiers.yaml: {e}", Colors.YELLOW)
        return []

def get_models() -> List[str]:
    """Get list of models from environment or tiers.yaml"""
    # Check environment variable first
    model_names = os.getenv("MODEL_NAMES", "")
    if model_names:
        print_colored("Using models from MODEL_NAMES environment variable", Colors.BLUE)
        models = [m.strip().replace('ollama/', '') for m in model_names.split(',') if m.strip()]
        return models
    
    # Extract from tiers.yaml
    print_colored("Extracting models from tiers.yaml", Colors.BLUE)
    models = extract_models_from_tiers()
    if not models:
        print_colored("⚠️  Could not extract models from tiers.yaml, using defaults", Colors.YELLOW)
        models = ["llama3.2:1b", "llama3.2:3b", "llama3.1:8b"]
    
    return models

def model_exists(model_name: str) -> bool:
    """Check if model exists locally"""
    try:
        result = subprocess.run(["ollama", "list"],
                              capture_output=True,
                              text=True,
                              timeout=10)
        if result.returncode == 0:
            return model_name in result.stdout
    except Exception:
        pass
    return False

def verify_model_api(model_name: str) -> bool:
    """Verify model availability via Ollama API"""
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    try:
        import urllib.request
        import urllib.error
        
        with urllib.request.urlopen(f"{ollama_url}/api/tags", timeout=5) as response:
            data = json.loads(response.read())
            models = data.get('models', [])
            for model in models:
                if model.get('name') == model_name:
                    return True
    except Exception:
        pass
    
    # Fallback to local check
    return model_exists(model_name)

def pull_model(model_name: str) -> Tuple[bool, str]:
    """Pull a model and return (success, message)"""
    print_colored(f"Pulling model: {model_name}", Colors.BLUE)
    
    # Check if already exists
    if model_exists(model_name):
        return True, f"Model {model_name} already exists"
    
    # Pull the model
    try:
        process = subprocess.Popen(
            ["ollama", "pull", model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Stream output
        for line in process.stdout:
            print(f"  {line.rstrip()}")
        
        process.wait()
        
        if process.returncode == 0:
            # Give Ollama time to register the model
            time.sleep(2)
            
            # Verify
            if verify_model_api(model_name):
                return True, f"Model {model_name} pulled and verified"
            else:
                return True, f"Model {model_name} pulled but verification uncertain"
        else:
            return False, f"Failed to pull {model_name}"
    except Exception as e:
        return False, f"Error pulling {model_name}: {str(e)}"

def main():
    """Main function"""
    print("=" * 50)
    print("Ollama Model Download Automation")
    print("=" * 50)
    print()
    
    # Check Ollama availability
    if not check_ollama_available():
        print_colored("✗ Ollama is not installed or not in PATH", Colors.RED)
        print()
        print("Install Ollama from: https://ollama.ai")
        print("Or use Docker: docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama")
        sys.exit(1)
    
    # Check if Ollama is running
    if not check_ollama_running():
        print_colored("⚠️  Ollama service is not running or not accessible", Colors.YELLOW)
        print()
        print("Start Ollama:")
        print("  Local: ollama serve")
        print("  Docker: docker start ollama")
        sys.exit(1)
    
    # Get models
    models = get_models()
    
    print()
    print("Models to download:")
    for model in models:
        print(f"  - {model}")
    print()
    
    # Pull and verify models
    success_count = 0
    failed_models = []
    
    for model in models:
        if not model:
            continue
        
        success, message = pull_model(model)
        
        if success:
            print_colored(f"✓ {message}", Colors.GREEN)
            success_count += 1
        else:
            print_colored(f"✗ {message}", Colors.RED)
            failed_models.append(model)
        print()
    
    # Summary
    print("=" * 50)
    print("Summary")
    print("=" * 50)
    print_colored(f"Successfully pulled/verified: {success_count} model(s)", Colors.GREEN if success_count > 0 else Colors.RED)
    
    if failed_models:
        print_colored(f"Failed: {len(failed_models)} model(s)", Colors.RED)
        print("Failed models:")
        for model in failed_models:
            print(f"  - {model}")
        print()
        print("Retry failed models with:")
        for model in failed_models:
            print(f"  ollama pull {model}")
        sys.exit(1)
    else:
        print_colored("✓ All models downloaded and verified successfully!", Colors.GREEN)
        print()
        print("Available models:")
        try:
            subprocess.run(["ollama", "list"], check=True)
        except Exception:
            pass
        sys.exit(0)

if __name__ == "__main__":
    main()

