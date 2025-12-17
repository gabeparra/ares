#!/bin/bash
# Setup script for Gemma 3 27B model in Ollama

set -e

echo "╔══════════════════════════════════════════════════════╗"
echo "║  Setting up Gemma 3 27B for Ollama                  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Check if Ollama is running
echo "[1/3] Checking Ollama..."
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠ Ollama is not running. Starting Ollama..."
    ollama serve &
    sleep 3
fi

if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✓ Ollama is running"
else
    echo "✗ Failed to start Ollama. Please start it manually:"
    echo "   ollama serve"
    exit 1
fi

# Ask user which size they want
echo ""
echo "[2/3] Select Gemma 3 model:"
echo ""
echo "1. Gemma 3 1B   - Smallest (~2GB)   - Fast, good for testing"
echo "2. Gemma 3 4B   - Small (~8GB)      - Balanced, recommended for most users"
echo "3. Gemma 3 4B Abliterated (UNCENSORED) - Small (~8GB) - Uncensored version, removes refusals"
echo "4. Gemma 3 12B  - Medium (~24GB)    - Better quality, needs more VRAM"
echo "5. Gemma 3 27B  - Large (~50GB+)    - Best quality, needs 24GB+ VRAM"
echo ""
read -p "Enter choice (1-5, default: 3): " size_choice
size_choice=${size_choice:-3}

case $size_choice in
    1)
        MODEL_SIZE="1b"
        MODEL_NAMES=("gemma3:1b" "gemma3:1b-it" "gemma-3-1b-it")
        SIZE_DESC="1B (~2GB)"
        FROM_HF=""
        ;;
    2)
        MODEL_SIZE="4b"
        MODEL_NAMES=("gemma3:4b" "gemma3:4b-it" "gemma-3-4b-it")
        SIZE_DESC="4B (~8GB)"
        FROM_HF=""
        ;;
    3)
        MODEL_SIZE="4b-abliterated"
        MODEL_NAMES=("gemma3:4b-abliterated")
        SIZE_DESC="4B Abliterated UNCENSORED (~8GB)"
        FROM_HF="mlabonne/gemma-3-4b-it-abliterated"
        ;;
    4)
        MODEL_SIZE="12b"
        MODEL_NAMES=("gemma3:12b" "gemma3:12b-it" "gemma-3-12b-it")
        SIZE_DESC="12B (~24GB)"
        FROM_HF=""
        ;;
    5)
        MODEL_SIZE="27b"
        MODEL_NAMES=("gemma3:27b" "gemma3:27b-it" "gemma-3-27b-it")
        SIZE_DESC="27B (~50GB+)"
        FROM_HF=""
        ;;
    *)
        MODEL_SIZE="4b-abliterated"
        MODEL_NAMES=("gemma3:4b-abliterated")
        SIZE_DESC="4B Abliterated UNCENSORED (~8GB)"
        FROM_HF="mlabonne/gemma-3-4b-it-abliterated"
        ;;
esac

echo ""
echo "Pulling Gemma 3 $SIZE_DESC model..."
echo "This may take a while depending on your internet connection..."
echo ""

for model_name in "${MODEL_NAMES[@]}"; do
    echo "Trying to pull: $model_name"
    if ollama pull "$model_name" 2>&1 | tee /tmp/ollama_pull.log; then
        echo ""
        echo "✓ Successfully pulled: $model_name"
        SELECTED_MODEL="$model_name"
        break
    else
        if grep -q "model not found" /tmp/ollama_pull.log 2>/dev/null; then
            echo "  Model name '$model_name' not found, trying next..."
            continue
        else
            echo "  Error pulling model, but continuing..."
            continue
        fi
    fi
done

if [ -z "$SELECTED_MODEL" ]; then
    echo ""
    echo "⚠ Could not find Gemma 3 $MODEL_SIZE in Ollama's default library."
    echo ""
    
    # If it's the abliterated version, create it from Hugging Face
    if [ -n "$FROM_HF" ]; then
        echo "Creating uncensored Gemma 3 4B Abliterated from Hugging Face..."
        echo ""
        cat > /tmp/Modelfile << EOF
FROM huggingface/$FROM_HF
PARAMETER temperature 1.0
PARAMETER top_k 64
PARAMETER top_p 0.95
EOF
        if ollama create gemma3:4b-abliterated -f /tmp/Modelfile; then
            SELECTED_MODEL="gemma3:4b-abliterated"
            echo "✓ Successfully created uncensored Gemma 3 4B Abliterated model"
        else
            echo "⚠ Failed to create from Hugging Face. You may need to:"
            echo "   1. Accept the Gemma license on Hugging Face"
            echo "   2. Set HUGGING_FACE_HUB_TOKEN in your environment"
            echo ""
            echo "   export HUGGING_FACE_HUB_TOKEN=your_token_here"
            echo "   Then run this script again"
        fi
        rm -f /tmp/Modelfile
    else
        echo "You can try:"
        echo "1. Check available Gemma models: ollama list | grep gemma"
        echo "2. Pull from Hugging Face manually:"
        echo "   Create a Modelfile with:"
        echo "   FROM huggingface/google/gemma-3-4b-it"
        echo "   Then run: ollama create gemma3:4b -f Modelfile"
        echo ""
        echo "3. Or use an available Gemma model:"
        echo "   ollama pull gemma2:2b    # Small (~1.4GB)"
        echo "   ollama pull gemma2:7b    # Medium (~5GB)"
        echo "   ollama pull gemma2:27b   # Large (~16GB)"
        echo ""
        read -p "Enter a model name to use (or press Enter to skip): " manual_model
        if [ -n "$manual_model" ]; then
            SELECTED_MODEL="$manual_model"
            ollama pull "$SELECTED_MODEL" || echo "Warning: Could not pull $SELECTED_MODEL"
        fi
    fi
fi

# Update .env file
if [ -n "$SELECTED_MODEL" ]; then
    echo ""
    echo "[3/3] Updating configuration..."
    
    if [ -f .env ]; then
        # Update existing OLLAMA_MODEL if present, or add it
        if grep -q "^OLLAMA_MODEL=" .env; then
            sed -i "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=$SELECTED_MODEL|" .env
            echo "✓ Updated OLLAMA_MODEL in .env"
        else
            echo "OLLAMA_MODEL=$SELECTED_MODEL" >> .env
            echo "✓ Added OLLAMA_MODEL to .env"
        fi
    else
        echo "OLLAMA_MODEL=$SELECTED_MODEL" > .env
        echo "✓ Created .env with OLLAMA_MODEL"
    fi
    
    echo ""
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║  Setup Complete!                                    ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo ""
    echo "Model configured: $SELECTED_MODEL"
    echo ""
    echo "Next steps:"
    echo "1. Restart your backend server:"
    echo "   python -m caption_ai --web --port 8000"
    echo ""
    echo "2. Or change the model in the web UI Settings tab"
    echo ""
else
    echo ""
    echo "⚠ No model was configured. You can manually set OLLAMA_MODEL in .env"
fi

