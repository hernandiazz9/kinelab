// Cliente de la API local (service/app.py). Todo va por /api/*, que next.config.ts reenvía al 8765.
//
// Y el MODO DEMO, que es el mismo tipo de datos sin backend: `NEXT_PUBLIC_KINELAB_MODO=demo`
// lee de `/demo/index.json` y `/demo/<id>/trabajo.json`, archivos estáticos que escribe
// `python -m kinelab.tools.exportar_demo`. El motor no se despliega (onnxruntime con CoreML,
// pesos de cientos de MB, 76 s por clip): lo que se despliega es un visor de resultados YA
// calculados en la Mac del entrenador.
//
// La decisión de por dónde leer está en ESTE archivo y en ningún otro: los componentes
// llaman a las mismas funciones en los dos modos. Lo único que cambia afuera es que en demo
// no se muestra el formulario de subir (page.tsx) — porque no hay a quién subirle nada.

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

/** De dónde sale el fps con el que se midió el tiempo (CONTEXTO.md §procedencia).
 *  `sin_verificar` = camino declarado, sin cronómetro: ADR-016. */
export type Procedencia = "medido_aqui" | "sin_verificar";

/** De dónde sale el divisor de cada cm (`CONTRATO.md` §La escala). Son dos porque
 *  son los dos caminos de `px_to_cm`: la cadena de la estatura de la repetición,
 *  o la caída a `body_height_px` del cuadro cuando la cadena no se pudo medir. */
export type EscalaFuente = "stature_chain_rep" | "body_height_px_frame";

/** Un camino de captura de `capture-paths.yaml`, tal como lo da `GET /api/config`. */
export interface CaminoCaptura {
  id: string;
  device: string;
  mode: "video" | "slomo";
  transfer: string;
  calibrated: boolean;
  nominal_fps: number | null;
  codec_expected: string | null;
  notes: string;
}

export interface Config {
  sport: { id: string; gestures: string[]; views: string[]; fps_min: number };
  capture_paths: CaminoCaptura[];
  data_dir: string;
}

/** La ficha del archivo tal como llegó, del `capture.json`. Está antes que la
 *  pose: `prepare_take` la escribe antes de correr el modelo. Los pares
 *  efectivo/bruto viajan juntos y `fps_note` dice por qué difieren. */
export interface FichaArchivo {
  codec: string;
  ancho: number;
  alto: number;
  rotacion_deg: number;
  cuadros: number;
  duracion_s: number;
  duracion_reproduccion_s: number;
  fps_real: number | null;
  fps_reproduccion: number;
  fps_reproduccion_bruto: number | null;
  stretch_factor: number | null;
  vfr_ratio: number;
  vfr_ratio_bruto: number | null;
  tasa_variable: boolean;
  vfr_ratio_max: number;
  primer_delta_s: number | null;
  fps_note: string | null;
  camino: string;
  camino_calibrado: boolean | null;
  fps_provenance: Procedencia;
  /** El clip con el que se calibró el camino. `null` = el camino no lo declara. */
  calibracion_clip_sha256?: string | null;
  /** ¿Ese clip es este archivo? `null` = no se puede saber (el camino no declara sha). */
  calibracion_mismo_archivo?: boolean | null;
  original: string;
  grabado: string | null;
}

/** Una entrada de `repeticiones_detalle`: TODO lo que hasta el encargo 35 existía
 *  sólo para la primera repetición, ahora por repetición. Las claves son las
 *  mismas que las de primer nivel a propósito — es el mismo dato, una repetición
 *  más abajo — y cada una se mide contra SU address, no contra el de la 1. */
export interface RepeticionDetalle {
  rep: number;
  frame_start: number;
  frame_end: number;
  eventos_frame: Eventos;
  eventos_t_s: Eventos;
  eventos_tol_frames?: Partial<Record<EventoId, number>>;
  eventos_subcuadro?: Partial<Record<EventoId, Subcuadro>>;
  escala_px: number | null;
  escala_fuente: EscalaFuente | null;
  /** El cuadro del que salió esa escala (contrato 2.2.0, `reps[].scale_frame`).
   *  `null` con el fallback de escala: ahí no hay ningún máximo que mirar. */
  escala_cuadro: number | null;
  referencia_cuadro: number | null;
  referencia_fuente: string | null;
  duraciones: Record<string, number>;
  /** El pico DENTRO de esta repetición, no el del clip entero. */
  picos: Record<string, number | null>;
  en_cada_evento: Partial<Record<EventoId, Fila>>;
  diferencias_vs_address: Record<string, Fila>;
}

