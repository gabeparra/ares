# Rebuilding Ares with HERETIC IQ4_NL Model

## Model Information

- **Model Name**: `ares`
- **Quantization**: IQ4_NL (~11GB VRAM)
- **File**: `OpenAI-20B-NEOPlus-Uncensored-IQ4_NL.gguf`
- **Source**: `hf.co/DavidAU/OpenAi-GPT-oss-20b-HERETIC-uncensored-NEO-Imatrix-gguf`

## Option 1: Rebuild via API (from main server)

You can rebuild the model remotely using the Ollama API:

```bash
curl -X POST http://<4090-rig-ip>:11434/api/create \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ares",
    "from": "huggingface/DavidAU/OpenAi-GPT-oss-20b-HERETIC-uncensored-NEO-Imatrix-gguf:OpenAI-20B-NEOPlus-Uncensored-IQ4_NL",
    "parameters": {
      "temperature": 0.7,
      "top_k": 40,
      "top_p": 0.95,
      "min_p": 0.05,
      "repeat_penalty": 1.1,
      "num_predict": 2048,
      "num_ctx": 32768
    }
  }'
```

Or use the Ares rebuild endpoint:

```bash
curl -X POST http://localhost:8000/api/v1/ollama/rebuild \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-token>"
```

## Option 2: Rebuild on 4090 Rig (Recommended)

1. **Copy the Modelfile to your 4090 rig:**
   ```bash
   # The Modelfile is at: /home/gabe/ares/Modelfile
   # Copy it to your 4090 rig
   ```

2. **Run the rebuild script on the 4090 rig:**
   ```bash
   ./scripts/rebuild_ares_heretic.sh
   ```

   Or manually:
   ```bash
   # Delete old model if it exists
   ollama rm ares
   
   # Create new model from Modelfile
   ollama create ares -f Modelfile
   ```

## Option 3: Download File First (if direct HF reference fails)

If Ollama can't pull directly from Hugging Face:

1. **Download the GGUF file:**
   ```bash
   wget https://huggingface.co/DavidAU/OpenAi-GPT-oss-20b-HERETIC-uncensored-NEO-Imatrix-gguf/resolve/main/OpenAI-20B-NEOPlus-Uncensored-IQ4_NL.gguf
   ```

2. **Create Modelfile pointing to local file:**
   ```bash
   cat > Modelfile << EOF
   FROM $(pwd)/OpenAI-20B-NEOPlus-Uncensored-IQ4_NL.gguf
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
   ```

3. **Create the model:**
   ```bash
   ollama create ares -f Modelfile
   ```

## Verification

After rebuilding, verify the model:

```bash
# List models
ollama list

# Show model details
ollama show ares

# Test the model
ollama run ares "Hello! What model are you?"
```

## Configuration

After rebuilding, ensure your `.env` file has:
```bash
OLLAMA_MODEL=ares
OLLAMA_BASE_URL=http://<4090-rig-ip>:11434
```

Then restart your backend server.

## Notes

- **IQ4_NL Quantization**: ~11GB VRAM (more efficient than Q5_1)
- **First Load**: Takes ~7-8 seconds
- **Model Size**: ~11GB download
- **System Prompt**: Controlled by Settings panel, not Modelfile
