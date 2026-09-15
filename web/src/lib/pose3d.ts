// `pose3d.json` y la proyección que el propio archivo declara.
//
// Está aparte del componente a propósito: es matemática pura, sin React y sin
// canvas, así se puede correr con `node --experimental-strip-types` y comparar
// contra el `pose.npz` del arnés sin abrir un navegador. La receta es la de
// `camaras.<vista>.modelo` del archivo, y el test que la fija está en Python
// (`truth/tests/test_pose3d.py`): ahí la misma fórmula, escrita a mano, tiene
// que reproducir el `pose.npz` dentro de 1 px en las dos vistas.

export type V3 = [number, number, number];

/** Una cámara del protocolo, tal como la escribe `mocap.camera_record`. */
export interface Camara {
  vista: string;
  ancho: number;
  alto: number;
  fx: number;
  fy: number;
  cx: number;
  cy: number;
  dist: number[];
  posicion_m: V3;
  objetivo_m: V3;
  distancia_m: number;
  altura_camara_m: number;
  cuerpo_px: number;
  cuerpo_frac_del_alto: number;
  procedencia: string;
  modelo: string;
}

/** `pose3d.json`. El marco, las unidades y los rótulos son parte del archivo. */
export interface Pose3D {
  schema: string;
  que_es: string;
  marco: { id: string; unidades: string; origen: string; ejes: { x: string; y: string; z: string }; mano: string };
  suelo: { punto_mas_bajo: { nombre: string; cuadro: number }; pies_sobre_el_cero_en_el_cuadro_de_referencia_m: number; nota: string };
  decimales: number;
  fps: number;
  fps_nota: string;
  frames: number;
  trial: string;
  sujeto: string;
  vista_del_trabajo: string;
  estatura_m: number;
  cuadro_de_referencia: number;
  nombres: string[];
  huesos: [number, number][];
  puntos_construidos: Record<string, string>;
  eventos: Record<string, number> | null;
  eventos_3d: Record<string, number>;
  camaras: Record<string, Camara>;
  indicador: {
    que_mide: string;
    unidad: string;
    definicion: string;
    umbral_colapso_frac: number;
    lineas: Record<string, [string, string]>;
    texto: string;
    texto_colapso: string;
    medido: string;
  };
  /** desde `kinelab.pose3d/1.1.0`. Un archivo 1.0.0 no los trae y el visor
   *  abre igual, sin la capa de ángulos. */
  angulos?: Angulos;
  rotulos: { resumen: string; fuente: string; no_es_video: string; no_con_un_celular: string; para_que_sirve: string; descriptivo: string };
  atribucion: string;
  /** `{nombre: [un valor por cuadro]}`. `null` donde el ángulo no existe. */
  angulos_3d?: Record<string, (number | null)[]>;
  /** `{vista: {nombre: [un valor por cuadro]}}`, una por cámara del protocolo. */
  angulos_proyectados?: Record<string, Record<string, (number | null)[]>>;
  puntos: number[][][];
}

/** Una definición de ángulo, tal como la escribe `mocap.angulos_doc`. */
export interface DefAngulo {
  etiqueta: string;
  definicion: string;
  puntos: string[];
  /** los keypoints en cuyo punto medio se dibuja el número. */
  anclaje: string[];
  rango: [number, number];
  /** contra qué se compara el proyectado: el valor, o su valor absoluto. */
  comparar: "valor" | "abs";
  respecto_de: string;
  proyectado: string;
}

export interface Angulos {
  unidad: string;
  decimales: number;
  marco_3d: string;
  marco_proyectado: string;
  procedencia_3d: string;
  procedencia_proyectado: string;
  nota_respecto_de: string;
  definiciones: Record<string, DefAngulo>;
  rotulo: string;
  texto_comparacion: string;
  nota_nivel: string;
  nota_diferencia: string;
  resumen: { ventana: [number, number]; eventos: Record<string, number>; nota: string; por_vista: Record<string, Record<string, Record<string, number>>> };
}

// --- la proyección, palabra por palabra como la declara el archivo ------------

