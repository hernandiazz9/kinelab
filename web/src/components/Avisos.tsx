// Lo que hay que leer ANTES de cualquier número (ADR-016, invariante 2).
//
// Cuando el trabajo tiene `analysis.json`, esto es `analysis.warnings` entero,
// en orden y tal cual: es la lista que arma el motor (`kinelab/explore.py:345`,
// `[AVISO, *gate_notes, *warnings]`) y de la que `datos-eventos.json` copia
// `aviso`, `fps_aviso` y `gate_diria`. Mostrar las copias además de la lista
// repetía frases; mostrar sólo las copias dejaba afuera los avisos que el motor
// agregue después, que la pantalla no tiene por qué conocer de antemano.
//
// Sin `analysis.json` quedan las tres copias, que es lo único que hay. Ése es
// también el estado mientras el archivo se está bajando, y es a propósito: las
// copias son un subconjunto de `warnings`, así que en el peor caso se ve de
// menos por un instante, nunca un número sin su aviso.
//
// `fps_note` no viene de ahí: sale de `capture.json` y no está en `warnings`.
//
// Las dos últimas líneas son lo único que compone la pantalla, y hablan de la
// pantalla: qué versión del contrato trae el archivo y qué campos suyos no se
// están mostrando. Van separadas del resto a propósito.

import type { Analysis, FichaArchivo, Resumen } from "@/lib/api";
import { AVISO_RETIRADOS, CONTRATO_VIGENTE, contratoAnterior, retiradosEn } from "@/lib/retirados";

export default function Avisos({ resumen, archivo, analysis }: { resumen: Resumen; archivo: FichaArchivo | null; analysis: Analysis | null }) {
  const note = archivo?.fps_note ?? null;
  const delMotor = analysis?.warnings ?? null;
  const version = analysis?.header.schema_version ?? null;
  const viejo = contratoAnterior(version);
  const retirados = retiradosEn([...resumen.columnas, ...Object.keys(resumen.picos)]);

  return (
    <section className="rounded-lg border border-amber-700 bg-amber-950/30 p-3 text-sm">
      {delMotor ? (
        delMotor.map((w, i) => (
          <p key={i} className={i === 0 ? "font-medium text-amber-200" : "mt-2 text-amber-100"}>
            {w}
          </p>
        ))
      ) : (
        <>
          <p className="font-medium text-amber-200">{resumen.aviso}</p>
          {resumen.fps_aviso && <p className="mt-2 text-amber-100">{resumen.fps_aviso}</p>}
        </>
      )}

      {note && (
        <p className="mt-2 text-amber-100">
          <span className="font-medium">El fps que se usó no es el que sale de contar todos los deltas del archivo.</span> {note}
        </p>
      )}

      {/* Sin `analysis.json` no hay `warnings`, y las razones del gate sólo están acá. */}
      {!delMotor && resumen.gate_diria.length > 0 && <p className="mt-2 text-amber-200/90">El gate diría: {resumen.gate_diria.join(" · ")}</p>}

      {(viejo || retirados.length > 0) && (
        <div className="mt-3 border-t border-amber-800/60 pt-2 text-amber-200/90">
          {viejo && (
            <p>
              Este trabajo se calculó con un contrato anterior: su <code className="font-mono text-xs">analysis.json</code> es {version} y el vigente es {CONTRATO_VIGENTE}. Se corrige re-analizando el video.
            </p>
          )}
          {retirados.length > 0 && (
            <p className={viejo ? "mt-2" : undefined}>
              {AVISO_RETIRADOS}: <span className="font-mono text-xs">{retirados.join(" · ")}</span>
            </p>
          )}
        </div>
      )}
    </section>
  );
}
