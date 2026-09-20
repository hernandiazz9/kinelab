// Las repeticiones de un trabajo, en UN solo lugar.
//
// Desde el encargo 35 `datos-eventos.json` publica `repeticiones_detalle`: una
// entrada por repetición con sus eventos, su escala, sus duraciones, sus picos,
// la tabla por evento y las diferencias contra SU address. Los campos de primer
// nivel siguen ahí, duplicando la repetición 1, y son transitorios: los retira
// el encargo que regenera todo (R10).
//
// Por qué el respaldo y no leer el detalle a secas: los 19 trabajos de
// `data/exploracion/` y los 3 de la demo se calcularon ANTES del 33 (sus
// `analysis.json` son 1.0.0 y 1.2.0) y **no tienen `repeticiones_detalle`**. Hoy
// lo único que los hace visibles son los campos de primer nivel. Así que un
// trabajo viejo entra acá como **una repetición única** armada con ellos, y se
// sigue viendo como se veía: sin selector, con los mismos números.
//
// Esto vive en un módulo y no repartido por los componentes a propósito. La
// pregunta «cuál es la repetición que se está mirando» se contesta una vez y
// baja por props; si cada tabla la resolviera por su cuenta, dos de ellas
// podrían quedar mirando repeticiones distintas y nada lo diría — que es
// exactamente el problema que el encargo 35 midió en el motor (la repetición 2
// se medía contra el address de la 1: 4,84 cm contra un MDC de 2,42).

import type { Analysis, EscalaFuente, EventoId, Eventos, Fila, Resumen, Subcuadro } from "@/lib/api";

/** Una repetición tal como la pantalla la necesita, venga del detalle o del
 *  respaldo. Los nombres son los de `datos-eventos.json` porque es el mismo dato:
 *  el motor publica el detalle con las mismas claves que el primer nivel. */
export interface Repeticion {
  rep: number;
  /** Los cuadros que abarca. `null` en el respaldo: un trabajo viejo no los publica. */
  frame_start: number | null;
  frame_end: number | null;
  eventos_frame: Eventos;
  eventos_t_s: Eventos;
  eventos_tol_frames?: Partial<Record<EventoId, number>>;
  eventos_subcuadro?: Partial<Record<EventoId, Subcuadro>>;
  escala_px: number | null;
  escala_fuente: EscalaFuente | null;
  escala_cuadro: number | null;
  referencia_cuadro: number | null;
  referencia_fuente: string | null;
  duraciones: Record<string, number>;
  picos: Record<string, number | null>;
  en_cada_evento: Partial<Record<EventoId, Fila>>;
  diferencias_vs_address: Record<string, Fila>;
}

export interface Repeticiones {
  /** Las que la pantalla puede mostrar, en orden. Nunca vacía si hay algo que mostrar. */
  lista: Repeticion[];
  /** Cuántas encontró el motor. Puede ser MAYOR que `lista.length` en un trabajo
   *  viejo: su `analysis.json` puede tener tres repeticiones y su
   *  `datos-eventos.json` publicar sólo la primera. `null` si nadie lo dice. */
  total: number | null;
  /** `true` = las de arriba salen del primer nivel, no de `repeticiones_detalle`.
   *  Es la marca del trabajo viejo: sin selector y sin cambiar nada de lo que ya
   *  mostraba. */
  respaldo: boolean;
}

/** Las repeticiones de este trabajo. `analysis` sólo se usa para el total cuando
 *  el resumen no lo dice, que es el caso del trabajo viejo. */
export function repeticionesDe(resumen: Resumen, analysis?: Analysis | null): Repeticiones {
  const detalle = resumen.repeticiones_detalle;
  if (detalle && detalle.length > 0) {
    return { lista: detalle, total: resumen.repeticiones ?? detalle.length, respaldo: false };
  }
  // El respaldo: el primer nivel, como una repetición única. No se inventa nada
  // que no esté — un trabajo viejo no trae `escala_px` ni `repeticion_mostrada`,
  // y esas piezas quedan en `null`, que es lo que la pantalla ya sabe no mostrar.
  const unica: Repeticion = {
    rep: resumen.repeticion_mostrada ?? 1,
    frame_start: null,
    frame_end: null,
    eventos_frame: resumen.eventos_frame ?? {},
    eventos_t_s: resumen.eventos_t_s ?? {},
    eventos_tol_frames: resumen.eventos_tol_frames,
    eventos_subcuadro: resumen.eventos_subcuadro,
    escala_px: resumen.escala_px ?? null,
    escala_fuente: resumen.escala_fuente ?? null,
    escala_cuadro: resumen.escala_cuadro ?? null,
    referencia_cuadro: resumen.referencia_cuadro ?? null,
    referencia_fuente: resumen.referencia_fuente ?? null,
    duraciones: resumen.duraciones ?? {},
    picos: resumen.picos ?? {},
    en_cada_evento: resumen.en_cada_evento ?? {},
    diferencias_vs_address: resumen.diferencias_vs_address ?? {},
  };
  return { lista: [unica], total: resumen.repeticiones ?? analysis?.reps?.length ?? null, respaldo: true };
}

/** La elegida, acotada: un índice que se fue de rango (cambió el trabajo antes de
 *  que el estado se resetee) no rompe la pantalla, devuelve la primera. */
export function elegir(reps: Repeticiones, i: number): Repeticion | null {
  if (reps.lista.length === 0) return null;
  return reps.lista[Math.min(Math.max(i, 0), reps.lista.length - 1)];
}

/** Las métricas de ESA repetición en `analysis.json`. Se busca por número de
 *  repetición y no por índice: los dos arreglos salen del mismo bucle del motor
 *  y coinciden, pero un trabajo viejo publica una sola entrada en la pantalla y
 *  puede tener varias en el `analysis.json`, y ahí el índice mentiría. */
export function repDelAnalysis(analysis: Analysis | null, rep: Repeticion | null): Analysis["reps"][number] | null {
  if (!analysis?.reps?.length) return null;
  if (!rep) return analysis.reps[0] ?? null;
  return analysis.reps.find((r) => r.rep === rep.rep) ?? analysis.reps[0] ?? null;
}

/** «Repetición 2 de 3». Una sola frase, para los tres lugares que la dicen: la
 *  tabla por evento, la tabla por cuadro y las métricas. Hasta el encargo 35 la
 *  componían por separado y de dos fuentes distintas. */
export function fraseRepeticion(rep: Repeticion | null, total: number | null): string | null {
  if (!rep) return null;
  return total && total > 0 ? `Repetición ${rep.rep} de ${total}` : `Repetición ${rep.rep}`;
}

/** Los nombres posibles de la foto de un evento, en orden de preferencia. Es el
 *  espejo de `kinelab.explore.foto_de_evento`: la repetición 1 conserva el nombre
 *  de siempre y las demás llevan la suya delante. Van PNG y JPG porque el motor
 *  escribe PNG y el exportador de la demo los pasa a JPEG
 *  (`kinelab/tools/exportar_demo.py`). */
export function nombresDeFoto(rep: number, evento: EventoId): string[] {
  const base = rep === 1 ? `evento-${evento}` : `evento-r${rep}-${evento}`;
  return [`${base}.png`, `${base}.jpg`];
}
