import { useState } from "react";
import type { ToolCall } from "../api";
import { ToolIcon } from "./icons";

// Agent transparency: one row per tool the agent called, name in bold and the
// arguments rendered as a plain readable trail. Click a row to see the raw
// result. Rows stack with a hairline divider, mirroring the reference's
// "recommended actions" card.
export function ToolCallPanel({ calls }: { calls: ToolCall[] }) {
  if (calls.length === 0) return null;
  return (
    <div className="tools">
      <div className="tools__title">
        Tool calls · {calls.length}
      </div>
      {calls.map((c, i) => (
        <ToolCallRow key={i} call={c} />
      ))}
    </div>
  );
}

// "IGC · Total Revenue · 8" — just the values, in call order.
function summarizeArgs(args: Record<string, unknown>): string {
  return Object.values(args)
    .map((v) => (typeof v === "string" ? v : JSON.stringify(v)))
    .join("  ·  ");
}

function ToolCallRow({ call }: { call: ToolCall }) {
  const [open, setOpen] = useState(false);
  const args = summarizeArgs(call.args);
  return (
    <>
      <button
        className="tool-row"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span
          className={
            "tool-row__icon" + (call.ok ? "" : " tool-row__icon--error")
          }
        >
          <ToolIcon />
        </span>
        <span className="tool-row__body">
          <span className="tool-row__line">
            <span className="tool-row__name">{call.name}</span>
            {args && <span className="tool-row__args"> · {args}</span>}
          </span>
          <span className="tool-row__meta">
            {call.ok ? "returned" : "error"} in {call.latency_ms} ms
          </span>
        </span>
      </button>
      {open && (
        <pre className="tool-row__result">
          {JSON.stringify(call.result, null, 2)}
        </pre>
      )}
    </>
  );
}
