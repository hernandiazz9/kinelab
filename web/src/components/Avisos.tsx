// Lo que hay que leer ANTES de cualquier número (ADR-016, invariante 2).
//
// Tres cosas, en este orden: que esto es exploración y no una medición
// juzgable; bajo qué supuesto se midió el tiempo (`fps_aviso`, la frase que
// escribe el motor en `warnings[0]`); y si el fps que se usó no es el que
// declara el archivo, por qué (`fps_note`). Ninguna se compone acá: las tres
// vienen del dato. Va arriba del reproductor y de todas las tablas.

import type { FichaArchivo, Resumen } from "@/lib/api";

export default function Avisos({ resumen, archivo }: { resumen: Resumen; archivo: FichaArchivo | null }) {
  const note = archivo?.fps_note ?? null;
  return (
    <section className="rounded-lg border border-amber-700 bg-amber-950/30 p-3 text-sm">
      <p className="font-medium text-amber-200">{resumen.aviso}</p>

      {resumen.fps_aviso && <p className="mt-2 text-amber-100">{resumen.fps_aviso}</p>}

      {note && (
        <p className="mt-2 text-amber-100">
          <span className="font-medium">El fps que se usó no es el que sale de contar todos los deltas del archivo.</span> {note}
        </p>
      )}

      {resumen.gate_diria.length > 0 && <p className="mt-2 text-amber-200/90">El gate diría: {resumen.gate_diria.join(" · ")}</p>}
    </section>
  );
}
