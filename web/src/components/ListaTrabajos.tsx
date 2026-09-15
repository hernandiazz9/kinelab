"use client";

// Los trabajos que ya están en disco: los que se subieron antes (incluso en otra
// sesión del servidor) y los ejemplos que deja otro proceso. Clic en uno y se
// abre como si acabara de terminar, sin volver a subir el video. No se borra
// nada desde acá.
//
// Y **publicar a internet**, uno por uno. Nada se publica al subir, ni por
// defecto, ni en lote: hay que pedirlo para ese trabajo y confirmar un texto que
// dice con todas las letras qué implica. Publicado, la fila lo muestra y ofrece
// copiar el enlace y quitarlo de internet.
//
// El estado de publicación se sondea acá (`GET /api/publicacion`) y no viene de
// las filas: publicar tarda decenas de segundos —exportar, construir el sitio,
// desplegarlo— y la lista se refresca por su cuenta sólo cuando termina un
// análisis. En modo demo no hay backend y no se muestra ninguna de estas
// acciones: ahí no hay a quién pedirle que publique.

import { useCallback, useEffect, useRef, useState } from "react";
import {
  AVISO_PUBLICAR,
  ES_DEMO,
  ETAPA,
  despublicarTrabajo,
  getPublicacion,
  publicarTrabajo,
  type EstadoPublicacion,
  type EventoId,
  type Publicacion,
  type TrabajoFila,
} from "@/lib/api";
import { EVENTOS, PROCEDENCIA, fecha, fmt } from "@/lib/etiquetas";

interface Props {
  filas: TrabajoFila[];
  actual: string | null;
  cargando: boolean;
  error: string | null;
  onElegir: (id: string) => void;
}

const ORDEN_EVENTOS = Object.keys(EVENTOS) as EventoId[];

/** Cada cuánto se vuelve a preguntar mientras hay una publicación corriendo. */
const SONDEO_MS = 700;

/** La segunda línea de cada fila: qué es ese trabajo, en una línea. */
function detalle(f: TrabajoFila): string {
  if (f.estado !== "listo") return f.error ? `error · ${f.error}` : (ETAPA[f.estado] ?? f.estado);
  const partes: string[] = [];
  if (f.cuadros !== null) partes.push(`${f.cuadros} cuadros`);
  // El fps nunca solo: al lado, de dónde sale (ADR-016).
  if (f.fps_archivo !== null) partes.push(`${fmt(f.fps_archivo, 3)} fps${f.fps_provenance ? ` (${PROCEDENCIA[f.fps_provenance] ?? f.fps_provenance})` : ""}`);
  partes.push(f.altura_m !== null ? `${fmt(f.altura_m, 2)} m` : "sin altura");
  const ev = f.eventos_frame;
  if (ev) {
    const nombrados = ORDEN_EVENTOS.filter((k) => ev[k] !== undefined).map((k) => `${EVENTOS[k]} ${ev[k]}`);
    if (nombrados.length > 0) partes.push(nombrados.join(" · "));
  }
  return partes.join(" · ");
}

/** El estado de publicación del backend, sondeado mientras algo corre.
 *  Devuelve `null` hasta la primera respuesta (y siempre, en modo demo). */
function usePublicacion(): { estado: EstadoPublicacion | null; error: string | null; refrescar: () => void } {
  const [estado, setEstado] = useState<EstadoPublicacion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const vivo = useRef(true);

  const refrescar = useCallback(() => {
    if (ES_DEMO) return;
    getPublicacion()
      .then((e) => {
        if (!vivo.current) return;
        setEstado(e);
        setError(null);
      })
      .catch((e: Error) => vivo.current && setError(e.message));
  }, []);

  useEffect(() => {
    vivo.current = true;
    refrescar();
    return () => {
      vivo.current = false;
    };
  }, [refrescar]);

  // Mientras hay algo corriendo se pregunta seguido; cuando no, no se pregunta.
  const corriendo = estado?.corriendo != null;
  useEffect(() => {
    if (!corriendo) return;
    const t = setInterval(refrescar, SONDEO_MS);
    return () => clearInterval(t);
  }, [corriendo, refrescar]);

  return { estado, error, refrescar };
}

