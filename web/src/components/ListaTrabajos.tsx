"use client";

// Los trabajos que ya están en disco: los que se subieron antes (incluso en otra
// sesión del servidor) y los ejemplos que deja otro proceso. Clic en uno y se
// abre como si acabara de terminar, sin volver a subir el video. No se borra
// nada desde acá.

import { ETAPA, type EventoId, type TrabajoFila } from "@/lib/api";
import { EVENTOS, fecha, fmt } from "@/lib/etiquetas";

interface Props {
  filas: TrabajoFila[];
  actual: string | null;
  cargando: boolean;
  error: string | null;
  onElegir: (id: string) => void;
}

const ORDEN_EVENTOS = Object.keys(EVENTOS) as EventoId[];

/** La segunda línea de cada fila: qué es ese trabajo, en una línea. */
function detalle(f: TrabajoFila): string {
  if (f.estado !== "listo") return f.error ? `error · ${f.error}` : (ETAPA[f.estado] ?? f.estado);
  const partes: string[] = [];
  if (f.cuadros !== null) partes.push(`${f.cuadros} cuadros`);
  if (f.fps_archivo !== null) partes.push(`${fmt(f.fps_archivo, 3)} fps`);
  partes.push(f.altura_m !== null ? `${fmt(f.altura_m, 2)} m` : "sin altura");
  const ev = f.eventos_frame;
  if (ev) {
    const nombrados = ORDEN_EVENTOS.filter((k) => ev[k] !== undefined).map((k) => `${EVENTOS[k]} ${ev[k]}`);
    if (nombrados.length > 0) partes.push(nombrados.join(" · "));
  }
  return partes.join(" · ");
}

export default function ListaTrabajos({ filas, actual, cargando, error, onElegir }: Props) {
  return (
    <section className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
      <div className="flex flex-wrap items-baseline gap-x-3">
        <h2 className="text-base font-semibold">Trabajos anteriores y ejemplos</h2>
        <span className="text-xs text-zinc-500">
          {cargando && filas.length === 0 ? "buscando…" : `${filas.length} en data/exploracion/`}
        </span>
      </div>

      {error && <p className="mt-2 text-sm text-red-300">No se pudo leer la lista: {error}</p>}
      {!error && !cargando && filas.length === 0 && <p className="mt-2 text-sm text-zinc-400">Todavía no hay ninguno. Subí un video.</p>}

      {filas.length > 0 && (
        <ul className="mt-2 max-h-72 overflow-y-auto">
          {filas.map((f) => {
            const abierto = f.id === actual;
            return (
              <li key={f.id}>
                <button
                  type="button"
                  onClick={() => onElegir(f.id)}
                  aria-current={abierto ? "true" : undefined}
                  className={`w-full rounded border-l-2 px-2 py-1.5 text-left text-sm hover:bg-zinc-800/60 ${abierto ? "border-sky-500 bg-zinc-800/60" : "border-transparent"}`}
                >
                  <span className="flex flex-wrap items-baseline gap-x-2">
                    {f.origen === "ejemplo" && <span className="rounded bg-emerald-900/60 px-1.5 py-0.5 text-xs text-emerald-200">ejemplo</span>}
                    <span className="font-medium">{f.video}</span>
                    <span className="text-xs text-zinc-500">
                      {fecha(f.creado)} · {f.vista}
                      {f.estado !== "listo" && ` · ${f.estado}`}
                    </span>
                  </span>
                  {f.etiqueta && <span className="block text-xs text-emerald-200/80">{f.etiqueta}</span>}
                  <span className={`block text-xs ${f.estado === "error" ? "text-red-300" : "text-zinc-400"}`}>{detalle(f)}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
