import { defineConfig } from "vite";
import { TanStackRouterVite } from "@tanstack/router-vite-plugin";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";

// vinxi reads app.config.ts; this file kept for IDE + direct vite usage.
export default defineConfig({
  plugins: [
    tsconfigPaths(),
    TanStackRouterVite({ routesDirectory: "./app/routes", generatedRouteTree: "./app/routeTree.gen.ts" }),
    react(),
  ],
});
