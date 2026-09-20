// Toda la data por evento de `datos-eventos.json`: primero el cuadro legible,
// después duraciones, picos, diferencias contra el address, y por último TODAS
// las columnas en cada evento. Nada se resume en un puntaje (ADR-012).
//
// Cada evento lleva su tolerancia en cuadros al lado del cuadro, cuando el motor
// la manda (`eventos_tol_frames`): es la banda de ese evento en ESA repetición y
// no siempre es 1 —el top de `vid1` sale con 4—. No se compone acá ni se pone un
// ±1 por defecto: el rótulo fijo «±1 cuadro» es lo que la auditoría del 16/9
// marcó como falso.
//
// «Todas» quiere decir todas menos las que ADR-018 retiró (`lib/retirados.ts`),
// que un trabajo calculado con un contrato anterior sigue trayendo en el
// archivo. Lo desconocido no se esconde: lo que no tiene nombre legible se
// muestra con su identificador.

import type { EventoId, Resumen } from "@/lib/api";
import { DURACIONES, EVENTOS, etiqueta, fmt, fmtCol, textoEscala, textoSubcuadro, textoTolerancia } from "@/lib/etiquetas";
import { sinRetirados } from "@/lib/retirados";
import { COLOR_EVENTO } from "./Reproductor";

interface FilaResumen {
  titulo: string;
  cols: string[];
  dec: number;
  unidad: string;
  signo?: boolean;
}

const FILAS: FilaResumen[] = [
  { titulo: "codo izquierdo / derecho", cols: ["elbow_left_deg", "elbow_right_deg"], dec: 0, unidad: "°" },
  { titulo: "rodilla izquierda / derecha", cols: ["knee_left_deg", "knee_right_deg"], dec: 0, unidad: "°" },
  { titulo: "cadera izquierda / derecha (hombro-cadera-rodilla)", cols: ["hip_left_deg", "hip_right_deg"], dec: 0, unidad: "°" },
  { titulo: "hombro izquierdo / derecho (codo-hombro-cadera)", cols: ["shoulder_left_deg", "shoulder_right_deg"], dec: 0, unidad: "°" },
  { titulo: "línea de hombros / línea de caderas / tronco", cols: ["shoulder_line_deg", "hip_line_deg", "trunk_lean_deg"], dec: 1, unidad: "°", signo: true },
  { titulo: "brazo izquierdo / derecho vs vertical", cols: ["arm_left_vs_vertical_deg", "arm_right_vs_vertical_deg"], dec: 0, unidad: "°", signo: true },
  { titulo: "altura de manos sobre los tobillos", cols: ["hands_height_pct"], dec: 0, unidad: " %" },
  { titulo: "manos vs centro de cadera (x)", cols: ["hands_x_vs_hip_bh"], dec: 2, unidad: " alturas", signo: true },
  { titulo: "pelvis vs address (dx / dy)", cols: ["pelvis_dx_vs_address_cm", "pelvis_dy_vs_address_cm"], dec: 1, unidad: " cm", signo: true },
  { titulo: "tórax vs address (dx / dy)", cols: ["thorax_dx_vs_address_cm", "thorax_dy_vs_address_cm"], dec: 1, unidad: " cm", signo: true },
  { titulo: "cabeza vs address (dx / dy)", cols: ["head_dx_vs_address_cm", "head_dy_vs_address_cm"], dec: 1, unidad: " cm", signo: true },
  { titulo: "manos vs address (dx / dy)", cols: ["hands_dx_vs_address_cm", "hands_dy_vs_address_cm"], dec: 1, unidad: " cm", signo: true },
  { titulo: "pelvis vs address (dx / dy)", cols: ["pelvis_dx_vs_address_pct", "pelvis_dy_vs_address_pct"], dec: 1, unidad: " % altura", signo: true },
  { titulo: "tórax vs address (dx / dy)", cols: ["thorax_dx_vs_address_pct", "thorax_dy_vs_address_pct"], dec: 1, unidad: " % altura", signo: true },
  { titulo: "cabeza vs address (dx / dy)", cols: ["head_dx_vs_address_pct", "head_dy_vs_address_pct"], dec: 1, unidad: " % altura", signo: true },
  { titulo: "manos vs address (dx / dy)", cols: ["hands_dx_vs_address_pct", "hands_dy_vs_address_pct"], dec: 1, unidad: " % altura", signo: true },
  { titulo: "velocidad de manos", cols: ["hands_speed_cm_s"], dec: 0, unidad: " cm/s" },
  { titulo: "velocidad de manos", cols: ["hands_speed_bh_s"], dec: 2, unidad: " alturas/s" },
  { titulo: "altura del cuerpo", cols: ["body_height_px"], dec: 0, unidad: " px" },
  { titulo: "banderas de plausibilidad (0 = limpio)", cols: ["plausibility_flags"], dec: 0, unidad: "" },
];