/** El contenido de `datos-eventos.json` tal como lo escribe `kinelab.explore`. */
export interface Resumen {
  aviso: string;
  video: string;
  fps_archivo: number;
  cuadros: number;
  altura_m: number | null;
  gate_diria: string[];
  /** Los cuatro de ADR-016. Faltan en un trabajo anterior al encargo 06. */
  camino?: string;
  camino_calibrado?: boolean | null;
  fps_provenance?: Procedencia;
  fps_aviso?: string | null;
  eventos_frame: Eventos;
  eventos_t_s: Eventos;
  /** Tolerancia de cada evento en cuadros (CONTRATO.md §events[]): de ahí sale la
   *  banda de toda métrica anclada a él, y no siempre es 1. Falta en un trabajo
   *  anterior al encargo 31. */
  eventos_tol_frames?: Partial<Record<EventoId, number>>;
  eventos_subcuadro?: Partial<Record<EventoId, Subcuadro>>;
  /** El divisor en píxeles de las columnas en cm de la repetición que se muestra,
   *  y de dónde sale (CONTRATO.md §La escala). Faltan en un trabajo anterior al
   *  encargo 33: ahí no se muestra nada, no se inventa una escala. */
  escala_px?: number | null;
  escala_fuente?: EscalaFuente | null;
  /** El cuadro donde la cadena de la estatura llegó a su máximo; `null` con más de
   *  una repetición, porque entonces el cuadro publicado es el de una sola. */
  escala_cuadro?: number | null;
  /** Contra qué cuadro se miden las ocho columnas `*_vs_address_*`. Sin address el
   *  motor cae al cuadro 0 — el valor no cambia, pero deja de ser mudo. */
  referencia_cuadro?: number | null;
  referencia_fuente?: string | null;
  /** Los campos de arriba —eventos, escala, referencia, duraciones, picos y las
   *  dos tablas— son los de la repetición `repeticion_mostrada`, o sea la 1, y son
   *  **transitorios**: están duplicados en `repeticiones_detalle[0]` y los retira
   *  el encargo que regenera todo (R10). Hasta entonces son lo único que hace
   *  visible a un trabajo anterior al 35, que no trae el detalle. */
  repeticion_mostrada?: number | null;
  repeticiones?: number;
  /** Una entrada por repetición (encargo 35). Falta en un trabajo anterior: ahí
   *  el primer nivel se lee como repetición única (`lib/repeticiones.ts`). */
  repeticiones_detalle?: RepeticionDetalle[];
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
  /** El camino de captura con el que se subió (ADR-016); null en un trabajo viejo. */
  camino: string | null;
  /** La ficha del archivo. Llega ANTES que la pose: se muestra mientras el modelo corre. */
  archivo: FichaArchivo | null;
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
  camino: string | null;
  /** Va al lado del fps: un fps sin procedencia no se puede leer (ADR-016). */
  fps_provenance: Procedencia | null;
  fps_archivo: number | null;
  cuadros: number | null;
  eventos_frame: Eventos | null;
  /** Si ese trabajo está publicado a internet, y desde cuándo. Opcionales porque
   *  el `index.json` de la demo no los trae: ahí no hay backend que publique nada. */
  publicado?: boolean;
  publicado_url?: string | null;
  publicado_en?: string | null;
}

// --- publicar a internet (sólo en modo local: en demo no hay a quién pedírselo) -----

/** En qué va una publicación (o una baja), tal como la devuelve el backend.
 *  Exportar, construir el sitio y desplegarlo tardan decenas de segundos: la
 *  petición vuelve enseguida con esto y la pantalla lo sondea. */
export interface Publicacion {
  id: string;
  accion: "publicar" | "quitar";
  estado: "corriendo" | "listo" | "error";
  paso: number;
  total: number;
  texto: string;
  error: string | null;
  url: string | null;
  empezado: string;
  terminado: string | null;
}

/** `GET /api/publicacion`: qué está publicado y qué está corriendo, de una. */
export interface EstadoPublicacion {
  sitio: string;
  publicados: Record<string, { url: string | null; publicado_en: string | null; despliegue: string | null }>;
  corriendo: Publicacion | null;
  ultima: Publicacion | null;
}

/** Lo que hay que leer antes de publicar. No es un tecnicismo: el video es de una
 *  persona y esto lo saca de la Mac del entrenador. */
export const AVISO_PUBLICAR =
  "Publicar sube ESTE trabajo a internet: el video del swing, la pose cuadro a cuadro, las fotos y todos los" +
  " datos quedan accesibles para cualquiera que tenga el enlace. No hay contraseña; lo único que hay es que el" +
  " enlace no está indexado por buscadores. Se puede quitar después, y entonces deja de estar accesible.";

