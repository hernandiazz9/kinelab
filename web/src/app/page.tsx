"use client";

// Una sola pantalla: subir un video → el overlay con los palitos en un
// reproductor con cámara lenta, cuadro a cuadro y zoom; las fotos por evento;
// y toda la data que el motor produce, en tablas. Sin login, sin sesiones, sin
// gate, sin puntaje.

import { useCallback, useEffect, useRef, useState } from "react";
import DosCuadros from "@/components/DosCuadros";
import ListaTrabajos from "@/components/ListaTrabajos";
import Reproductor, { COLOR_EVENTO, type ReproductorHandle } from "@/components/Reproductor";
import Subida from "@/components/Subida";
import TablaCuadros from "@/components/TablaCuadros";
import TablaEventos from "@/components/TablaEventos";
import {
  ETAPA,
  archivoUrl,
  getTrabajo,
  listarTrabajos,
  olvidarUltimoTrabajo,
  ponerTrabajoEnLaUrl,
  recordarTrabajo,
  subirVideo,
  trabajoDeLaUrl,
  ultimoTrabajoId,
  type EventoId,
  type Trabajo,
  type TrabajoFila,
} from "@/lib/api";
import { EVENTOS, fmt, textoSubcuadro } from "@/lib/etiquetas";

type Fase =
  | { tipo: "inicio" }
  | { tipo: "subiendo"; pct: number; nombre: string }
  | { tipo: "procesando"; trabajo: Trabajo }
  | { tipo: "listo"; trabajo: Trabajo }
  | { tipo: "error"; mensaje: string };

const SONDEO_MS = 500;

function faseDe(t: Trabajo): Fase {
  if (t.estado === "listo" && t.resumen) return { tipo: "listo", trabajo: t };
  if (t.estado === "error") return { tipo: "error", mensaje: t.error ?? "el trabajo falló sin detalle" };
  return { tipo: "procesando", trabajo: t };
}

export default function Pagina() {
  const [fase, setFase] = useState<Fase>({ tipo: "inicio" });
  const [cuadro, setCuadro] = useState(0);
  const [filas, setFilas] = useState<TrabajoFila[]>([]);
  const [lista, setLista] = useState<{ cargando: boolean; error: string | null }>({ cargando: true, error: null });
  const [nota, setNota] = useState<string | null>(null);
  const reproductor = useRef<ReproductorHandle>(null);
  const arranque = useRef(false);

  const refrescarLista = useCallback(() => {
    listarTrabajos()
      .then((f) => {
        setFilas(f);
        setLista({ cargando: false, error: null });
      })
      .catch((e: Error) => setLista({ cargando: false, error: e.message }));
  }, []);

  /** Abre un trabajo que ya está en disco: el mismo resultado, sin volver a subir nada. */
  const abrir = useCallback(
    (id: string) => {
      getTrabajo(id)
        .then((t) => {
          setNota(null);
          setCuadro(0);
          setFase(faseDe(t));
          recordarTrabajo(t.id);
          ponerTrabajoEnLaUrl(t.id);
        })
        .catch((e: Error) => {
          // Borrado del disco, o un id que no existe en la URL: se olvida y se sigue.
          olvidarUltimoTrabajo();
          ponerTrabajoEnLaUrl(null);
          setFase({ tipo: "inicio" });
          setNota(`No se pudo abrir el trabajo ${id}: ${e.message}`);
          refrescarLista();
        });
    },
    [refrescarLista],
  );

  // Al cargar: el trabajo de `?trabajo=<id>` si lo hay, si no el último (localStorage).
  useEffect(() => {
    if (arranque.current) return;
    arranque.current = true;
    const id = trabajoDeLaUrl() ?? ultimoTrabajoId();
    if (id) abrir(id);
  }, [abrir]);

  // La lista, al empezar y cada vez que un trabajo termina (así aparece el nuevo).
  const terminado = fase.tipo === "listo" ? fase.trabajo.id : fase.tipo === "error" ? "error" : null;
  useEffect(() => {
    refrescarLista();
  }, [terminado, refrescarLista]);

  // Sondeo mientras el backend trabaja.
  const idEnCurso = fase.tipo === "procesando" ? fase.trabajo.id : null;
  useEffect(() => {
    if (!idEnCurso) return;
    const timer = setInterval(() => {
      getTrabajo(idEnCurso)
        .then((t) => setFase(faseDe(t)))
        .catch((e: Error) => setFase({ tipo: "error", mensaje: e.message }));
    }, SONDEO_MS);
    return () => clearInterval(timer);
  }, [idEnCurso]);

  const subir = useCallback(async (archivo: File, alturaM: number | null) => {
    setFase({ tipo: "subiendo", pct: 0, nombre: archivo.name });
    try {
      const t = await subirVideo(archivo, alturaM, (p) => setFase({ tipo: "subiendo", pct: p, nombre: archivo.name }));
      setCuadro(0);
      setFase({ tipo: "procesando", trabajo: t });
      ponerTrabajoEnLaUrl(t.id);
    } catch (e) {
      setFase({ tipo: "error", mensaje: (e as Error).message });
    }
  }, []);

  const ir = useCallback((n: number) => reproductor.current?.irACuadro(n), []);
  const irArriba = useCallback(
    (n: number) => {
      ir(n);
      window.scrollTo({ top: 0, behavior: "smooth" });
    },
    [ir],
  );

  const ocupado = fase.tipo === "subiendo" || fase.tipo === "procesando";
  const abiertoId = fase.tipo === "listo" || fase.tipo === "procesando" ? fase.trabajo.id : null;

  return (
    <main className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-6">
      <header className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <h1 className="text-xl font-semibold">kinelab · exploración</h1>
        <p className="text-sm text-zinc-400">Subí un video de un swing: los palitos y toda la data que el motor produce. Sin gate, sin puntaje: números para mirar, no para juzgar.</p>
      </header>

      <section className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
        <Subida ocupado={ocupado} onSubir={subir} />
      </section>

      <ListaTrabajos filas={filas} actual={abiertoId} cargando={lista.cargando} error={lista.error} onElegir={abrir} />

      {nota && <p className="text-sm text-amber-300">{nota}</p>}

      {fase.tipo === "subiendo" && (
        <Progreso titulo={`subiendo ${fase.nombre}`} fraccion={fase.pct} detalle={`${Math.round(fase.pct * 100)} %`} />
      )}
      {fase.tipo === "procesando" && (
        <Progreso
          titulo={`${fase.trabajo.video} · ${ETAPA[fase.trabajo.estado]}`}
          fraccion={fase.trabajo.progreso.total ? fase.trabajo.progreso.cuadros / fase.trabajo.progreso.total : null}
          detalle={fase.trabajo.progreso.total ? `${fase.trabajo.progreso.cuadros} / ${fase.trabajo.progreso.total} cuadros` : ""}
        />
      )}
      {fase.tipo === "error" && (
        <section className="rounded-lg border border-red-800 bg-red-950/40 p-4 text-sm">
          <strong>No salió.</strong> {fase.mensaje}
        </section>
      )}

      {fase.tipo === "listo" && <Resultado trabajo={fase.trabajo} cuadro={cuadro} onCuadro={setCuadro} ir={ir} irArriba={irArriba} reproductor={reproductor} />}
    </main>
  );
}

