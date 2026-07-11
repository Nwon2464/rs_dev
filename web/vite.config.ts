import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    // The existing 8,008-row CSV is intentionally bundled for a self-contained viewer.
    chunkSizeWarningLimit: 3000,
  },
  server: {
    fs: {
      allow: [".."],
    },
  },
});
