import { useState } from "react";
import { askChat, type ChatResult } from "./api";
import { ToolCallPanel } from "./components/ToolCallPanel";

interface Turn {
  question: string;
  result?: ChatResult;
  error?: string;
}

const SAMPLES = [
  "What's IGC's QTD subscriber growth this quarter?",
  "Show Total Revenue history for CloudNine",
  "Which companies are in the Fintech sector?",
];

export default function App() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function send(question: string) {
    if (!question.trim() || loading) return;
    setInput("");
    setLoading(true);
    const idx = turns.length;
    setTurns((t) => [...t, { question }]);
    try {
      const result = await askChat(question);
      setTurns((t) => t.map((v, i) => (i === idx ? { ...v, result } : v)));
    } catch (e) {
      const error = e instanceof Error ? e.message : String(e);
      setTurns((t) => t.map((v, i) => (i === idx ? { ...v, error } : v)));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="app__header">
        <h1>FinTalk</h1>
        <p>KPI estimates for public companies — ask in plain English.</p>
      </header>

      <div className="conversation">
        {turns.length === 0 && (
          <div className="samples">
            {SAMPLES.map((s) => (
              <button key={s} onClick={() => send(s)}>
                {s}
              </button>
            ))}
          </div>
        )}

        {turns.map((turn, i) => (
          <div key={i} className="turn">
            <div className="bubble bubble--user">{turn.question}</div>
            {turn.result && (
              <>
                <div className="bubble bubble--assistant">
                  {turn.result.answer}
                  <div className="bubble__model">{turn.result.model}</div>
                </div>
                <ToolCallPanel calls={turn.result.tool_calls} />
              </>
            )}
            {turn.error && (
              <div className="bubble bubble--error">{turn.error}</div>
            )}
          </div>
        ))}

        {loading && <div className="bubble bubble--assistant">…</div>}
      </div>

      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about a company's KPIs…"
          disabled={loading}
          autoFocus
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
