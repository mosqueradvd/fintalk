import { useState } from "react";
import type { ToolCall } from "../api";

// Shows what the agent actually did: which tools, with what args, and the
// raw result. This is the "visibility into tool calls" the assignment asks for.
export function ToolCallPanel({ calls }: { calls: ToolCall[] }) {
  if (calls.length === 0) return null;
  return (
    <div className="tool-panel">
      <div className="tool-panel__title">Tool calls ({calls.length})</div>
      {calls.map((c, i) => (
        <ToolCallRow key={i} call={c} />
      ))}
    </div>
  );
}

function ToolCallRow({ call }: { call: ToolCall }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`tool-call ${call.ok ? "" : "tool-call--error"}`}>
      <button className="tool-call__head" onClick={() => setOpen(!open)}>
        <span className="tool-call__name">{call.name}</span>
        <span className="tool-call__args">
          {Object.entries(call.args)
            .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
            .join(", ")}
        </span>
        <span className="tool-call__meta">
          {call.ok ? "ok" : "error"} · {call.latency_ms}ms
        </span>
      </button>
      {open && (
        <pre className="tool-call__result">
          {JSON.stringify(call.result, null, 2)}
        </pre>
      )}
    </div>
  );
}
