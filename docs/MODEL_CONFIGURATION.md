# OpenAI GPT-oss-20B HERETIC Model Configuration

## Overview

This document describes the configuration for the OpenAI GPT-oss-20B HERETIC uncensored NEO model used in Ares.

## Model Details

- **Model Name**: `openai-20b-neo:latest` (or `openai-20b-neo-heretic`)
- **Base**: OpenAI GPT-oss-20B HERETIC uncensored with NEO-CODEPlus Imatrix
- **Quantization**: Q5_1 (~16GB VRAM) or IQ4_NL (~11GB VRAM)
- **Parameters**: 20.9B
- **Context Window**: Up to 131,072 tokens (128k)
- **Type**: Mixture of Experts (MOE) with 24 experts

## Default Configuration

### Generation Parameters

These defaults are set in `/home/gabe/ares/api/utils.py` (`_get_model_config()`):

- **temperature**: 0.7 (coding/general use)
- **top_p**: 0.95
- **top_k**: 40
- **min_p**: 0.05
- **repeat_penalty**: 1.1 (CRITICAL - prevents repetition)
- **num_ctx**: 32768 (can be increased up to 131072)
- **num_predict**: 2048 (max tokens to generate)
- **num_gpu**: 40

### Temperature Guidelines

- **0.6-0.8**: Coding and general use (default: 0.7)
- **1.0-1.2+**: Creative writing and brainstorming
- **2.0+**: Very creative/unpredictable (use with caution)

## System Prompt

**IMPORTANT**: The system prompt is controlled by the Settings panel in the web UI, NOT by the Modelfile.

- The system prompt is stored in the database (`chat_system_prompt` setting)
- It can be configured via: Settings → System Prompt
- Default prompt is in `/home/gabe/ares/api/utils.py` (`_get_default_system_prompt()`)
- The prompt assembler (`ares_core/prompt_assembler.py`) uses the prompt from settings

## Modelfile

The Modelfile (`/home/gabe/ares/Modelfile`) contains:
- Base model reference
- Default parameter values (can be overridden via API)
- **NO SYSTEM prompt** (system prompt comes from settings)

## API Usage

### Via Orchestrator (Recommended)

The orchestrator (`ares_core/orchestrator.py`) automatically:
- Uses model config from settings
- Applies system prompt from settings
- Handles memory and context injection

### Direct Ollama API

Endpoints in `/api/v1/ollama/chat` and `/api/v1/ollama/generate` support:
- All generation parameters
- Custom system prompts via messages array
- Streaming responses

## Configuration Files

1. **Model Config Defaults**: `/home/gabe/ares/api/utils.py` → `_get_model_config()`
2. **System Prompt Default**: `/home/gabe/ares/api/utils.py` → `_get_default_system_prompt()`
3. **Modelfile**: `/home/gabe/ares/Modelfile`
4. **Orchestrator**: `/home/gabe/ares/ares_core/orchestrator.py`
5. **Ollama Views**: `/home/gabe/ares/api/ollama_views.py`

## Updating Configuration

### Model Parameters

Update via Settings panel in web UI, or directly in database:
```python
from api.utils import _set_setting
_set_setting("model_temperature", "0.8")
_set_setting("model_repeat_penalty", "1.15")
_set_setting("model_num_ctx", "65536")
```

### System Prompt

Update via Settings panel → System Prompt, or:
```python
from api.utils import _set_setting
_set_setting("chat_system_prompt", "Your custom prompt here")
```

## Important Notes

1. **System Prompt Priority**: Settings panel → Database → Default prompt
2. **Modelfile SYSTEM directive**: Removed - system prompt always comes from settings
3. **Repeat Penalty**: Critical for this model - keep at 1.1-1.15
4. **Context Window**: Can be increased up to 131072 for very long contexts
5. **MOE Model**: Different expert combinations may produce different results

## Troubleshooting

- **Repetition**: Increase `repeat_penalty` to 1.15
- **Empty responses**: Adjust temperature or expert count
- **Slow responses**: Model is large, first load takes ~7-8 seconds
- **Quality issues**: Try different expert counts (4-8 range)
