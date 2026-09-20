"use client";

// Una sola pantalla: subir un video → el overlay con los palitos en un
// reproductor con cámara lenta, cuadro a cuadro y zoom; las fotos por evento;
// y toda la data que el motor produce, en tablas. Sin login, sin sesiones, sin
// gate, sin puntaje.
//
// El orden de arriba hacia abajo no es estético: primero los avisos (bajo qué
// supuesto se midió el tiempo, ADR-016), después la ficha del archivo, y recién
// ahí los números derivados. La ficha aparece apenas el motor la escribió, con
// la pose todavía corriendo.
//
// En MODO DEMO (`NEXT_PUBLIC_KINELAB_MODO=demo`) no hay backend y no se puede subir
// nada: el formulario se reemplaza por la frase que dice por qué (el motor corre en
// la Mac del entrenador y no se despliega). Todo lo demás es idéntico, porque la
// lectura se decide en un solo lugar de `lib/api.ts`. Lo único que el modo demo
// agrega acá es `transformacion.json`: el video servido es un recorte al tramo del
// gesto, así que el reproductor necesita saber qué cuadro del origen es su t=0.

import { useCallback, useEffect, useRef, useState } from "react";
import Avisos from "@/components/Avisos";
import DosCuadros from "@/components/DosCuadros";
import FichaArchivo from "@/components/FichaArchivo";
import ListaTrabajos from "@/components/ListaTrabajos";
import Metricas from "@/components/Metricas";
import Reproductor, { COLOR_EVENTO, type ReproductorHandle } from "@/components/Reproductor";
import SelectorRepeticion from "@/components/SelectorRepeticion";
import Subida from "@/components/Subida";
import TablaCuadros from "@/components/TablaCuadros";
import TablaEventos from "@/components/TablaEventos";
import Visor3D from "@/components/Visor3D";
import {
  AVISO_DEMO,
  CAMINO_DESCONOCIDO,
  ES_DEMO,
  ETAPA,
  archivoUrl,
  bajarAnalysis,
  getTransformacion,
  getTrabajo,
  listarTrabajos,
  olvidarUltimoTrabajo,
  ponerTrabajoEnLaUrl,
  recordarCamino,
  recordarTrabajo,
  subirVideo,
  trabajoDeLaUrl,
  ultimoTrabajoId,
  type Analysis,
  type EventoId,
  type Trabajo,
  type TrabajoFila,
  type Transformacion,
} from "@/lib/api";
import { EVENTOS, PROCEDENCIA, fmt, textoSubcuadro } from "@/lib/etiquetas";
import { elegir, fraseRepeticion, nombresDeFoto, repDelAnalysis, repeticionesDe } from "@/lib/repeticiones";

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
  // Cuál de las repeticiones del clip se está mirando. Vive acá y no en
  // `Resultado` porque se resetea al abrir otro trabajo, igual que `cuadro`: el
  // índice 1 de un clip de dos swings no quiere decir nada en el siguiente.
  const [repElegida, setRepElegida] = useState(0);
  const [filas, setFilas] = useState<TrabajoFila[]>([]);
  const [lista, setLista] = useState<{ cargando: boolean; error: string | null }>({ cargando: true, error: null });
  const [nota, setNota] = useState<string | null>(null);
  const [camino, setCamino] = useState(CAMINO_DESCONOCIDO);
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
          setRepElegida(0);
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

  // El camino de captura arranca en el genérico y lo confirma `Subida` cuando
  // llegó la lista de `GET /api/config`: sólo ahí se sabe si el que quedó
  // recordado sigue existiendo y se puede usar.
  const elegirCamino = useCallback((id: string) => {
    setCamino(id);
    recordarCamino(id);
  }, []);

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

  const subir = useCallback(
    async (archivo: File, alturaM: number | null) => {
      setFase({ tipo: "subiendo", pct: 0, nombre: archivo.name });
      try {
        const t = await subirVideo(archivo, alturaM, camino, (p) => setFase({ tipo: "subiendo", pct: p, nombre: archivo.name }));
        setCuadro(0);
        setRepElegida(0);
        setFase({ tipo: "procesando", trabajo: t });
        ponerTrabajoEnLaUrl(t.id);
      } catch (e) {
        setFase({ tipo: "error", mensaje: (e as Error).message });
      }
    },
    [camino],
  );

  const ir = useCallback((n: number) => reproductor.current?.irACuadro(n), []);
  const irArriba = useCallback(
    (n: number) => {
      ir(n);
      window.scrollTo({ top: 0, behavior: "smooth" });
    },
    [ir],
  );

  const ocupado = fase.tipo === "subiendo" || fase.tipo === "procesando";
  const trabajo = fase.tipo === "listo" || fase.tipo === "procesando" ? fase.trabajo : null;
  const abiertoId = trabajo?.id ?? null;

  // `analysis.json` se baja ACÁ y no en `Metricas`, que va abajo de todo: los
  // avisos de arriba son `analysis.warnings` y se leen antes que cualquier
  // número. Una sola lectura para los dos. Se guarda con su URL al lado para que
  // la respuesta de un trabajo anterior nunca se aplique al que se está viendo.
  const urlAnalysis = trabajo ? archivoUrl(trabajo, "analysis.json") : null;
  const [leidoAnalysis, setLeidoAnalysis] = useState<{ url: string; valor: Analysis | null; error: string | null } | null>(null);
  useEffect(() => {
    if (!urlAnalysis) return;
    let vivo = true;
    bajarAnalysis(urlAnalysis)
      .then((a) => vivo && setLeidoAnalysis({ url: urlAnalysis, valor: a, error: null }))
      .catch((e: Error) => vivo && setLeidoAnalysis({ url: urlAnalysis, valor: null, error: e.message }));
    return () => {
      vivo = false;
    };
  }, [urlAnalysis]);
  const analysis = leidoAnalysis?.url === urlAnalysis ? leidoAnalysis.valor : null;
  const errorAnalysis = leidoAnalysis?.url === urlAnalysis ? leidoAnalysis.error : null;

  return (
    <main className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-6">
      <header className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <h1 className="text-xl font-semibold">kinelab · exploración</h1>
        <p className="text-sm text-zinc-400">
          {ES_DEMO ? "Resultados ya calculados" : "Subí un video de un swing"}: los palitos y toda la data que el motor produce. Sin gate, sin puntaje: números para mirar, no para juzgar.
        </p>
      </header>

      {ES_DEMO ? (
        <section className="rounded-lg border border-amber-800 bg-amber-950/30 p-4 text-sm text-amber-200">{AVISO_DEMO}</section>
      ) : (
        <section className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
          <Subida ocupado={ocupado} camino={camino} onCamino={elegirCamino} onSubir={subir} />
        </section>
      )}

      <ListaTrabajos filas={filas} actual={abiertoId} cargando={lista.cargando} error={lista.error} onElegir={abrir} />

      {nota && <p className="text-sm text-amber-300">{nota}</p>}

      {/* Los avisos, antes de cualquier número derivado (ADR-016). */}
      {fase.tipo === "listo" && <Avisos resumen={fase.trabajo.resumen!} archivo={fase.trabajo.archivo} analysis={analysis} />}

      {/* Y la ficha del archivo, que está desde antes de la pose. */}
      {trabajo?.archivo && <FichaArchivo ficha={trabajo.archivo} procesando={fase.tipo === "procesando"} />}

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

      {fase.tipo === "listo" && (
        <Resultado
          trabajo={fase.trabajo}
          cuadro={cuadro}
          onCuadro={setCuadro}
          ir={ir}
          irArriba={irArriba}
          reproductor={reproductor}
          analysis={analysis}
          errorAnalysis={errorAnalysis}
          repElegida={repElegida}
          onRepElegida={setRepElegida}
        />
      )}
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
  analysis,
  errorAnalysis,
  repElegida,
  onRepElegida,
}: {
  trabajo: Trabajo;
  cuadro: number;
  onCuadro: (n: number) => void;
  ir: (n: number) => void;
  irArriba: (n: number) => void;
  reproductor: React.RefObject<ReproductorHandle | null>;
  analysis: Analysis | null;
  errorAnalysis: string | null;
  repElegida: number;
  onRepElegida: (i: number) => void;
}) {
  const r = trabajo.resumen!;
  const [verDosCuadros, setVerDosCuadros] = useState(false);
  // Las repeticiones de este trabajo, en UN solo lugar (`lib/repeticiones.ts`):
  // `repeticiones_detalle` cuando está, y si no el primer nivel como repetición
  // única, que es lo que hace visible a un trabajo anterior al encargo 35.
  const reps = repeticionesDe(r, analysis);
  const rep = elegir(reps, repElegida);
  const repAnalysis = repDelAnalysis(analysis, rep);
  const frase = fraseRepeticion(rep, reps.total);
  // Al cambiar de repetición: el reproductor salta al primer evento de la nueva
  // y los dos cuadros del impacto se cierran. Sin esto la pantalla mentiría — el
  // `cuadro` del reproductor se inicializa al montar y se quedaría en el impacto
  // de la repetición anterior mientras todo lo demás habla de la nueva, y los dos
  // cuadros abiertos serían los del impacto viejo.
  const elegirRep = (i: number) => {
    onRepElegida(i);
    setVerDosCuadros(false);
    const destino = reps.lista[i]?.eventos_frame.address ?? reps.lista[i]?.frame_start ?? null;
    if (destino !== null && destino !== undefined) ir(destino);
  };
  // `transformacion.json` sólo existe en un trabajo exportado a la demo: ahí el
  // video es un recorte al tramo del gesto y hay que decirle al reproductor qué
  // cuadro del ORIGEN es su segundo 0. En local no hay archivo y todo queda en 0,
  // que es exactamente lo que valía antes de que la demo existiera. Se guarda con
  // el id al lado para no tener que borrarlo dentro del efecto (cascada de renders)
  // y para que la respuesta de un trabajo anterior nunca se aplique al que se ve.
  const [leido, setLeido] = useState<{ id: string; valor: Transformacion | null } | null>(null);
  const overlay = archivoUrl(trabajo, "overlay.mp4");

  useEffect(() => {
    let vivo = true;
    getTransformacion(trabajo)
      .then((x) => vivo && setLeido({ id: trabajo.id, valor: x }))
      .catch(() => vivo && setLeido({ id: trabajo.id, valor: null }));
    return () => {
      vivo = false;
    };
  }, [trabajo]);
  const tr = leido?.id === trabajo.id ? leido.valor : null;
  const primerCuadro = tr?.cuadro_offset ?? 0;
  const cuadrosVideo = tr?.cuadros ?? r.cuadros;
  const subImpacto = rep?.eventos_subcuadro?.impact;
  // Los dos cuadros entre los que cayó el instante estimado, si los hay.
  const parImpacto = subImpacto && subImpacto.frame_before !== null && subImpacto.frame_after !== null ? { antes: subImpacto.frame_before, despues: subImpacto.frame_after } : null;
  const csv = archivoUrl(trabajo, "datos-por-cuadro.csv");
  // La foto de ese evento EN LA REPETICIÓN ELEGIDA. La 1 conserva
  // `evento-<id>` y las demás son `evento-r<N>-<id>` (`kinelab.explore.foto_de_evento`),
  // y cada una puede estar en PNG (local) o en JPEG (la demo: un PNG del overlay
  // de vid1 pesa 18 MB). Los nombres los arma `lib/repeticiones.ts`.
  const foto = (ev: EventoId) => {
    for (const n of nombresDeFoto(rep?.rep ?? 1, ev)) {
      const u = archivoUrl(trabajo, n);
      if (u) return u;
    }
    return null;
  };
  const fotos = (Object.keys(EVENTOS) as EventoId[]).filter((ev) => foto(ev));
  const descargas: [string, string][] = [
    ["video.mp4", "video sin palitos"],
    ["pose.json", "pose por cuadro (JSON)"],
    ["transformacion.json", "transformacion.json"],
    ["datos-por-cuadro.csv", "CSV por cuadro"],
    ["datos-eventos.json", "JSON por evento"],
    ["analysis.json", "analysis.json"],
    ["capture.json", "capture.json"],
    ["overlay.mp4", "video con palitos"],
  ];

  return (
    <>
      {/* El aviso y la ficha ya se mostraron arriba; acá queda la identidad del
          trabajo. El fps va con su procedencia al lado, siempre (ADR-016). */}
      <section className="rounded-lg border border-zinc-800 p-3 text-sm">
        {/* El rótulo de un ejemplo lo trae `trabajo.json`: acá no se inventa ninguno. */}
        {trabajo.origen === "ejemplo" && <p className="mb-1 font-medium text-emerald-300">{trabajo.etiqueta ?? "ejemplo"}</p>}
        <p className="text-zinc-400">
          {r.video} · {r.cuadros} cuadros a {fmt(r.fps_archivo, 3)} fps
          {r.fps_provenance && <span className="text-amber-300"> ({PROCEDENCIA[r.fps_provenance] ?? r.fps_provenance})</span>}
          {r.camino && ` · camino ${r.camino}`} · altura {r.altura_m ? `${fmt(r.altura_m, 2)} m` : "sin declarar (sin cm)"} · procesado en {fmt(trabajo.segundos, 1)} s
        </p>
      </section>

      {overlay ? (
        <section className="flex flex-col gap-2">
          <Reproductor ref={reproductor} src={overlay} fps={r.fps_archivo} cuadros={cuadrosVideo} primerCuadro={primerCuadro} eventos={rep?.eventos_frame ?? {}} onCuadro={onCuadro} />
          {tr && (
            <p className="text-xs text-zinc-500">
              Video recortado al sujeto y al tramo del gesto para poder desplegarlo: cuadros {tr.tramo_origen[0]}–{tr.tramo_origen[1]} de {tr.cuadros_origen ?? "?"}, recorte {tr.recorte.ancho}×{tr.recorte.alto} px en ({tr.offset_x},{tr.offset_y}) del cuadro de {tr.tamano_origen[0]}×{tr.tamano_origen[1]}, escala {fmt(tr.escala, 4)}. Los números de cuadro de abajo son los del video original, sin renumerar.
            </p>
          )}
          {subImpacto && (
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
              <span style={{ color: COLOR_EVENTO.impact }}>impacto</span>
              <span className="text-zinc-300">
                {textoSubcuadro(subImpacto) ?? `cuadro ${rep?.eventos_frame.impact}`}
                {subImpacto.t_sub_s !== null && (
                  <span className="text-zinc-500">
                    {" · "}
                    {fmt(subImpacto.t_sub_s, 4)} s{subImpacto.uncertainty_s !== null && ` · precisión interna del cruce ± ${fmt(subImpacto.uncertainty_s * 1000, 1)} ms`}
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
          {subImpacto && (
            // Qué es y qué no es ese ±. Sin números: el único sesgo contra la
            // pelota que existe salió de un informe sobre un clip, no del motor,
            // y ponerlo acá lo convertiría en una medición que no es.
            <p className="text-xs text-zinc-500">
              La <span className="text-zinc-400">precisión interna del cruce</span> es cuánto se corre ese instante estimado por el ruido de la señal y por la curvatura entre los dos cuadros: es la precisión del cruce
              consigo mismo. No incluye el sesgo contra el contacto con la pelota, que no está medido.
            </p>
          )}
          {verDosCuadros && parImpacto && (
            <DosCuadros src={overlay} fps={r.fps_archivo} antes={parImpacto.antes} despues={parImpacto.despues} fraccion={subImpacto?.fraction ?? null} primerCuadro={primerCuadro} />
          )}
        </section>
      ) : (
        <p className="text-sm text-red-300">No hay overlay.mp4 en este trabajo.</p>
      )}

      {fotos.length > 0 && (
        <section className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
          {fotos.map((ev) => {
            const f = rep?.eventos_frame[ev];
            return (
              <figure key={ev} className="cursor-pointer rounded-lg border border-zinc-800 bg-black p-1" onClick={() => f !== undefined && irArriba(f)} title="ver ese cuadro en el reproductor">
                {/* eslint-disable-next-line @next/next/no-img-element -- PNG grande servido por el backend, sin optimizar */}
                <img src={foto(ev)!} alt={`cuadro del evento ${EVENTOS[ev]}`} loading="lazy" className="mx-auto max-h-96 object-contain" />
                <figcaption className="mt-1 text-center text-sm" style={{ color: COLOR_EVENTO[ev] }}>
                  {EVENTOS[ev]}
                  {f !== undefined && <span className="text-zinc-400"> · cuadro {f} · {fmt(rep?.eventos_t_s[ev], 3)} s</span>}
                  {textoSubcuadro(rep?.eventos_subcuadro?.[ev]) && <span className="block text-xs text-zinc-400">{textoSubcuadro(rep?.eventos_subcuadro?.[ev])}</span>}
                </figcaption>
              </figure>
            );
          })}
        </section>
      )}

      {/* El swing en 3-D: sólo si el trabajo lo tiene, o sea sólo si su
          movimiento está medido en 3-D. De un video no sale (ADR-010). */}
      {archivoUrl(trabajo, "pose3d.json") && (
        <section>
          <Visor3D key={archivoUrl(trabajo, "pose3d.json")!} url={archivoUrl(trabajo, "pose3d.json")!} />
        </section>
      )}

      {/* El selector, antes que cualquier número: de qué swing habla todo lo de
          abajo. Con una sola repetición —y con un trabajo viejo, que entra como
          repetición única— no se muestra. */}
      <SelectorRepeticion reps={reps.lista} elegida={repElegida} onElegir={elegirRep} />

      {/* Qué se pudo medir con ESTE archivo, métrica por métrica y con la razón
          cuando no se pudo. Antes de las tablas de exploración, que son la lupa. */}
      {archivoUrl(trabajo, "analysis.json") && (
        <section>
          {/* El JSON lo bajó `Pagina`, que lo necesita también para los avisos. */}
          <Metricas analysis={analysis} rep={repAnalysis} frase={frase} error={errorAnalysis} />
        </section>
      )}

      <section>
        <TablaEventos rep={rep} frase={reps.respaldo ? null : frase} columnas={r.columnas} calidad={r.calidad} onIr={irArriba} />
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
        {/* `r` lleva la escala con la que se dividieron los cm y el cuadro contra el
            que se miden los «vs address»: la tabla los dice arriba (encargo 33). */}
        {csv ? <TablaCuadros url={csv} cuadroActual={cuadro} onIr={ir} rep={rep} frase={reps.respaldo ? null : frase} /> : <p className="text-sm text-red-300">No hay datos-por-cuadro.csv en este trabajo.</p>}
      </section>
    </>
  );
}
