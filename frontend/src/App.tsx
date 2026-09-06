import { useEffect, useRef, useState } from "react";
import { askChat, type ChatResult } from "./api";
import { ToolCallPanel } from "./components/ToolCallPanel";
import {
  CheckIcon,
  CloseIcon,
  CopyIcon,
  MoonIcon,
  SparkIcon,
  SunIcon,
} from "./components/icons";

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

type Theme = "light" | "dark";

function initialTheme(): Theme {
  try {
    const saved = localStorage.getItem("fintalk-theme");
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    /* private mode / storage blocked — fall through */
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export default function App() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [theme, setTheme] = useState<Theme>(initialTheme);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("fintalk-theme", theme);
    } catch {
      /* ignore */
    }
  }, [theme]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [turns, loading]);

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
    <div className="panel">
      <header className="header">
        <span className="header__mark">
          <SparkIcon />
        </span>
        <h1 className="header__title">FinTalk</h1>
        <span className="badge">Beta</span>
        <span className="header__spacer" />
        <button
          className="icon-btn"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {theme === "dark" ? <SunIcon /> : <MoonIcon />}
        </button>
        <button className="icon-btn" aria-label="Close" onClick={() => setTurns([])}>
          <CloseIcon />
        </button>
      </header>

      <div className="conversation" ref={scrollRef}>
        <div className="bubble">
          KPI estimates for public companies — ask in plain English.
        </div>

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
            <div className="bubble">{turn.question}</div>
            {turn.result && (
              <>
                <div className="bubble answer">
                  {turn.result.answer}
                  <div className="bubble__model">{turn.result.model}</div>
                  <div className="answer__toolbar">
                    <CopyButton text={turn.result.answer} />
                  </div>
                </div>
                <ToolCallPanel calls={turn.result.tool_calls} />
              </>
            )}
            {turn.error && <div className="bubble bubble--error">{turn.error}</div>}
          </div>
        ))}

        {loading && <div className="bubble">…</div>}
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

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      aria-label={copied ? "Copied" : "Copy response"}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        } catch {
          /* clipboard unavailable */
        }
      }}
    >
      {copied ? <CheckIcon /> : <CopyIcon />}
    </button>
  );
}