const PICOS: Record<string, string> = {
  hands_speed_bh_s: "velocidad de manos (alturas/s)",
  hands_speed_cm_s: "velocidad de manos (cm/s)",
};

const th = "px-3 py-1.5 text-left font-medium";
const td = "px-3 py-1 tabular-nums";
const tabla = "w-full border-collapse text-sm [&_tbody_tr]:border-t [&_tbody_tr]:border-zinc-800";
const h2 = "mt-6 mb-2 text-base font-semibold";

function Cabecera({ evs, resumen, onIr }: { evs: EventoId[]; resumen: Resumen; onIr: (n: number) => void }) {
  return (
    <thead className="bg-zinc-900">
      <tr>
        <th className={th}></th>
        {evs.map((ev) => {
          const f = resumen.eventos_frame[ev];
          const tol = textoTolerancia(resumen.eventos_tol_frames?.[ev]);
          const sub = textoSubcuadro(resumen.eventos_subcuadro?.[ev]);
          return (
            <th key={ev} className={th}>
              <button type="button" className="hover:underline" style={{ color: COLOR_EVENTO[ev] }} onClick={() => f !== undefined && onIr(f)} title="ir a ese cuadro">
                {EVENTOS[ev]}
              </button>
              {f !== undefined && (
                <span className="block text-xs font-normal text-zinc-500">
                  cuadro {f} · {fmt(resumen.eventos_t_s[ev], 3)} s{tol && ` · ${tol}`}
                </span>
              )}
              {sub && <span className="block text-xs font-normal text-zinc-400">{sub}</span>}
            </th>
          );
        })}
      </tr>
    </thead>
  );
}

