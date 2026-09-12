// Cliente de la API local (service/app.py). Todo va por /api/*, que next.config.ts reenvía al 8765.

export type Estado = "en_cola" | "cargando_modelo" | "detectando_pose" | "calculando" | "dibujando" | "listo" | "error";
export type EventoId = "address" | "top" | "impact" | "follow_end";
export type Eventos = Partial<Record<EventoId, number>>;
export type Fila = Record<string, number | null>;

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
        try {
          localStorage.setItem(CLAVE_ULTIMO, t.id);
        } catch {
          /* sin localStorage sólo se pierde el resultado al recargar */
        }
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