export async function getPublicacion(): Promise<EstadoPublicacion> {
  if (ES_DEMO) throw new Error(AVISO_DEMO);
  return leerJson<EstadoPublicacion>("/api/publicacion");
}

/** Arranca la publicación de un trabajo. Vuelve enseguida: el trabajo de verdad
 *  (exportar → construir → desplegar) corre en un hilo del backend. */
export async function publicarTrabajo(id: string): Promise<Publicacion> {
  return pedir<Publicacion>("POST", `/api/datos/${encodeURIComponent(id)}/publicar`);
}

/** Lo saca de internet. El trabajo sigue en disco: lo que se va es lo publicado. */
export async function despublicarTrabajo(id: string): Promise<Publicacion> {
  return pedir<Publicacion>("DELETE", `/api/datos/${encodeURIComponent(id)}/publicar`);
}

async function pedir<T>(metodo: string, url: string): Promise<T> {
  if (ES_DEMO) throw new Error(AVISO_DEMO);
  const r = await fetch(url, { method: metodo, cache: "no-store" });
  if (!r.ok) throw new Error(await leerError(r));
  return (await r.json()) as T;
}

/** Una métrica del registro en `analysis.json`, con su sextuplo (CONTRATO.md).
 *  O tiene `value` con su unidad y su banda, o tiene `null_reason`: nunca las dos.
 *  El `method` de la banda es la frase del motor con la tolerancia real de cada
 *  evento ancla; va opcional porque el archivo lo escribió otra versión del
 *  contrato y la pantalla no lo puede suponer (es el rótulo que se muestra). */
export interface Metrica {
  value: number | null;
  unit: string;
  confidence: { value: number; method: string } | null;
  uncertainty: { low: number; high: number; method?: string } | null;
  view: string;
  mdc: number | null;
  level: number;
  fps_min: number;
  fps_min_met: boolean;
  fps_provenance: Procedencia;
  judgment_allowed: boolean;
  null_reason: string | null;
}

