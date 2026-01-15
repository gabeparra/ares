#!/bin/bash
# Rebuild Ares model with HERETIC IQ4_NL quantization
# Run this script ON THE 4090 RIG where Ollama is installed

set -e

echo "╔══════════════════════════════════════════════════════╗"
echo "║  Rebuilding Ares with HERETIC IQ4_NL Model          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

MODEL_NAME="ares"
HF_REPO="DavidAU/OpenAi-GPT-oss-20b-HERETIC-uncensored-NEO-Imatrix-gguf"
GGUF_FILE="OpenAI-20B-NEOPlus-Uncensored-IQ4_NL.gguf"

# Check if Ollama is running
echo "[1/4] Checking Ollama..."
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

# Check if model already exists
echo ""
echo "[2/4] Checking existing model..."
if ollama list | grep -q "^$MODEL_NAME"; then
    echo "⚠ Model '$MODEL_NAME' already exists"
    read -p "  Delete and rebuild? (y/N): " rebuild
    if [[ "$rebuild" =~ ^[Yy]$ ]]; then
        echo "  Deleting existing model..."
        ollama rm "$MODEL_NAME" || true
    else
        echo "  Keeping existing model. Exiting."
        exit 0
    fi
fi

# Get Modelfile path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MODELFILE="$PROJECT_ROOT/Modelfile"

if [ ! -f "$MODELFILE" ]; then
    echo "✗ Modelfile not found at: $MODELFILE"
    echo "  Please ensure the Modelfile exists in the project root"
    exit 1
fi

echo ""
echo "[3/4] Reading Modelfile..."
echo "  Modelfile: $MODELFILE"
cat "$MODELFILE"
echo ""

# Create model from Modelfile
echo ""
echo "[4/4] Creating model from Modelfile..."
echo "  This will download the IQ4_NL model (~11GB) if not already cached"
echo "  This may take a while depending on your internet connection..."
echo ""

if ollama create "$MODEL_NAME" -f "$MODELFILE" 2>&1 | tee /tmp/ollama_create.log; then
    echo ""
    echo "✓ Successfully created model '$MODEL_NAME'"
    rm -f /tmp/ollama_create.log
else
    echo ""
    echo "✗ Failed to create model. Error log:"
    cat /tmp/ollama_create.log 2>/dev/null || echo "  (No error log available)"
    rm -f /tmp/ollama_create.log
    
    # Try alternative: download file first
    echo ""
    echo "Attempting alternative method: downloading GGUF file first..."
    
    MODELS_DIR="$HOME/.ollama/models"
    mkdir -p "$MODELS_DIR"
    
    LOCAL_FILE="$MODELS_DIR/$GGUF_FILE"
    HF_URL="https://huggingface.co/$HF_REPO/resolve/main/$GGUF_FILE"
    
    echo "Downloading from: $HF_URL"
    echo "Saving to: $LOCAL_FILE"
    
    if command -v huggingface-cli &> /dev/null; then
        echo "Using huggingface-cli..."
        huggingface-cli download "$HF_REPO" "$GGUF_FILE" --local-dir "$MODELS_DIR/$HF_REPO" || {
            echo "huggingface-cli failed, trying direct download..."
            wget -O "$LOCAL_FILE" "$HF_URL" || curl -L -o "$LOCAL_FILE" "$HF_URL" || {
                echo "✗ Failed to download file"
                exit 1
            }
        }
        if [ -d "$MODELS_DIR/$HF_REPO" ]; then
            LOCAL_FILE="$MODELS_DIR/$HF_REPO/$GGUF_FILE"
        fi
    else
        wget -O "$LOCAL_FILE" "$HF_URL" || curl -L -o "$LOCAL_FILE" "$HF_URL" || {
            echo "✗ Failed to download file. Please install wget or curl"
            exit 1
        }
    fi
    
    if [ -f "$LOCAL_FILE" ]; then
        echo "✓ Downloaded GGUF file"
        echo ""
        echo "Creating Modelfile with local file reference..."
        TEMP_MODELFILE=$(mktemp)
        cat > "$TEMP_MODELFILE" << EOF
FROM $LOCAL_FILE
PARAMETER temperature 0.7
PARAMETER top_k 40
PARAMETER top_p 0.95
PARAMETER min_p 0.05
PARAMETER repeat_penalty 1.1
PARAMETER num_predict 2048
PARAMETER num_ctx 32768
PARAMETER stop "<|endoftext|>"
PARAMETER stop "<|im_end|>"
PARAMETER stop "</s>"
EOF
        
        if ollama create "$MODEL_NAME" -f "$TEMP_MODELFILE"; then
            echo "✓ Successfully created model from local file"
            rm -f "$TEMP_MODELFILE"
        else
            echo "✗ Failed to create model from local file"
            rm -f "$TEMP_MODELFILE"
            exit 1
        fi
    else
        echo "✗ File not found after download"
        exit 1
    fi
fi

# Verify model was created
echo ""
echo "Verifying model..."
if ollama list | grep -q "^$MODEL_NAME"; then
    echo "✓ Model '$MODEL_NAME' is available"
    echo ""
    echo "Model info:"
    ollama show "$MODEL_NAME" || true
else
    echo "⚠ Warning: Model was created but not found in list"
fi

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  Rebuild Complete!                                 ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "Model name: $MODEL_NAME"
echo "Quantization: IQ4_NL (~11GB VRAM)"
echo ""
echo "Next steps:"
echo "1. On your main server, verify .env has:"
echo "   OLLAMA_MODEL=$MODEL_NAME"
echo ""
echo "2. Restart your backend server"
echo ""
echo "To test the model:"
echo "   ollama run $MODEL_NAME"
