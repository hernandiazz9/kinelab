import type { NextConfig } from "next";

// Dos modos, una sola build de código (ver web/src/lib/api.ts §el modo):
//
//   local (default)  habla con el backend (service/, FastAPI) en el 8765 por /api/*.
//   demo             sitio estático, sin backend: lee /demo/*, que escribe
//                    `python -m kinelab.tools.exportar_demo`. Es lo que se sube a
//                    Vercel. El motor NO se despliega: son onnxruntime con CoreML,
//                    rtmlib, OpenCV y ffmpeg, con pesos de cientos de MB y 76 s por
//                    clip de 18 s. Nada de eso entra en una función serverless.
//
//     cd web && NEXT_PUBLIC_KINELAB_MODO=demo pnpm build   → web/out/
const DEMO = process.env.NEXT_PUBLIC_KINELAB_MODO === "demo";

// El backend (service/, FastAPI) escucha en el 8765. Todo /api/* se reenvía ahí:
// para el navegador es el mismo origen, así que no hace falta CORS a mano.
const API = process.env.KINELAB_API ?? "http://127.0.0.1:8765";

const nextConfig: NextConfig = {
  // `export` no admite rewrites ni proxy: no hay servidor que los ejecute. Los del
  // modo local quedan tal como estaban; en demo no existe ninguno de los dos.
  ...(DEMO
    ? { output: "export" as const }
    : {
        async rewrites() {
          return [{ source: "/api/:path*", destination: `${API}/api/:path*` }];
        },
        // Un video de 1080p120 de 30 s pesa ~85 MB y la pose tarda decenas de segundos:
        // el proxy no puede cortar a los 30 s por defecto, ni a los 10 MiB de cuerpo
        // que Next 16 trae por defecto (medido: un .mp4 de 20 MB llegaba truncado a
        // 10 MiB y la conexión quedaba colgada, sin error).
        experimental: { proxyTimeout: 600_000, proxyClientMaxBodySize: "2gb" },
      }),
};

export default nextConfig;
