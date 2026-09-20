"use client";

// Cuál de las repeticiones del clip se está mirando.
//
// Va arriba de las métricas y de las tablas porque cambia TODAS: los eventos,
// las fotos, la escala, la referencia de los «vs address», las duraciones, los
// picos y el sextuplo de cada métrica. No es un filtro de la vista; es de qué
// swing habla la pantalla.
//
// Con una sola repetición no se muestra: un selector de un solo elemento no es
// una elección, es ruido. La frase «repetición 1 de 1» sí se muestra, en los
// lugares que ya la decían — que es otra cosa: dice cuál es, no invita a
// cambiarla.
//
// Cada botón lleva el cuadro del address de su repetición: es lo que la
// distingue de la de al lado en un clip de varios swings, y es a dónde salta el
// reproductor al elegirla.

import type { Repeticion } from "@/lib/repeticiones";

interface Props {
  reps: Repeticion[];
  elegida: number;
  onElegir: (i: number) => void;
}

export default function SelectorRepeticion({ reps, elegida, onElegir }: Props) {
  if (reps.length < 2) return null;
  return (
    <section className="flex flex-wrap items-baseline gap-x-3 gap-y-2 rounded-lg border border-zinc-800 bg-zinc-900/40 p-3">
      <span className="text-sm font-medium">Repetición</span>
      <div className="flex flex-wrap gap-2">
        {reps.map((r, i) => {
          const desde = r.eventos_frame.address ?? r.frame_start;
          const activa = i === elegida;
          return (
            <button
              key={r.rep}
              type="button"
              aria-pressed={activa}
              onClick={() => onElegir(i)}
              className={`rounded border px-3 py-1 text-sm ${activa ? "border-sky-500 bg-sky-900/60 text-sky-100" : "border-zinc-700 bg-zinc-900 text-zinc-300 hover:bg-zinc-800"}`}
            >
              {r.rep}
              {desde !== null && desde !== undefined && <span className={`ml-2 text-xs ${activa ? "text-sky-300/80" : "text-zinc-500"}`}>desde el cuadro {desde}</span>}
            </button>
          );
        })}
      </div>
      <span className="text-xs text-zinc-500">
        cambia toda la pantalla: los eventos, las fotos, el reproductor, la escala, las dos tablas y las métricas. Cada repetición se mide contra SU address.
      </span>
    </section>
  );
}
