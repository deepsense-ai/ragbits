import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../../packages/ragbits-chat/src/ragbits/chat/ui-build",
    emptyOutDir: true,
  },
});
