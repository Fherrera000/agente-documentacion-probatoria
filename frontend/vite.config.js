import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// La interfaz llama a /api/... y Vite reenvía esas peticiones a FastAPI.
// Así el navegador ve un solo origen y no hace falta configurar CORS en desarrollo.
//   - En tu computadora (npm run dev):  API en http://127.0.0.1:8000
//   - Dentro de Docker (docker compose): API en http://api:8000
const destinoApi = process.env.API_URL || "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    // En Docker sobre Windows los cambios de archivos solo se detectan con sondeo.
    watch: { usePolling: process.env.VITE_POLLING === "true" },
    proxy: {
      "/api": {
        target: destinoApi,
        changeOrigin: true,
        rewrite: (ruta) => ruta.replace(/^\/api/, ""),
      },
    },
  },
});
