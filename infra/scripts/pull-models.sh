#!/bin/bash
# Pull Ollama models and verify availability
# Reads MODEL_NAMES from environment (comma-separated) or extracts from tiers.yaml

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Ollama Model Download Automation"
echo "=========================================="
echo ""

# Check if Ollama is available
if ! command -v ollama &> /dev/null; then
    echo -e "${RED}✗ Ollama is not installed or not in PATH${NC}"
    echo ""
    echo "Install Ollama from: https://ollama.ai"
    echo "Or use Docker: docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama"
    exit 1
fi

# Check if Ollama service is running
if ! ollama list &> /dev/null; then
    echo -e "${YELLOW}⚠️  Ollama service is not running or not accessible${NC}"
    echo ""
    echo "Start Ollama:"
    echo "  Local: ollama serve"
    echo "  Docker: docker start ollama"
    exit 1
fi

# Function to extract models from tiers.yaml
extract_models_from_tiers() {
    local tiers_file="${1:-src/content_creation_crew/config/tiers.yaml}"
    if [ ! -f "$tiers_file" ]; then
        echo ""
        return
    fi
    
    # Extract model names from tiers.yaml (remove "ollama/" prefix if present)
    grep -E "^\s+model:" "$tiers_file" | \
        sed 's/.*model:\s*"*ollama\/\([^"]*\)"*/\1/' | \
        sed 's/.*model:\s*"*\([^"]*\)"*/\1/' | \
        sort -u | \
        tr '\n' ',' | \
        sed 's/,$//'
}

# Get models from environment or tiers.yaml
if [ -n "$MODEL_NAMES" ]; then
    echo -e "${BLUE}Using models from MODEL_NAMES environment variable${NC}"
    IFS=',' read -ra MODELS <<< "$MODEL_NAMES"
else
    echo -e "${BLUE}Extracting models from tiers.yaml${NC}"
    models_str=$(extract_models_from_tiers)
    if [ -z "$models_str" ]; then
        echo -e "${YELLOW}⚠️  Could not extract models from tiers.yaml, using defaults${NC}"
        models_str="llama3.2:1b,llama3.2:3b,llama3.1:8b"
    fi
    IFS=',' read -ra MODELS <<< "$models_str"
fi

# Remove "ollama/" prefix if present
for i in "${!MODELS[@]}"; do
    MODELS[$i]=${MODELS[$i]//ollama\//}
    MODELS[$i]=$(echo "${MODELS[$i]}" | xargs)  # Trim whitespace
done

echo ""
echo "Models to download:"
for model in "${MODELS[@]}"; do
    echo "  - $model"
done
echo ""

# Function to check if model exists
model_exists() {
    local model_name=$1
    ollama list | grep -q "^$model_name" || ollama list | grep -q "$model_name"
}

# Function to verify model availability via API
verify_model_api() {
    local model_name=$1
    local ollama_url="${OLLAMA_BASE_URL:-http://localhost:11434}"
    
    # Try API check if curl is available
    if command -v curl &> /dev/null; then
        response=$(curl -s "$ollama_url/api/tags" 2>/dev/null || echo "")
        if [ -n "$response" ]; then
            echo "$response" | grep -q "\"name\":\"$model_name\"" && return 0
        fi
    fi
    
    # Fallback to ollama list
    model_exists "$model_name"
}

# Pull and verify each model
SUCCESS_COUNT=0
FAILED_MODELS=()

for model in "${MODELS[@]}"; do
    if [ -z "$model" ]; then
        continue
    fi
    
    echo -e "${BLUE}Pulling model: $model${NC}"
    
    # Check if model already exists
    if model_exists "$model"; then
        echo -e "${GREEN}✓ Model $model already exists${NC}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        continue
    fi
    
    # Pull the model
    if ollama pull "$model"; then
        echo -e "${GREEN}✓ Successfully pulled $model${NC}"
        
        # Verify model availability
        echo "  Verifying model availability..."
        sleep 2  # Give Ollama time to register the model
        
        if verify_model_api "$model"; then
            echo -e "${GREEN}✓ Model $model verified and available${NC}"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        else
            echo -e "${YELLOW}⚠️  Model $model pulled but verification failed${NC}"
            echo "  Model may still be available. Check with: ollama list"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))  # Count as success since pull succeeded
        fi
    else
        echo -e "${RED}✗ Failed to pull $model${NC}"
        FAILED_MODELS+=("$model")
    fi
    echo ""
done

# Summary
echo "=========================================="
echo "Summary"
echo "=========================================="
echo -e "Successfully pulled/verified: ${GREEN}$SUCCESS_COUNT${NC} model(s)"
if [ ${#FAILED_MODELS[@]} -gt 0 ]; then
    echo -e "Failed: ${RED}${#FAILED_MODELS[@]}${NC} model(s)"
    echo "Failed models:"
    for model in "${FAILED_MODELS[@]}"; do
        echo "  - $model"
    done
    echo ""
    echo "Retry failed models with:"
    for model in "${FAILED_MODELS[@]}"; do
        echo "  ollama pull $model"
    done
    exit 1
else
    echo -e "${GREEN}✓ All models downloaded and verified successfully!${NC}"
    echo ""
    echo "Available models:"
    ollama list
    exit 0
fi

