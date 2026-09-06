# frontend/ — chat UI

Vite + React + TypeScript SPA. Deliberately thin: one page that POSTs to
`/chat` and renders the answer plus the agent's tool-call trace.

## Run

```bash
# backend first (repo root)
uvicorn api.main:app --port 8000

# then
cd frontend && npm install && npm run dev   # http://localhost:5173
```

`vite.config.ts` proxies `/chat`, `/companies`, `/sectors`, `/health` to
`:8000`, so the app uses same-origin relative paths (no CORS setup).

## Layout

| File | Role |
|------|------|
| `src/App.tsx` | conversation state, composer, sample prompts |
| `src/components/ToolCallPanel.tsx` | per-turn tool-call trace (name, args, ok/error, latency, expandable raw result) |
| `src/api.ts` | `askChat()` + types mirroring `chat/schemas.py` |
