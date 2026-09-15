import type { Metadata } from "next";
import "./globals.css";

// `noindex`: el enlace de la demo es para mostrárselo a alguien, no para que lo
// levante un buscador. Va siempre, también en local: una pantalla de exploración
// corriendo en localhost tampoco tiene nada que indexar.
export const metadata: Metadata = {
  title: "kinelab · exploración",
  description: "Subir un video de un swing y mirar los palitos y toda la data que el motor produce.",
  robots: { index: false, follow: false, nocache: true, googleBot: { index: false, follow: false } },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className="h-full antialiased">
      <body className="min-h-full">{children}</body>
    </html>
  );
}
