#!/bin/bash
# Setup script for OpenAI 20B NEO model from Hugging Face

set -e

echo "╔══════════════════════════════════════════════════════╗"
echo "║  Setting up OpenAI 20B NEO for Ollama               ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

MODEL_NAME="openai-20b-neo"
HF_REPO="DavidAU/OpenAi-GPT-oss-20b-abliterated-uncensored-NEO-Imatrix-gguf"
GGUF_FILE="OpenAI-20B-NEO-CODEPlus-Uncensored-Q5_1.gguf"

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
echo "[2/4] Checking if model already exists..."
if ollama list | grep -q "^$MODEL_NAME"; then
    echo "✓ Model '$MODEL_NAME' already exists"
    echo "  To recreate it, first delete it: ollama rm $MODEL_NAME"
    read -p "  Delete and recreate? (y/N): " recreate
    if [[ "$recreate" =~ ^[Yy]$ ]]; then
        echo "  Deleting existing model..."
        ollama rm "$MODEL_NAME" || true
    else
        echo "  Keeping existing model. Updating .env..."
        if [ -f .env ]; then
            if grep -q "^OLLAMA_MODEL=" .env; then
                sed -i "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=$MODEL_NAME|" .env
            else
                echo "OLLAMA_MODEL=$MODEL_NAME" >> .env
            fi
        fi
        echo "✓ Configuration updated"
        exit 0
    fi
fi

# Create model from Hugging Face
echo ""
echo "[3/4] Creating model from Hugging Face..."
echo "  Repository: $HF_REPO"
echo "  File: $GGUF_FILE"
echo ""

# Try method 1: Direct Hugging Face repo reference (Ollama should auto-detect GGUF)
echo "Attempting to create model from Hugging Face repo..."
cat > /tmp/Modelfile << EOF
FROM huggingface/$HF_REPO
PARAMETER temperature 0.7
PARAMETER top_k 40
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1
EOF

if ollama create "$MODEL_NAME" -f /tmp/Modelfile 2>&1 | tee /tmp/ollama_create.log; then
    echo ""
    echo "✓ Successfully created model '$MODEL_NAME' from Hugging Face"
    rm -f /tmp/Modelfile /tmp/ollama_create.log
else
    echo ""
    echo "⚠ Method 1 failed. Trying alternative approach..."
    rm -f /tmp/Modelfile
    
    # Method 2: Download the GGUF file and use local path
    echo ""
    echo "Downloading GGUF file from Hugging Face..."
    echo "This may take a while depending on your internet connection..."
    echo ""
    
    # Create models directory if it doesn't exist
    MODELS_DIR="$HOME/.ollama/models"
    mkdir -p "$MODELS_DIR"
    
    # Download using huggingface-cli or wget/curl
    if command -v huggingface-cli &> /dev/null; then
        echo "Using huggingface-cli to download..."
        huggingface-cli download "$HF_REPO" "$GGUF_FILE" --local-dir "$MODELS_DIR/$HF_REPO" || {
            echo "⚠ huggingface-cli download failed. Trying direct download..."
            # Fallback to direct download
            HF_URL="https://huggingface.co/$HF_REPO/resolve/main/$GGUF_FILE"
            wget -O "$MODELS_DIR/$GGUF_FILE" "$HF_URL" || curl -L -o "$MODELS_DIR/$GGUF_FILE" "$HF_URL" || {
                echo "✗ Failed to download file. Please download manually:"
                echo "   URL: https://huggingface.co/$HF_REPO/resolve/main/$GGUF_FILE"
                echo "   Save to: $MODELS_DIR/$GGUF_FILE"
                echo "   Then run: ollama create $MODEL_NAME -f Modelfile"
                exit 1
            }
        }
        LOCAL_FILE="$MODELS_DIR/$HF_REPO/$GGUF_FILE"
    else
        # Direct download
        HF_URL="https://huggingface.co/$HF_REPO/resolve/main/$GGUF_FILE"
        LOCAL_FILE="$MODELS_DIR/$GGUF_FILE"
        echo "Downloading from: $HF_URL"
        wget -O "$LOCAL_FILE" "$HF_URL" || curl -L -o "$LOCAL_FILE" "$HF_URL" || {
            echo "✗ Failed to download file. Please install wget or curl, or download manually:"
            echo "   URL: $HF_URL"
            echo "   Save to: $LOCAL_FILE"
            echo "   Then run: ollama create $MODEL_NAME -f Modelfile"
            exit 1
        }
    fi
    
    if [ -f "$LOCAL_FILE" ]; then
        echo "✓ Downloaded GGUF file: $LOCAL_FILE"
        echo ""
        echo "Creating model from local file..."
        cat > /tmp/Modelfile << EOF
FROM $LOCAL_FILE
PARAMETER temperature 0.7
PARAMETER top_k 40
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1
EOF
        
        if ollama create "$MODEL_NAME" -f /tmp/Modelfile; then
            echo "✓ Successfully created model '$MODEL_NAME' from local file"
            rm -f /tmp/Modelfile
        else
            echo "✗ Failed to create model from local file"
            echo "  You may need to:"
            echo "  1. Check that the file is a valid GGUF: $LOCAL_FILE"
            echo "  2. Ensure you have enough disk space and memory"
            echo "  3. Try running: ollama create $MODEL_NAME -f Modelfile"
            rm -f /tmp/Modelfile
            exit 1
        fi
    else
        echo "✗ File not found after download attempt"
        exit 1
    fi
fi

# Update .env file
echo ""
echo "[4/4] Updating configuration..."
if [ -f .env ]; then
    if grep -q "^OLLAMA_MODEL=" .env; then
        sed -i "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=$MODEL_NAME|" .env
        echo "✓ Updated OLLAMA_MODEL in .env"
    else
        echo "OLLAMA_MODEL=$MODEL_NAME" >> .env
        echo "✓ Added OLLAMA_MODEL to .env"
    fi
else
    echo "OLLAMA_MODEL=$MODEL_NAME" > .env
    echo "✓ Created .env with OLLAMA_MODEL"
fi

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  Setup Complete!                                    ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "Model configured: $MODEL_NAME"
echo ""
echo "Next steps:"
echo "1. Restart your backend server:"
echo "   python manage.py runserver 0.0.0.0:8000"
echo ""
echo "2. Or change the model in the web UI Settings tab"
echo ""
echo "To test the model:"
echo "   ollama run $MODEL_NAME"
