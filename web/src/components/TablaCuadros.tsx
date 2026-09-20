"use client";

// `datos-por-cuadro.csv` entero, navegable: filtro de columnas, filas
// virtualizadas (miles de cuadros × ~116 columnas no entran en el DOM de una),
// clic en una fila → ese cuadro en el reproductor, y la fila del cuadro actual
// resaltada.
//
// El número de columnas: hoy son **116 con altura declarada del atleta y 107
// sin ella** (las ocho en cm y `hands_speed_cm_s` salen cuando no hay altura).
// El «118» que decía esta línea era de los CSV congelados de `web/public/demo/`,
// anteriores a ADR-018 —que retiró tres columnas— y al encargo 33, que agregó
// `escala_px`. La cuenta que se muestra abajo sale del archivo, no de acá.
//
// «Entero» menos las columnas que ADR-018 retiró (`lib/retirados.ts`), que el
// CSV de un trabajo calculado con un contrato anterior sigue trayendo. El
// archivo se puede descargar tal cual: lo que no se hace es mostrarlas como si
// fueran una medición.
//
// Las filas de la repetición elegida van con fondo más claro: son las únicas que
// tienen cm —los dividió SU escala— y las únicas medidas contra SU address. Al
// cambiar de repetición la tabla se lleva sola al primer cuadro de la nueva.
//
// Y arriba de la tabla, **con qué escala se dividieron los cm y contra qué
// cuadro se miden los «vs address»**: hasta el encargo 33 esta tabla convertía
// con el `body_height_px` de cada cuadro mientras las métricas usaban la escala
// de la repetición, así que la misma pantalla mostraba dos números distintos
// para el mismo evento —hasta 4,4 cm— y ninguno decía cuál había usado. Si el
// motor no los manda (trabajo anterior), no se muestra nada: no se inventa.

import { useEffect, useMemo, useRef, useState } from "react";
import { bajarTexto } from "@/lib/api";
import { parseCsv, type Tabla } from "@/lib/csv";
import { etiqueta, fmt, textoEscala } from "@/lib/etiquetas";
import type { Repeticion } from "@/lib/repeticiones";
import { esRetirado } from "@/lib/retirados";

const ALTO = 26; // px por fila; fijo para poder virtualizar
const VENTANA = 50;

interface Props {
  url: string;
  cuadroActual: number;
  onIr: (n: number) => void;
  /** La repetición elegida (`lib/repeticiones.ts`): de ahí salen la escala, la
   *  referencia de los «vs address» y el tramo de filas que se marca. */
  rep?: Repeticion | null;
  /** «Repetición N de M», la misma frase que dicen las otras dos tablas. `null`
   *  en un trabajo que no declara cuál es: ahí no se inventa ninguna. */
  frase?: string | null;
}

/** La línea de arriba de la tabla: con qué escala se dividieron los cm, contra
 *  qué cuadro se miden los «vs address», y cuál de las repeticiones es ésta.
 *  Cada pieza se muestra sólo si el motor la mandó. */
function Cabecera({ rep, frase }: { rep?: Repeticion | null; frase?: string | null }) {
  if (!rep) return null;
  const escala = textoEscala(rep.escala_px, rep.escala_fuente, rep.escala_cuadro);
  const ref = rep.referencia_fuente;
  const partes: string[] = [];
  if (escala) partes.push(`Los cm de esta tabla se dividieron por ${escala}.`);
  if (ref) partes.push(`Las columnas «vs address» se miden contra el ${ref === "address" ? `address (cuadro ${rep.referencia_cuadro})` : ref}.`);
  if (frase) partes.push(`Escala y address son los de la ${frase.toLowerCase()}; los cuadros fuera de una repetición no tienen cm.`);
  if (partes.length === 0) return null;
  return <p className="text-xs text-zinc-500">{partes.join(" ")}</p>;
}