export function normalizar(v: V3): V3 {
  const n = Math.hypot(v[0], v[1], v[2]);
  return [v[0] / n, v[1] / n, v[2] / n];
}

export function cruz(a: V3, b: V3): V3 {
  return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
}

/** El estado de la cámara del visor: la posición sale de estos tres números. */
export interface Camino {
  /** grados alrededor del eje vertical; 0 = `face_on`, −90 = `down_the_line`. */
  az: number;
  /** grados por encima de la horizontal. */
  el: number;
  /** focal en píxeles del cuadro del protocolo (1080×1920): es el zoom. */
  f: number;
}

export function posicionDe(objetivo: V3, distancia: number, c: Camino): V3 {
  const a = (c.az * Math.PI) / 180;
  const e = (c.el * Math.PI) / 180;
  return [objetivo[0] + distancia * Math.sin(a) * Math.cos(e), objetivo[1] + distancia * Math.sin(e), objetivo[2] + distancia * Math.cos(a) * Math.cos(e)];
}

/** El az / el / f de una cámara del protocolo, para poder ir exactamente ahí. */
export function caminoDe(cam: Camara): { camino: Camino; objetivo: V3; distancia: number } {
  const o = cam.objetivo_m;
  const off: V3 = [cam.posicion_m[0] - o[0], cam.posicion_m[1] - o[1], cam.posicion_m[2] - o[2]];
  const distancia = Math.hypot(off[0], off[1], off[2]);
  return {
    camino: { az: (Math.atan2(off[0], off[2]) * 180) / Math.PI, el: (Math.asin(off[1] / distancia) * 180) / Math.PI, f: cam.fx },
    objetivo: o,
    distancia,
  };
}

/** `R` (filas) y la posición: `R = [r; d; f]`, con `f` mirando al objetivo. */
export function marcoCamara(posicion: V3, objetivo: V3): { R: [V3, V3, V3]; posicion: V3 } {
  const f = normalizar([objetivo[0] - posicion[0], objetivo[1] - posicion[1], objetivo[2] - posicion[2]]);
  const r = normalizar(cruz(f, [0, 1, 0]));
  const d = cruz(f, r);
  return { R: [r, d, f], posicion };
}

/** Dónde cae el origen del dibujo y con qué escala. Sale de `encuadreDe`, que
 *  mira al sujeto en TODOS los cuadros: así la figura entra entera y no cambia
 *  de tamaño al reproducir. */
export interface Encuadre {
  /** canvas ÷ cuadro del protocolo. */
  s: number;
  /** dónde cae el centro del dibujo, en píxeles del canvas. */
  ox: number;
  oy: number;
}

/** (x,y,z) en metros → (u,v) en píxeles del canvas y la profundidad `z`. */
export function proyectarEn(p: V3, m: { R: [V3, V3, V3]; posicion: V3 }, f: number, e: Encuadre): { u: number; v: number; z: number } {
  const dx = p[0] - m.posicion[0];
  const dy = p[1] - m.posicion[1];
  const dz = p[2] - m.posicion[2];
  const cx = m.R[0][0] * dx + m.R[0][1] * dy + m.R[0][2] * dz;
  const cy = m.R[1][0] * dx + m.R[1][1] * dy + m.R[1][2] * dz;
  const cz = m.R[2][0] * dx + m.R[2][1] * dy + m.R[2][2] * dz;
  return { u: (e.s * f * cx) / cz + e.ox, v: (e.s * f * cy) / cz + e.oy, z: cz };
}

/** La misma proyección centrada en el canvas: con `s = 1` da el píxel exacto
 *  del `pose.npz`, y con cualquier otro da la misma imagen escalada. Es la que
 *  verifica `pose3d.verificar.mjs` contra el arnés; no cambió. */
export function proyectar(p: V3, m: { R: [V3, V3, V3]; posicion: V3 }, f: number, s: number, W: number, H: number): { u: number; v: number; z: number } {
  return proyectarEn(p, m, f, { s, ox: W / 2, oy: H / 2 });
}

