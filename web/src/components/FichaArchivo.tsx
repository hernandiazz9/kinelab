// La ficha del archivo tal como llegó: lo que dice el contenedor y lo que sale
// de contar los cuadros y medir sus PTS.
//
// Está antes que la pose —`prepare_take` escribe el `capture.json` antes de
// correr el modelo—, así que se muestra mientras el trabajo sigue procesando.
// Dos reglas de la casa acá adentro: el fps nunca aparece sin su procedencia al
// lado (ADR-016), y cuando el número efectivo difiere del bruto se muestran los
// dos con la nota que lo explica, nunca la corrección en silencio.

import type { FichaArchivo as Ficha } from "@/lib/api";
import { fmt, PROCEDENCIA } from "@/lib/etiquetas";

function Dato({ que, children, ancho }: { que: string; children: React.ReactNode; ancho?: boolean }) {
  return (
    <div className={ancho ? "col-span-2 md:col-span-3" : undefined}>
      <dt className="text-xs text-zinc-500">{que}</dt>
      <dd className="tabular-nums">{children}</dd>
    </div>
  );
}

export default function FichaArchivo({ ficha, procesando }: { ficha: Ficha; procesando: boolean }) {
  const proc = PROCEDENCIA[ficha.fps_provenance] ?? ficha.fps_provenance;
  const brutoDistinto = ficha.fps_reproduccion_bruto !== null && ficha.fps_reproduccion_bruto !== ficha.fps_reproduccion;

  return (
    <section className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
      <div className="flex flex-wrap items-baseline gap-x-3">
        <h2 className="text-base font-semibold">El archivo</h2>
        <span className="text-xs text-zinc-500">{ficha.original}</span>
        {procesando && <span className="text-xs text-sky-400">ya se leyó; la pose sigue</span>}
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-3 text-sm md:grid-cols-3 lg:grid-cols-4">
        <Dato que="codec">{ficha.codec}</Dato>
        <Dato que="tamaño y rotación">
          {ficha.ancho}×{ficha.alto} px · {ficha.rotacion_deg}°
        </Dato>
        <Dato que="cuadros">{ficha.cuadros}</Dato>
        <Dato que="duración">{fmt(ficha.duracion_s, 3)} s</Dato>

        <Dato que="fps de reproducción (de los PTS)">
          {fmt(ficha.fps_reproduccion, 3)}
          {brutoDistinto && <span className="text-zinc-500"> · bruto {fmt(ficha.fps_reproduccion_bruto, 3)}</span>}
        </Dato>
        <Dato que="fps con el que se midió">
          {fmt(ficha.fps_real, 3)} <span className="text-amber-300">· {proc}</span>
        </Dato>
        <Dato que="tasa variable">
          {ficha.tasa_variable ? "sí" : "no"}
          <span className="text-zinc-500">
            {" "}
            · ratio {fmt(ficha.vfr_ratio, 3)}
            {ficha.vfr_ratio_bruto !== null && ficha.vfr_ratio_bruto !== ficha.vfr_ratio && ` (bruto ${fmt(ficha.vfr_ratio_bruto, 3)})`} · límite {fmt(ficha.vfr_ratio_max, 2)}
          </span>
        </Dato>
        <Dato que="primer delta de PTS">{ficha.primer_delta_s === null ? "—" : `${fmt(ficha.primer_delta_s * 1000, 1)} ms`}</Dato>

        <Dato que="camino de captura" ancho>
          {ficha.camino}
          <span className="text-zinc-500"> · {ficha.camino_calibrado === true ? "calibrado con cronómetro" : ficha.camino_calibrado === false ? "declarado, sin cronómetro" : "sin camino conocido"}</span>
        </Dato>
      </dl>

      {ficha.fps_note && <p className="mt-3 rounded border border-amber-800/60 bg-amber-950/20 p-2 text-sm text-amber-100">{ficha.fps_note}</p>}
    </section>
  );
}
