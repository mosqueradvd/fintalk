import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The FastAPI backend runs on :8000. Proxy API calls there in dev so the
// frontend can use same-origin relative paths (no CORS config needed).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/chat": "http://localhost:8000",
      "/companies": "http://localhost:8000",
      "/sectors": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