export default function TablaCuadros({ url, cuadroActual, onIr, rep, frase }: Props) {
  const [tabla, setTabla] = useState<Tabla | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filtro, setFiltro] = useState("");
  const [inicio, setInicio] = useState(0);
  const cajaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let vivo = true;
    bajarTexto(url)
      .then((t) => {
        if (vivo) setTabla(parseCsv(t));
      })
      .catch((e: Error) => {
        if (vivo) setError(e.message);
      });
    return () => {
      vivo = false;
    };
  }, [url]);

  // Al cambiar de repetición, la tabla se lleva al primer cuadro de la nueva: el
  // contenido de la cabecera y el tramo marcado cambian, y dejar la vista en el
  // tramo de la anterior haría mirar filas grises creyendo que son las suyas. El
  // filtro de columnas NO se toca a propósito: es una preferencia de quien mira
  // («mostrame las rodillas») y no dice nada de ninguna repetición.
  const desde = rep?.frame_start ?? null;
  useEffect(() => {
    if (desde === null) return;
    const el = cajaRef.current;
    if (!el) return;
    el.scrollTop = Math.max(0, desde * ALTO - ALTO * 2);
  }, [desde]);

  // `i` es la posición en el CSV y se conserva: es con lo que se lee cada fila.
  // Sacar una columna acá no corre a las demás.
  const mostrables = useMemo(() => (tabla ? tabla.columnas.map((c, i) => ({ c, i, e: etiqueta(c) })).filter(({ c }) => !esRetirado(c)) : []), [tabla]);

  const cols = useMemo(() => {
    const q = filtro.trim().toLowerCase();
    return mostrables.filter(({ c, e, i }) => i === 0 || !q || c.toLowerCase().includes(q) || e.nombre.toLowerCase().includes(q));
  }, [mostrables, filtro]);

  if (error) return <p className="text-sm text-red-300">No se pudo leer el CSV: {error}</p>;
  if (!tabla) return <p className="text-sm text-zinc-500">cargando la tabla por cuadro…</p>;

  const n = tabla.filas.length;
  const fin = Math.min(n, inicio + VENTANA);
  const onScroll = () => {
    const el = cajaRef.current;
    if (el) setInicio(Math.max(0, Math.floor(el.scrollTop / ALTO) - 5));
  };
  const irAlActual = () => {
    const el = cajaRef.current;
    if (el) el.scrollTop = Math.max(0, cuadroActual * ALTO - el.clientHeight / 2 + ALTO);
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <input
          type="search"
          placeholder="filtrar columnas: codo, rodilla, muñeca, score…"
          value={filtro}
          onChange={(e) => setFiltro(e.target.value)}
          className="w-80 rounded border border-zinc-700 bg-zinc-900 px-2 py-1"
        />
        <span className="text-zinc-400">
          {n} cuadros × {mostrables.length} columnas{filtro && ` · mostrando ${cols.length}`}
          {desde !== null && rep?.frame_end !== null && rep?.frame_end !== undefined && ` · esta repetición: ${desde}–${rep.frame_end}`}
        </span>
        <button type="button" onClick={irAlActual} className="rounded border border-zinc-700 bg-zinc-900 px-2 py-1 hover:bg-zinc-800">
          ir al cuadro actual ({cuadroActual})
        </button>
        <span className="text-xs text-zinc-500">clic en una fila: ese cuadro en el reproductor</span>
      </div>
      <Cabecera rep={rep} frase={frase} />
      <div ref={cajaRef} onScroll={onScroll} className="max-h-[60vh] overflow-auto rounded border border-zinc-800">
        <table className="border-collapse whitespace-nowrap text-xs tabular-nums">
          <thead className="sticky top-0 z-20 bg-zinc-900">
            <tr>
              {cols.map(({ c, e, i }) => (
                <th key={c} title={c} className={`px-2 py-1 text-left font-medium ${i === 0 ? "sticky left-0 z-30 bg-zinc-900" : ""}`}>
                  {e.nombre}
                  {e.unidad && <span className="text-zinc-500"> ({e.unidad})</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {inicio > 0 && (
              <tr style={{ height: inicio * ALTO }}>
                <td colSpan={cols.length} />
              </tr>
            )}
            {tabla.filas.slice(inicio, fin).map((fila, k) => {
              const r = inicio + k;
              const f = fila[0] ?? r;
              const actual = f === cuadroActual;
              // Las filas de ESTA repetición, marcadas: son las únicas que tienen
              // cm (los dividió su escala) y las únicas medidas contra su address.
              // Afuera del tramo las ocho columnas en cm están vacías y conviene
              // que se vea por qué.
              const dentro = f !== null && desde !== null && rep?.frame_end !== null && rep?.frame_end !== undefined && Number(f) >= desde && Number(f) <= rep.frame_end;
              const fondo = actual ? "bg-sky-900/60" : dentro ? "bg-zinc-800/40 hover:bg-zinc-800/70" : "hover:bg-zinc-800/60";
              return (
                <tr key={r} onClick={() => onIr(Number(f))} style={{ height: ALTO }} className={`cursor-pointer border-t border-zinc-800/60 ${fondo}`}>
                  {cols.map(({ c, i, e }) => (
                    <td key={c} className={`px-2 ${i === 0 ? `sticky left-0 z-10 font-medium ${actual ? "bg-sky-900" : dentro ? "bg-zinc-800" : "bg-zinc-950"}` : ""}`}>
                      {fmt(fila[i], e.dec, e.signo)}
                    </td>
                  ))}
                </tr>
              );
            })}
            {fin < n && (
              <tr style={{ height: (n - fin) * ALTO }}>
                <td colSpan={cols.length} />
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