/** Lo que la pantalla usa de `analysis.json`; el archivo tiene bastante más. */
export interface Analysis {
  header: { schema_version: string; engine_version: string; registry_version: string; source: { fps_real: number; fps_provenance: Procedencia | null; capture_path_id: string } };
  /** `scale_px` / `scale_source` son del contrato 2.1.0 y `scale_frame` del 2.2.0;
   *  los tres van opcionales: un trabajo anterior no los trae y no se le inventa
   *  ninguno. Son el divisor de las métricas en cm de ESA repetición y el cuadro
   *  del que salió — `quality.scale_px` es la mediana entre repeticiones y con
   *  dos o más no es el divisor de ninguna, ni su cuadro el de ninguna. */
  reps: { rep: number; frame_start: number; frame_end: number; scale_px?: number | null; scale_source?: EscalaFuente | null; scale_frame?: number | null; metrics: Record<string, Metrica> }[];
  warnings: string[];
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

// --- el modo: `local` (con backend) o `demo` (archivos estáticos) --------------------

/** La transformación afín del origen al video exportado, tal como la escribe
 *  `kinelab.tools.exportar_demo`. Los keypoints NO se reescriben: esto es cómo
 *  pasar de `image_px` del `pose.npz` al video que se sirve (CONTEXTO.md
 *  §Sistemas de coordenadas: toda serie lleva su marco). */
export interface Transformacion {
  schema: string;
  reference_frame_origen: string;
  reference_frame_destino: string;
  nota: string;
  offset_x: number;
  offset_y: number;
  escala: number;
  cuadro_offset: number;
  cuadros: number;
  fps: number;
  tamano_origen: [number, number];
  recorte: { x: number; y: number; ancho: number; alto: number };
  tamano_destino: [number, number];
  modo_recorte: string;
  cuadros_origen: number;
  tramo_origen: [number, number];
  /** Los que caen fuera del cuadro del ORIGEN: ningún recorte los puede incluir. */
  puntos_fuera_del_origen: { n: number; de: number; nota: string | null };
  video_limpio: string | null;
  video_limpio_null_reason: string | null;
}

/** `x_demo = (x_origen − offset_x) · escala`, y lo mismo en y. La misma fórmula que
 *  `kinelab.tools.exportar_demo.aplicar`, que es contra la que se testea. */
export function aplicarTransformacion(tr: Transformacion, x: number, y: number): [number, number] {
  return [(x - tr.offset_x) * tr.escala, (y - tr.offset_y) * tr.escala];
}

export type Modo = "local" | "demo";

/** `demo` sólo si la variable lo dice: el default es el de siempre. Se lee una vez;
 *  en Next es una constante sustituida en el build, no un valor de runtime. */
export const MODO: Modo = process.env.NEXT_PUBLIC_KINELAB_MODO === "demo" ? "demo" : "local";
export const ES_DEMO = MODO === "demo";

export const DEMO_BASE = "/demo";
const INDICE_DEMO = "index.json";

/** Lo que dice la pantalla en lugar del formulario de subir. El motor no se
 *  despliega: no es una limitación de esta página, es de qué es el motor. */
export const AVISO_DEMO =
  "Esto es una demo estática: los resultados ya están calculados. El motor corre en la Mac del entrenador —" +
  " onnxruntime con CoreML, pesos de cientos de MB, 76 s por clip de 18 s— y no se despliega en ningún servidor." +
  " Acá no se puede subir un video: lo que se ve es el visor sobre resultados guardados.";

/** Una fila de `/demo/index.json`. Es una `TrabajoFila` más los avisos ya juntados. */
export interface DemoFila extends TrabajoFila {
  avisos: string[];
}

export interface DemoIndice {
  schema: string;
  generado: string;
  aviso: string;
  trabajos: DemoFila[];
}

async function leerJson<T>(url: string): Promise<T> {
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(await leerError(r));
  return (await r.json()) as T;
}

/** El `transformacion.json` del trabajo, en modo demo. `null` en modo local: ahí el
 *  video que se sirve es el del trabajo, sin recortar, y no hay nada que aplicar. */
export async function getTransformacion(t: Trabajo): Promise<Transformacion | null> {
  const u = t.archivos["transformacion.json"];
  if (!u) return null;
  return leerJson<Transformacion>(u);
}

const CLAVE_ULTIMO = "kinelab:ultimo-trabajo";
const CLAVE_CAMINO = "kinelab:camino";
/** El camino genérico de `capture-paths.yaml`: "no sé con qué se filmó". Es el default. */
export const CAMINO_DESCONOCIDO = "desconocido-video";

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

/** GET /api/config: el deporte y los caminos de captura de `capture-paths.yaml`.
 *  En demo no hay backend que la responda; tampoco hay quien la use, porque el
 *  único que la pide es el formulario de subir y en demo no se muestra. */
export async function getConfig(): Promise<Config> {
  if (ES_DEMO) throw new Error(AVISO_DEMO);
  return leerJson<Config>("/api/config");
}

/** PUT /api/datos con el archivo como cuerpo crudo. XHR porque fetch no informa el progreso de subida. */
export function subirVideo(archivo: File, alturaM: number | null, camino: string, onProgreso: (fraccion: number) => void): Promise<Trabajo> {
  if (ES_DEMO) return Promise.reject(new Error(AVISO_DEMO));
  const q = new URLSearchParams({ filename: archivo.name, camino });
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
  // En demo, el `trabajo.json` estático tiene exactamente la forma que devuelve
  // `GET /api/datos/<id>`, con `archivos` apuntando a `/demo/<id>/…`: lo escribe
  // así el exportador para que de acá hacia afuera no haya dos caminos.
  if (ES_DEMO) return leerJson<Trabajo>(`${DEMO_BASE}/${encodeURIComponent(id)}/trabajo.json`);
  return leerJson<Trabajo>(`/api/datos/${encodeURIComponent(id)}`);
}

/** Los trabajos que hay en disco, del más nuevo al más viejo. Incluye los ejemplos. */
export async function listarTrabajos(): Promise<TrabajoFila[]> {
  if (ES_DEMO) return (await leerJson<DemoIndice>(`${DEMO_BASE}/${INDICE_DEMO}`)).trabajos;
  return leerJson<TrabajoFila[]>("/api/datos");
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

/** El último camino elegido. Se recuerda porque el teléfono no cambia entre clips. */
export function caminoRecordado(): string | null {
  try {
    return localStorage.getItem(CLAVE_CAMINO);
  } catch {
    return null;
  }
}

export function recordarCamino(id: string): void {
  try {
    localStorage.setItem(CLAVE_CAMINO, id);
  } catch {
    /* sin localStorage, sólo hay que volver a elegirlo */
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

/** El `analysis.json` del trabajo: de ahí salen las métricas del registro, cada
 *  una con su valor o con la razón por la que no se pudo calcular. Son ~15 KB. */
export async function bajarAnalysis(url: string): Promise<Analysis> {
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(await leerError(r));
  return (await r.json()) as Analysis;
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
