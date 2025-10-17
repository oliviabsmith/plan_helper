import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  return {
    plugins: [react()],
    server: {
      port: 5173,
      open: true,
      proxy: env.VITE_API_PROXY
        ? {
            "/tools": {
              target: env.VITE_API_PROXY,
              changeOrigin: true,
            },
          }
        : undefined,
    },
    build: {
      outDir: "dist",
    },
  };
});
