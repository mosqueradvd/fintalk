// Types mirror chat/schemas.py (ChatResult / ToolCall).

export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
  result: unknown;
  latency_ms: number;
  ok: boolean;
}

export interface ChatResult {
  answer: string;
  model: string;
  tool_calls: ToolCall[];
}

export async function askChat(question: string): Promise<ChatResult> {
  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    throw new Error(`Backend error ${res.status}: ${await res.text()}`);
  }
  return res.json();
}
