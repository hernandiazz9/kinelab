import type { NextConfig } from "next";

// El backend (service/, FastAPI) escucha en el 8765. Todo /api/* se reenvía ahí:
// para el navegador es el mismo origen, así que no hace falta CORS a mano.
const API = process.env.KINELAB_API ?? "http://127.0.0.1:8765";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API}/api/:path*` }];
  },
  // Un video de 1080p120 de 30 s pesa ~85 MB y la pose tarda decenas de segundos:
  // el proxy no puede cortar a los 30 s por defecto.
  experimental: { proxyTimeout: 600_000 },
};

export default nextConfig;
