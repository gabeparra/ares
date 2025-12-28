import express, { Request, Response, NextFunction } from "express";
import cors from "cors";
import { OpenRouter } from "@openrouter/sdk";

const app = express();
app.use(cors());
app.use(express.json({ limit: "10mb" }));

const PORT = process.env.OPENROUTER_SERVICE_PORT || 3100;
const API_KEY = process.env.OPENROUTER_API_KEY;

if (!API_KEY) {
  console.error("OPENROUTER_API_KEY environment variable is required");
  process.exit(1);
}

const client = new OpenRouter({
  apiKey: API_KEY,
});

interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

interface ChatRequest {
  model: string;
  messages: ChatMessage[];
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
}

interface ModelsResponse {
  data: Array<{
    id: string;
    name: string;
    context_length?: number;
    pricing?: {
      prompt: string;
      completion: string;
    };
  }>;
}

// Health check endpoint
app.get("/health", (_req: Request, res: Response) => {
  res.json({ status: "ok", service: "openrouter-service" });
});

// Chat completions endpoint (non-streaming)
app.post("/v1/chat/completions", async (req: Request, res: Response) => {
  try {
    const { model, messages, temperature, max_tokens, stream }: ChatRequest = req.body;

    if (!messages || !Array.isArray(messages)) {
      res.status(400).json({ error: "messages array is required" });
      return;
    }

    const modelToUse = model || process.env.OPENROUTER_MODEL || "openai/gpt-3.5-turbo";

    if (stream) {
      // Streaming response
      res.setHeader("Content-Type", "text/event-stream");
      res.setHeader("Cache-Control", "no-cache");
      res.setHeader("Connection", "keep-alive");

      const streamResponse = await client.chat.send({
        model: modelToUse,
        messages: messages.map((m) => ({
          role: m.role,
          content: m.content,
        })),
        temperature: temperature ?? 0.7,
        maxTokens: max_tokens ?? 2048,
        stream: true,
        streamOptions: {
          includeUsage: true,
        },
      });

      for await (const chunk of streamResponse) {
        const data = JSON.stringify(chunk);
        res.write(`data: ${data}\n\n`);
      }

      res.write("data: [DONE]\n\n");
      res.end();
    } else {
      // Non-streaming response
      const result = await client.chat.send({
        model: modelToUse,
        messages: messages.map((m) => ({
          role: m.role,
          content: m.content,
        })),
        temperature: temperature ?? 0.7,
        maxTokens: max_tokens ?? 2048,
        stream: false,
      });

      res.json(result);
    }
  } catch (error) {
    console.error("Chat completion error:", error);
    const message = error instanceof Error ? error.message : "Unknown error";
    res.status(500).json({ error: { message } });
  }
});

// List available models endpoint
app.get("/v1/models", async (_req: Request, res: Response) => {
  try {
    // Fetch models from OpenRouter API directly since SDK may not expose this
    const response = await fetch("https://openrouter.ai/api/v1/models", {
      headers: {
        Authorization: `Bearer ${API_KEY}`,
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch models: ${response.statusText}`);
    }

    const data: ModelsResponse = await response.json() as ModelsResponse;
    res.json(data);
  } catch (error) {
    console.error("Models list error:", error);
    const message = error instanceof Error ? error.message : "Unknown error";
    res.status(500).json({ error: { message } });
  }
});

// Error handling middleware
app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
  console.error("Unhandled error:", err);
  res.status(500).json({ error: { message: err.message } });
});

app.listen(PORT, () => {
  console.log(`OpenRouter service running on port ${PORT}`);
});

