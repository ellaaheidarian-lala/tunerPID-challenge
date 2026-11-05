import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("/node_modules/")) return;
          if (/\/node_modules\/(react|react-dom|scheduler)\//.test(id))
            return "react";
          return "charts";
        },
      },
    },
  },
  server: { port: 3000, proxy: { "/api": "http://127.0.0.1:8000" } },
});