export default function TablaEventos({ resumen, onIr }: { resumen: Resumen; onIr: (n: number) => void }) {
  const evs = (Object.keys(EVENTOS) as EventoId[]).filter((k) => resumen.en_cada_evento[k]);
  const valor = (ev: EventoId, col: string) => resumen.en_cada_evento[ev]?.[col] ?? null;
  const filas = FILAS.filter((f) => evs.some((ev) => f.cols.some((c) => valor(ev, c) !== null)));
  const celda = (f: FilaResumen, ev: EventoId) => {
    const vals = f.cols.map((c) => valor(ev, c));
    if (vals.every((v) => v === null)) return "—";
    return vals.map((v) => fmt(v, f.dec, f.signo)).join(" / ") + f.unidad;
  };
  const difs = Object.keys(resumen.diferencias_vs_address);
  const difCols = Array.from(new Set(difs.flatMap((k) => Object.keys(resumen.diferencias_vs_address[k]))));
  const duraciones = Object.entries(resumen.duraciones);
  const picos = sinRetirados(Object.entries(resumen.picos), ([k]) => k);
  const columnas = sinRetirados(resumen.columnas, (c) => c);

  if (evs.length === 0) {
    return <p className="mt-6 rounded border border-amber-700 bg-amber-950/40 p-3 text-sm">El motor no encontró ningún evento (address, top, impacto) en este video: no hay tabla por evento. La tabla por cuadro está abajo igual.</p>;
  }

  // Contra qué cuadro se mide cada `*_vs_address_*` y con qué escala se
  // convirtieron los cm, tal como los manda el motor. Sin address, `explore.py`
  // cae al cuadro 0: los valores no cambian, pero ocho filas se llaman «vs
  // address» y no hay address, y eso hasta hoy no se decía en ningún lado.
  const escala = textoEscala(resumen.escala_px, resumen.escala_fuente, resumen.escala_cuadro);
  const ref = resumen.referencia_fuente;
  const cual = resumen.repeticion_mostrada;
  const cuantas = resumen.repeticiones;

  return (
    <div>
      <h2 className={h2}>En cada evento</h2>
      {cual && cuantas !== undefined && cuantas > 0 && (
        <p className="mb-2 text-sm text-zinc-400">
          Repetición {cual} de {cuantas}: todo lo de esta pantalla —los eventos, las fotos, el video con los palitos, la tabla por cuadro y las métricas— es esa repetición.
          {cuantas > 1 && " Las otras están en analysis.json; elegir cuál se muestra todavía no se puede."}
        </p>
      )}
      {(ref || escala) && (
        <p className="mb-2 text-xs text-zinc-500">
          {ref && `Las filas «vs address» se miden contra el ${ref === "address" ? `address (cuadro ${resumen.referencia_cuadro})` : ref}. `}
          {escala && `Los cm salen de dividir por ${escala}.`}
        </p>
      )}
      <div className="overflow-x-auto rounded border border-zinc-800">
        <table className={tabla}>
          <Cabecera evs={evs} resumen={resumen} onIr={onIr} />
          <tbody>
            {filas.map((f, i) => (
              <tr key={i}>
                <td className={`${td} text-zinc-300`}>{f.titulo}</td>
                {evs.map((ev) => (
                  <td key={ev} className={td}>
                    {celda(f, ev)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <div>
          <h2 className={`${h2} mt-0`}>Duraciones</h2>
          <div className="rounded border border-zinc-800">
            <table className={tabla}>
              <tbody>
                {duraciones.length === 0 && (
                  <tr>
                    <td className={td}>—</td>
                  </tr>
                )}
                {duraciones.map(([k, v]) => (
                  <tr key={k}>
                    <td className={`${td} text-zinc-300`}>{DURACIONES[k] ?? k}</td>
                    <td className={`${td} text-right`}>{k.endsWith("_ms") ? `${fmt(v, 1)} ms` : k === "tempo_ratio" ? `${fmt(v, 2)} : 1` : fmt(v, 2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div>
          <h2 className={`${h2} mt-0`}>Picos (máximo en todo el clip)</h2>
          <div className="rounded border border-zinc-800">
            <table className={tabla}>
              <tbody>
                {picos.length === 0 && (
                  <tr>
                    <td className={td}>—</td>
                  </tr>
                )}
                {picos.map(([k, v]) => (
                  <tr key={k}>
                    <td className={`${td} text-zinc-300`}>{PICOS[k] ?? k}</td>
                    <td className={`${td} text-right`}>{fmt(v, k.includes("bh_s") ? 2 : 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {difs.length > 0 && (
        <>
          <h2 className={h2}>Diferencias contra el address (ángulos)</h2>
          <div className="overflow-x-auto rounded border border-zinc-800">
            <table className={tabla}>
              <thead className="bg-zinc-900">
                <tr>
                  <th className={th}></th>
                  {difs.map((k) => {
                    const ev = k.replace(/_vs_address$/, "") as EventoId;
                    return (
                      <th key={k} className={th} style={{ color: COLOR_EVENTO[ev] }}>
                        {EVENTOS[ev] ?? ev} − address
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {difCols.map((c) => (
                  <tr key={c}>
                    <td className={`${td} text-zinc-300`} title={c}>
                      {etiqueta(c).nombre}
                    </td>
                    {difs.map((k) => (
                      <td key={k} className={td}>
                        {fmt(resumen.diferencias_vs_address[k][c], 1, true)}°
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      <details className="mt-6">
        <summary className="cursor-pointer text-base font-semibold">Todas las variables en cada evento ({columnas.length} columnas)</summary>
        <div className="mt-2 overflow-x-auto rounded border border-zinc-800">
          <table className={tabla}>
            <Cabecera evs={evs} resumen={resumen} onIr={onIr} />
            <tbody>
              {columnas.map((c) => (
                <tr key={c}>
                  <td className={`${td} text-zinc-300`}>
                    {etiqueta(c).nombre} <span className="font-mono text-xs text-zinc-500">{c}</span>
                  </td>
                  {evs.map((ev) => (
                    <td key={ev} className={td}>
                      {fmtCol(c, valor(ev, c))}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>

      <details className="mt-4">
        <summary className="cursor-pointer text-base font-semibold">Calidad según el motor (analysis.json → quality)</summary>
        <pre className="mt-2 overflow-x-auto rounded border border-zinc-800 bg-zinc-950 p-3 text-xs">{JSON.stringify(resumen.calidad, null, 2)}</pre>
      </details>
    </div>
  );
}
