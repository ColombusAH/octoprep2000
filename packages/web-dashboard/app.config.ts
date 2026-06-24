import { defineConfig } from "@tanstack/react-start/config";
import tsConfigPaths from "vite-tsconfig-paths";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  tsr: {
    appDirectory: "app",
  },
  vite: {
    plugins: [tsConfigPaths(), tailwindcss()],
    ssr: {
      external: ["@react-pdf/renderer"],
    },
    optimizeDeps: {
      include: ["@react-pdf/renderer"],
    },
  },
});
