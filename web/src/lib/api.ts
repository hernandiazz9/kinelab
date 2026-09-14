// Cliente de la API local (service/app.py). Todo va por /api/*, que next.config.ts reenvía al 8765.

export type Estado = "en_cola" | "cargando_modelo" | "detectando_pose" | "calculando" | "dibujando" | "listo" | "error";
export type Origen = "subida" | "ejemplo";
export type EventoId = "address" | "top" | "impact" | "follow_end";
export type Eventos = Partial<Record<EventoId, number>>;
export type Fila = Record<string, number | null>;

/** El instante estimado ENTRE dos cuadros, como lo escribe `sports.golf.events`.
 *  El cuadro entero (`eventos_frame`) no cambia: esto lo acompaña. Con `fraction`
 *  en null, `null_reason` dice por qué: nunca un número forzado. */
export interface Subcuadro {
  frame_before: number | null;
  frame_after: number | null;
  fraction: number | null;
  t_sub_s: number | null;
  uncertainty_frames: number | null;
  uncertainty_s: number | null;
  components: { curvature_frames: number | null; noise_frames: number | null; noise_px: number | null; slope_px_per_frame: number | null };
  method: string;
  signal: string;
  views: string[];
  provenance: string;
  null_reason: string | null;
}

/** El contenido de `datos-eventos.json` tal como lo escribe `kinelab.explore`. */
export interface Resumen {
  aviso: string;
  video: string;
  fps_archivo: number;
  cuadros: number;
  altura_m: number | null;
  gate_diria: string[];
  eventos_frame: Eventos;
  eventos_t_s: Eventos;
  eventos_subcuadro?: Partial<Record<EventoId, Subcuadro>>;
  duraciones: Record<string, number>;
  picos: Record<string, number | null>;
  en_cada_evento: Partial<Record<EventoId, Fila>>;
  diferencias_vs_address: Record<string, Fila>;
  calidad: unknown;
  columnas: string[];
}

export interface Trabajo {
  id: string;
  estado: Estado;
  /** `subida` (alguien la subió acá) o `ejemplo` (lo dejó otro proceso en disco). */
  origen: Origen;
  /** El rótulo de un ejemplo, tal como lo escribió quien lo armó. Acá no se inventa ninguno. */
  etiqueta: string | null;
  progreso: { cuadros: number; total: number | null };
  error: string | null;
  video: string;
  altura_m: number | null;
  vista: string;
  creado: string;
  terminado: string | null;
  segundos: number | null;
  archivos: Record<string, string>;
  resumen: Resumen | null;
}

/** Una línea de `GET /api/datos`: lo justo para elegir un trabajo de la lista. */
export interface TrabajoFila {
  id: string;
  estado: Estado;
  origen: Origen;
  etiqueta: string | null;
  video: string;
  altura_m: number | null;
  vista: string;
  creado: string;
  terminado: string | null;
  segundos: number | null;
  error: string | null;
  fps_archivo: number | null;
  cuadros: number | null;
  eventos_frame: Eventos | null;
}

export const ETAPA: Record<Estado, string> = {
  en_cola: "en cola",
  cargando_modelo: "cargando el modelo (sólo la primera vez tarda unos segundos)",
  detectando_pose: "detectando la pose",
  calculando: "calculando",
  dibujando: "dibujando el video con los palitos",
  listo: "listo",
  error: "error",
};

const CLAVE_ULTIMO = "kinelab:ultimo-trabajo";

async function leerError(r: Response): Promise<string> {
  try {
    const j = await r.json();
    if (j && typeof j.detail === "string") return j.detail;
    if (j && Array.isArray(j.detail)) return j.detail.map((d: { msg?: string }) => d.msg ?? JSON.stringify(d)).join(" · ");
    return JSON.stringify(j);
  } catch {
    return `${r.status} ${r.statusText}`;
  }
}

/** PUT /api/datos con el archivo como cuerpo crudo. XHR porque fetch no informa el progreso de subida. */
export function subirVideo(archivo: File, alturaM: number | null, onProgreso: (fraccion: number) => void): Promise<Trabajo> {
  const q = new URLSearchParams({ filename: archivo.name });
  if (alturaM !== null) q.set("altura_m", String(alturaM));
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", `/api/datos?${q.toString()}`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgreso(e.loaded / e.total);
    };
    xhr.onerror = () => reject(new Error("No se pudo hablar con el backend. ¿Está corriendo `.venv/bin/python -m service`?"));
    xhr.onload = () => {
      if (xhr.status === 202) {
        const t = JSON.parse(xhr.responseText) as Trabajo;
        recordarTrabajo(t.id);
        resolve(t);
        return;
      }
      let detalle = xhr.responseText;
      try {
        const j = JSON.parse(xhr.responseText);
        detalle = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? j);
      } catch {
        /* texto plano */
      }
      reject(new Error(`El backend respondió ${xhr.status}: ${detalle}`));
    };
    xhr.send(archivo);
  });
}

export async function getTrabajo(id: string): Promise<Trabajo> {
  const r = await fetch(`/api/datos/${encodeURIComponent(id)}`, { cache: "no-store" });
  if (!r.ok) throw new Error(await leerError(r));
  return (await r.json()) as Trabajo;
}

/** Los trabajos que hay en disco, del más nuevo al más viejo. Incluye los ejemplos. */
export async function listarTrabajos(): Promise<TrabajoFila[]> {
  const r = await fetch("/api/datos", { cache: "no-store" });
  if (!r.ok) throw new Error(await leerError(r));
  return (await r.json()) as TrabajoFila[];
}

export function recordarTrabajo(id: string): void {
  try {
    localStorage.setItem(CLAVE_ULTIMO, id);
  } catch {
    /* sin localStorage sólo se pierde el resultado al recargar */
  }
}

export function ultimoTrabajoId(): string | null {
  try {
    return localStorage.getItem(CLAVE_ULTIMO);
  } catch {
    return null;
  }
}

export function olvidarUltimoTrabajo(): void {
  try {
    localStorage.removeItem(CLAVE_ULTIMO);
  } catch {
    /* nada */
  }
}

/** URL de un archivo del trabajo; `descargar` pide Content-Disposition: attachment. */
export function archivoUrl(t: Trabajo, nombre: string, descargar = false): string | null {
  const u = t.archivos[nombre];
  if (!u) return null;
  return descargar ? `${u}?descargar=true` : u;
}

export async function bajarTexto(url: string): Promise<string> {
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(await leerError(r));
  return r.text();
}

// --- `?trabajo=<id>` en la barra de direcciones: un enlace local a un trabajo ------

export const PARAM_TRABAJO = "trabajo";

export function trabajoDeLaUrl(): string | null {
  if (typeof window === "undefined") return null;
  return new URLSearchParams(window.location.search).get(PARAM_TRABAJO);
}

/** Pone (o saca) `?trabajo=<id>` sin recargar la página, para poder compartir el enlace. */
export function ponerTrabajoEnLaUrl(id: string | null): void {
  if (typeof window === "undefined") return;
  const u = new URL(window.location.href);
  if (id) u.searchParams.set(PARAM_TRABAJO, id);
  else u.searchParams.delete(PARAM_TRABAJO);
  window.history.replaceState(null, "", u.toString());
}
