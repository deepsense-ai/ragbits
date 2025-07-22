import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir: "../../packages/ragbits-chat/src/ragbits/chat/ui-build",
    emptyOutDir: true,
  },
});