/** La caja que contiene al sujeto en **todos** los cuadros, en píxeles de la
 *  focal `f`, con el centro de la imagen en (0,0). Los puntos que quedan detrás
 *  de la cámara no cuentan: no se dibujan. */
export function cajaDelSujeto(puntos: number[][][], m: { R: [V3, V3, V3]; posicion: V3 }, f: number): { umin: number; umax: number; vmin: number; vmax: number } | null {
  let umin = Infinity;
  let umax = -Infinity;
  let vmin = Infinity;
  let vmax = -Infinity;
  const e: Encuadre = { s: 1, ox: 0, oy: 0 };
  for (const cuadro of puntos) {
    for (const p of cuadro) {
      const q = proyectarEn(p as V3, m, f, e);
      if (q.z <= 0.05) continue;
      if (q.u < umin) umin = q.u;
      if (q.u > umax) umax = q.u;
      if (q.v < vmin) vmin = q.v;
      if (q.v > vmax) vmax = q.v;
    }
  }
  return Number.isFinite(umin) && Number.isFinite(vmin) ? { umin, umax, vmin, vmax } : null;
}

/** El encuadre que hace entrar esa caja en un canvas de `W × H`, dejando
 *  `mx`/`my` de margen para los números de ángulo, que ocupan lugar.
 *
 *  `k` es el zoom: la caja se mide una vez con la focal base y acercarse con la
 *  rueda multiplica por `f / f_base`. Así el encuadre no pelea con el zoom —si
 *  se recalculara con la focal de cada momento, la rueda no haría nada— y la
 *  figura entra entera en 1:1, que es donde arranca. */
export function encuadreDe(caja: { umin: number; umax: number; vmin: number; vmax: number } | null, W: number, H: number, mx: number, my: number, k: number): Encuadre {
  if (!caja) return { s: 1, ox: W / 2, oy: H / 2 };
  const bw = Math.max(1e-6, caja.umax - caja.umin);
  const bh = Math.max(1e-6, caja.vmax - caja.vmin);
  const s = Math.max(1e-9, Math.min((W - 2 * mx) / bw, (H - 2 * my) / bh));
  return { s, ox: W / 2 - s * k * ((caja.umin + caja.umax) / 2), oy: H / 2 - s * k * ((caja.vmin + caja.vmax) / 2) };
}

/** Qué vista del protocolo es ésta, si es alguna: la comparación es de azimut
 *  y elevación y no de focal, porque acercarse con la rueda es una homotecia
 *  alrededor del centro y no cambia ningún ángulo de la imagen. */
export function vistaDelProtocolo(camino: Camino, camaras: Record<string, Camara>, tolerancia = 1.5): string | null {
  for (const [vista, cam] of Object.entries(camaras)) {
    const c = caminoDe(cam).camino;
    const daz = Math.abs(((camino.az - c.az + 540) % 360) - 180);
    if (daz <= tolerancia && Math.abs(camino.el - c.el) <= tolerancia) return vista;
  }
  return null;
}

/** El indicador: cuánto mide la línea `a`–`b` en la imagen comparada con lo que
 *  mide de verdad, desde este ángulo. Es la fórmula de `indicador.definicion`;
 *  no depende de la focal ni del zoom, sólo del ángulo. */
export function fraccionProyectada(pts: number[][], a: number, b: number, m: { R: [V3, V3, V3]; posicion: V3 }, f: number): number | null {
  const A = pts[a] as V3;
  const B = pts[b] as V3;
  if (!A || !B) return null;
  const pa = proyectar(A, m, f, 1, 0, 0);
  const pb = proyectar(B, m, f, 1, 0, 0);
  if (pa.z <= 0.05 || pb.z <= 0.05) return null;
  const largoPx = Math.hypot(pa.u - pb.u, pa.v - pb.v);
  const largoM = Math.hypot(A[0] - B[0], A[1] - B[1], A[2] - B[2]);
  if (largoM <= 0) return null;
  return (largoPx * ((pa.z + pb.z) / 2)) / (f * largoM);
}
