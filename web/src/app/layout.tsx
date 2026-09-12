import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "kinelab · exploración",
  description: "Subir un video de un swing y mirar los palitos y toda la data que el motor produce.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className="h-full antialiased">
      <body className="min-h-full">{children}</body>
    </html>
  );
}