export default function ListaTrabajos({ filas, actual, cargando, error, onElegir }: Props) {
  const { estado: pub, error: errorPub, refrescar } = usePublicacion();
  /** Qué fila está mostrando su confirmación, y para qué acción. */
  const [confirmando, setConfirmando] = useState<{ id: string; accion: "publicar" | "quitar" } | null>(null);
  const [copiado, setCopiado] = useState<string | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);

  const pedir = useCallback(
    (id: string, accion: "publicar" | "quitar") => {
      setConfirmando(null);
      setFallo(null);
      const f = accion === "publicar" ? publicarTrabajo : despublicarTrabajo;
      f(id)
        .then(() => refrescar())
        .catch((e: Error) => setFallo(`No se pudo ${accion === "publicar" ? "publicar" : "quitar"} ${id}: ${e.message}`));
    },
    [refrescar],
  );

  const copiar = useCallback((id: string, url: string) => {
    // `navigator.clipboard` no existe fuera de https (o localhost): si no está,
    // se muestra el enlace para copiarlo a mano en vez de no hacer nada.
    navigator.clipboard?.writeText(url).then(
      () => setCopiado(id),
      () => setCopiado(null),
    );
  }, []);

  const corriendo: Publicacion | null = pub?.corriendo ?? null;

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
      {errorPub && <p className="mt-2 text-xs text-zinc-500">No se pudo leer el estado de publicación: {errorPub}</p>}
      {fallo && <p className="mt-2 text-sm text-red-300">{fallo}</p>}
      {pub?.ultima?.estado === "error" && (
        <p className="mt-2 text-sm text-red-300">
          La última publicación falló ({pub.ultima.id}): {pub.ultima.error}
        </p>
      )}

      {filas.length > 0 && (
        <ul className="mt-2 max-h-96 overflow-y-auto">
          {filas.map((f) => {
            const abierto = f.id === actual;
            // El estado de publicación sale del sondeo cuando ya llegó; hasta
            // entonces, de la fila. Los dos salen del mismo registro en disco.
            const p = pub ? (pub.publicados[f.id] ?? null) : f.publicado ? { url: f.publicado_url ?? null, publicado_en: f.publicado_en ?? null, despliegue: null } : null;
            const enCurso = corriendo?.id === f.id ? corriendo : null;
            return (
              <li key={f.id} className={`rounded border-l-2 ${abierto ? "border-sky-500 bg-zinc-800/60" : "border-transparent"}`}>
                <div className="flex items-start gap-2">
                  <button
                    type="button"
                    onClick={() => onElegir(f.id)}
                    aria-current={abierto ? "true" : undefined}
                    className="min-w-0 flex-1 px-2 py-1.5 text-left text-sm hover:bg-zinc-800/60"
                  >
                    <span className="flex flex-wrap items-baseline gap-x-2">
                      {f.origen === "ejemplo" && <span className="rounded bg-emerald-900/60 px-1.5 py-0.5 text-xs text-emerald-200">ejemplo</span>}
                      {p && <span className="rounded bg-sky-900/60 px-1.5 py-0.5 text-xs text-sky-200">publicado</span>}
                      <span className="font-medium">{f.video}</span>
                      <span className="text-xs text-zinc-500">
                        {fecha(f.creado)} · {f.vista}
                        {f.camino && ` · ${f.camino}`}
                        {f.estado !== "listo" && ` · ${f.estado}`}
                      </span>
                    </span>
                    {f.etiqueta && <span className="block text-xs text-emerald-200/80">{f.etiqueta}</span>}
                    <span className={`block text-xs ${f.estado === "error" ? "text-red-300" : "text-zinc-400"}`}>{detalle(f)}</span>
                  </button>

                  {!ES_DEMO && f.estado === "listo" && (
                    <div className="flex shrink-0 flex-wrap items-center justify-end gap-1 py-1.5 pr-1 text-xs">
                      {enCurso ? (
                        <span className="text-sky-300">
                          {enCurso.accion === "publicar" ? "publicando" : "quitando"} · paso {enCurso.paso} de {enCurso.total} · {enCurso.texto}
                        </span>
                      ) : p ? (
                        <>
                          {p.url && (
                            <button type="button" onClick={() => copiar(f.id, p.url!)} className="rounded border border-zinc-700 px-2 py-1 hover:bg-zinc-800">
                              {copiado === f.id ? "copiado" : "copiar enlace"}
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => setConfirmando({ id: f.id, accion: "quitar" })}
                            disabled={corriendo !== null}
                            className="rounded border border-zinc-700 px-2 py-1 text-amber-200 hover:bg-zinc-800 disabled:opacity-40"
                          >
                            quitar de internet
                          </button>
                        </>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setConfirmando({ id: f.id, accion: "publicar" })}
                          disabled={corriendo !== null}
                          className="rounded border border-zinc-700 px-2 py-1 hover:bg-zinc-800 disabled:opacity-40"
                        >
                          publicar
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {p?.url && !enCurso && (
                  <p className="px-2 pb-1.5 text-xs break-all text-zinc-500">
                    <a href={p.url} target="_blank" rel="noreferrer" className="underline decoration-dotted hover:text-zinc-300">
                      {p.url}
                    </a>
                    {p.publicado_en && <span> · desde {fecha(p.publicado_en)}</span>}
                  </p>
                )}

                {confirmando?.id === f.id && (
                  <Confirmar
                    accion={confirmando.accion}
                    video={f.video}
                    onSi={() => pedir(f.id, confirmando.accion)}
                    onNo={() => setConfirmando(null)}
                  />
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

/** La confirmación, con el texto entero a la vista. Publicar saca el video de una
 *  persona de esta Mac: la frase va completa, no abreviada en un `¿seguro?`. */
function Confirmar({ accion, video, onSi, onNo }: { accion: "publicar" | "quitar"; video: string; onSi: () => void; onNo: () => void }) {
  const publicar = accion === "publicar";
  return (
    <div className={`m-2 rounded border p-3 text-sm ${publicar ? "border-amber-700 bg-amber-950/40 text-amber-100" : "border-zinc-700 bg-zinc-900 text-zinc-200"}`}>
      <p className="font-medium">
        {publicar ? `Publicar «${video}» a internet` : `Quitar «${video}» de internet`}
      </p>
      <p className="mt-1">
        {publicar
          ? AVISO_PUBLICAR
          : "Se borran de internet el video, la pose y los datos de este trabajo, y el enlace deja de funcionar. El trabajo sigue en esta Mac: no se borra nada de data/exploracion/."}
      </p>
      <p className="mt-1 text-xs opacity-80">
        Tarda alrededor de un minuto: se exporta el trabajo, se construye el sitio entero y se despliega. Va uno por vez.
      </p>
      <div className="mt-2 flex gap-2">
        <button type="button" onClick={onSi} className={`rounded px-3 py-1 text-sm ${publicar ? "bg-amber-700 hover:bg-amber-600" : "bg-zinc-700 hover:bg-zinc-600"}`}>
          {publicar ? "Sí, publicar a internet" : "Sí, quitar de internet"}
        </button>
        <button type="button" onClick={onNo} className="rounded border border-zinc-600 px-3 py-1 text-sm hover:bg-zinc-800">
          Cancelar
        </button>
      </div>
    </div>
  );
}
