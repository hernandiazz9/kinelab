// «Con este archivo»: las métricas del registro, una por una, con su número o
// con la razón por la que no hay número.
//
// Es la forma honesta de decir "el análisis depende de la calidad de la toma":
// en vez de una advertencia genérica, cada métrica dice si se pudo calcular y,
// si no, qué le faltó — fps, vista, altura declarada. Sale de `analysis.json`,
// que es donde el motor lo escribe (CONTRATO.md §El sextuplo de toda métrica).
// El archivo lo baja `page.tsx`, que lo necesita también para los avisos de
// arriba: acá llega ya leído.
//
// Nada se compone acá: ni el rótulo de la banda —es `uncertainty.method`, la
// frase que escribe el motor con la tolerancia real de cada evento ancla, que
// no siempre es ±1 cuadro— ni la lectura del juicio, que es el nombre del campo
// y nada más. Nada se compara contra nada: no hay rango, no hay semáforo, no hay
// puntaje (ADR-012). El MDC y el nivel se muestran como lo que son, la letra
// chica del instrumento, y mientras la tasa de cuadros esté sin verificar
// ninguna puede ser juicio (ADR-016).

import type { Analysis, Metrica } from "@/lib/api";
import { METRICAS, PROCEDENCIA, fmt, textoEscala } from "@/lib/etiquetas";

const DEC: Record<string, number> = { ms: 1, cm: 1, deg: 1, ratio: 2 };

/** "916,7 ms". El `-0` que sale de un desplazamiento nulo se muestra como 0. */
function valor(m: Metrica): string {
  const v = Object.is(m.value, -0) ? 0 : m.value;
  return `${fmt(v, DEC[m.unit] ?? 2)} ${m.unit}`;
}

function Fila({ id, m }: { id: string; m: Metrica }) {
  const calculada = m.value !== null;
  const dec = DEC[m.unit] ?? 2;
  return (
    <tr className={calculada ? undefined : "text-zinc-400"}>
      <td className="px-3 py-1.5 align-top">
        <span className="text-zinc-200">{METRICAS[id] ?? id}</span>
        <span className="ml-2 font-mono text-xs text-zinc-500">{id}</span>
      </td>
      <td className="px-3 py-1.5 text-right align-top tabular-nums">
        {calculada ? (
          <>
            <span className="text-zinc-100">{valor(m)}</span>
            {m.uncertainty && (
              <span className="block text-xs text-zinc-500">
                {/* Sin `method` va el rango solo: antes que inventarle un rótulo, ninguno. */}
                {m.uncertainty.method ? `${m.uncertainty.method}: ` : ""}
                {fmt(m.uncertainty.low, dec)} – {fmt(m.uncertainty.high, dec)}
              </span>
            )}
          </>
        ) : (
          <span className="italic">no se calculó</span>
        )}
      </td>
      <td className="px-3 py-1.5 align-top text-xs">
        {calculada ? (
          <span className="text-zinc-500">
            nivel {m.level} · MDC {m.mdc === null ? "sin medir" : `${fmt(m.mdc, 2)} ${m.unit}`} · fps mínimo {fmt(m.fps_min, 0)} · vista {m.view} ·{" "}
            {m.judgment_allowed ? "juicio habilitado (judgment_allowed)" : "descriptiva, no es juicio"}
          </span>
        ) : (
          <span className="text-amber-200/80">{m.null_reason}</span>
        )}
      </td>
    </tr>
  );
}

/** `rep` es la repetición ELEGIDA de `analysis.reps`, no `reps[0]`: la elige
 *  `page.tsx` y la resuelve `lib/repeticiones.ts`. Hasta el encargo 35 el índice
 *  estaba quemado acá en tres lugares, así que la pantalla mostraba siempre la
 *  primera aunque el clip tuviera dos swings. `frase` es la misma cadena que
 *  dicen las otras dos tablas: una sola fuente para los tres lugares. */
export default function Metricas({ analysis, rep, frase, error }: { analysis: Analysis | null; rep: Analysis["reps"][number] | null; frase: string | null; error: string | null }) {
  // `quality.scale_px` NO sirve acá: con dos o más repeticiones es la mediana
  // entre ellas y no es el divisor de ninguna. El divisor es `reps[i].scale_px`,
  // y desde el contrato 2.2.0 viene con el cuadro del que salió (`scale_frame`).
  const escala = rep ? textoEscala(rep.scale_px, rep.scale_source, rep.scale_frame) : null;
  return (
    <div>
      <div className="mt-6 mb-2 flex flex-wrap items-baseline gap-x-3">
        <h2 className="text-base font-semibold">Con este archivo</h2>
        <span className="text-sm text-zinc-400">qué se pudo medir y qué no, métrica por métrica</span>
      </div>

      {error && <p className="text-sm text-red-300">No se pudo leer analysis.json: {error}</p>}
      {!error && !analysis && <p className="text-sm text-zinc-400">leyendo analysis.json…</p>}

      {analysis && analysis.reps.length === 0 && (
        <p className="rounded border border-amber-700 bg-amber-950/40 p-3 text-sm">
          El motor no encontró ninguna repetición en este video, así que no hay ninguna métrica que calcular. Una persona quieta produce cero repeticiones a propósito: no métricas en null.
        </p>
      )}

      {analysis && analysis.reps.length > 0 && (
        <>
          {/* Cuál repetición es ésta, siempre — no sólo cuando hay más de una. La
              frase la compone `lib/repeticiones.ts` y es la misma que dicen la
              tabla por evento y la tabla por cuadro: hasta el encargo 35 salía de
              dos fuentes distintas y podían no coincidir. */}
          <p className="mb-2 text-sm text-zinc-400">
            {frase ?? `Repetición ${analysis.reps[0].rep} de ${analysis.reps.length}`}
            {analysis.reps.length > 1 && " — todo lo de esta pantalla es esa"}.
          </p>
          {/* La escala de ESTA repetición, al lado de los números que divide. Es el
              mismo divisor que usa la tabla por cuadro desde el encargo 33; antes
              eran dos y ninguno lo decía. Sin el campo (trabajo anterior), nada. */}
          {escala && <p className="mb-2 text-xs text-zinc-500">Los cm de abajo se dividieron por {escala}.</p>}
          <div className="overflow-x-auto rounded border border-zinc-800">
            <table className="w-full border-collapse text-sm [&_tbody_tr]:border-t [&_tbody_tr]:border-zinc-800">
              <tbody>
                {Object.entries((rep ?? analysis.reps[0]).metrics).map(([id, m]) => (
                  <Fila key={id} id={id} m={m} />
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-xs text-zinc-500">
            {/* Un analysis.json anterior a ADR-016 no trae procedencia: se dice, no se supone. */}
            Tasa de cuadros: {fmt(analysis.header.source.fps_real, 3)} fps · {PROCEDENCIA[analysis.header.source.fps_provenance ?? ""] ?? "procedencia sin declarar"} · camino{" "}
            {analysis.header.source.capture_path_id}. Motor {analysis.header.engine_version}, registro {analysis.header.registry_version}, contrato {analysis.header.schema_version}.
          </p>
        </>
      )}
    </div>
  );
}
