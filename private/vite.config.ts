import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

console.log("🏢 Building ENTERPRISE Ragbits");

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  root: path.resolve(__dirname, "../typescript/ui"),
  resolve: {
    alias: {
      // Override main.tsx with enterprise version
      "/src/main.tsx": path.resolve(__dirname, "main.tsx"),
      // You can add more overrides here as needed
      // "/src/config.tsx": path.resolve(__dirname, "config.tsx"),
      // "/src/plugins/AuthPlugin": path.resolve(__dirname, "plugins/AuthPlugin"),
    },
  },
  build: {
    outDir: path.resolve(
      __dirname,
      "../packages/ragbits-chat/src/ragbits/chat/ui-build"
    ),
    emptyOutDir: true,
  },
});