function Progreso({ titulo, fraccion, detalle }: { titulo: string; fraccion: number | null; detalle: string }) {
  return (
    <section className="rounded-lg border border-zinc-800 p-4 text-sm">
      <div className="flex justify-between">
        <span>{titulo}</span>
        <span className="tabular-nums text-zinc-400">{detalle}</span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded bg-zinc-800">
        {fraccion === null ? <div className="h-full w-1/3 animate-pulse bg-sky-600" /> : <div className="h-full bg-sky-500 transition-[width]" style={{ width: `${Math.round(fraccion * 100)}%` }} />}
      </div>
    </section>
  );
}

function Resultado({
  trabajo,
  cuadro,
  onCuadro,
  ir,
  irArriba,
  reproductor,
}: {
  trabajo: Trabajo;
  cuadro: number;
  onCuadro: (n: number) => void;
  ir: (n: number) => void;
  irArriba: (n: number) => void;
  reproductor: React.RefObject<ReproductorHandle | null>;
}) {
  const r = trabajo.resumen!;
  const [verDosCuadros, setVerDosCuadros] = useState(false);
  const overlay = archivoUrl(trabajo, "overlay.mp4");
  const subImpacto = r.eventos_subcuadro?.impact;
  // Los dos cuadros entre los que cayó el instante estimado, si los hay.
  const parImpacto = subImpacto && subImpacto.frame_before !== null && subImpacto.frame_after !== null ? { antes: subImpacto.frame_before, despues: subImpacto.frame_after } : null;
  const csv = archivoUrl(trabajo, "datos-por-cuadro.csv");
  const fotos = (Object.keys(EVENTOS) as EventoId[]).filter((ev) => archivoUrl(trabajo, `evento-${ev}.png`));
  const descargas: [string, string][] = [
    ["datos-por-cuadro.csv", "CSV por cuadro"],
    ["datos-eventos.json", "JSON por evento"],
    ["analysis.json", "analysis.json"],
    ["capture.json", "capture.json"],
    ["overlay.mp4", "video con palitos"],
  ];

  return (
    <>
      <section className="rounded-lg border border-amber-800/60 bg-amber-950/20 p-3 text-sm">
        {/* El rótulo de un ejemplo lo trae `trabajo.json`: acá no se inventa ninguno. */}
        {trabajo.origen === "ejemplo" && <p className="mb-1 font-medium text-emerald-300">{trabajo.etiqueta ?? "ejemplo"}</p>}
        <p>{r.aviso}</p>
        {r.gate_diria.length > 0 && (
          <p className="mt-1 text-amber-200">
            El gate diría: {r.gate_diria.join(" · ")}
          </p>
        )}
        <p className="mt-1 text-zinc-400">
          {r.video} · {r.cuadros} cuadros a {fmt(r.fps_archivo, 3)} fps del archivo · altura {r.altura_m ? `${fmt(r.altura_m, 2)} m` : "sin declarar (sin cm)"} · procesado en {fmt(trabajo.segundos, 1)} s
        </p>
      </section>

      {overlay ? (
        <section className="flex flex-col gap-2">
          <Reproductor ref={reproductor} src={overlay} fps={r.fps_archivo} cuadros={r.cuadros} eventos={r.eventos_frame} onCuadro={onCuadro} />
          {subImpacto && (
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
              <span style={{ color: COLOR_EVENTO.impact }}>impacto</span>
              <span className="text-zinc-300">
                {textoSubcuadro(subImpacto) ?? `cuadro ${r.eventos_frame.impact}`}
                {subImpacto.t_sub_s !== null && (
                  <span className="text-zinc-500">
                    {" · "}
                    {fmt(subImpacto.t_sub_s, 4)} s{subImpacto.uncertainty_s !== null && ` ± ${fmt(subImpacto.uncertainty_s * 1000, 1)} ms`}
                  </span>
                )}
              </span>
              {parImpacto && (
                <button type="button" className="rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-sm hover:bg-zinc-800" onClick={() => setVerDosCuadros((v) => !v)}>
                  {verDosCuadros ? "ocultar los dos cuadros" : `ver los cuadros ${parImpacto.antes} y ${parImpacto.despues}`}
                </button>
              )}
              <span className="text-xs text-zinc-500" title={subImpacto.signal}>
                estimado: cuándo las manos pasan por su posición de address, no el contacto con la bola
              </span>
            </div>
          )}
          {verDosCuadros && parImpacto && (
            <DosCuadros src={overlay} fps={r.fps_archivo} antes={parImpacto.antes} despues={parImpacto.despues} fraccion={subImpacto?.fraction ?? null} />
          )}
        </section>
      ) : (
        <p className="text-sm text-red-300">No hay overlay.mp4 en este trabajo.</p>
      )}

      {fotos.length > 0 && (
        <section className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
          {fotos.map((ev) => {
            const f = r.eventos_frame[ev];
            return (
              <figure key={ev} className="cursor-pointer rounded-lg border border-zinc-800 bg-black p-1" onClick={() => f !== undefined && irArriba(f)} title="ver ese cuadro en el reproductor">
                {/* eslint-disable-next-line @next/next/no-img-element -- PNG grande servido por el backend, sin optimizar */}
                <img src={archivoUrl(trabajo, `evento-${ev}.png`)!} alt={`cuadro del evento ${EVENTOS[ev]}`} loading="lazy" className="mx-auto max-h-96 object-contain" />
                <figcaption className="mt-1 text-center text-sm" style={{ color: COLOR_EVENTO[ev] }}>
                  {EVENTOS[ev]}
                  {f !== undefined && <span className="text-zinc-400"> · cuadro {f} · {fmt(r.eventos_t_s[ev], 3)} s</span>}
                  {textoSubcuadro(r.eventos_subcuadro?.[ev]) && <span className="block text-xs text-zinc-400">{textoSubcuadro(r.eventos_subcuadro?.[ev])}</span>}
                </figcaption>
              </figure>
            );
          })}
        </section>
      )}

      <section>
        <TablaEventos resumen={r} onIr={irArriba} />
      </section>

      <section>
        <div className="mt-6 mb-2 flex flex-wrap items-baseline gap-x-4 gap-y-1">
          <h2 className="text-base font-semibold">Todos los cuadros</h2>
          <span className="text-sm text-zinc-400">
            descargar:{" "}
            {descargas
              .filter(([n]) => archivoUrl(trabajo, n))
              .map(([n, texto], i) => (
                <span key={n}>
                  {i > 0 && " · "}
                  <a className="text-sky-400 hover:underline" href={archivoUrl(trabajo, n, true)!} download>
                    {texto}
                  </a>
                </span>
              ))}
          </span>
        </div>
        {csv ? <TablaCuadros url={csv} cuadroActual={cuadro} onIr={ir} /> : <p className="text-sm text-red-300">No hay datos-por-cuadro.csv en este trabajo.</p>}
      </section>
    </>
  );
}
