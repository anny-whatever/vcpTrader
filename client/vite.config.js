// vite.config.js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Proxy requests to /socket (including WebSocket upgrades) to your backend server
      "/socket": {
        target: "http://147.93.106.51:8000",
        ws: true, // Enable proxying of websockets
        changeOrigin: true, // Adjust the origin header to the target URL
        // Optionally, if your backend expects a different path, you can rewrite the path:
        // rewrite: (path) => path.replace(/^\/socket/, '/socket')
      },
    },
  },
  build: {
    minify: false,
    rollupOptions: {
      output: {
        // Optionally, use a more conservative manualChunks strategy
        manualChunks(id) {
          if (id.includes("node_modules")) {
            return "vendor";
          }
        },
      },
    },
  },
});
