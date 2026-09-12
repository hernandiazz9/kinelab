// Nombres legibles, unidad y decimales de cada columna de `datos-por-cuadro.csv`.
// Lo que no está acá se muestra con su identificador tal cual: nada se esconde.

export interface Etiqueta {
  nombre: string;
  unidad: string;
  dec: number;
  signo?: boolean;
}

const PUNTOS: Record<string, string> = {
  nose: "nariz",
  left_eye: "ojo izq.",
  right_eye: "ojo der.",
  left_ear: "oreja izq.",
  right_ear: "oreja der.",
  left_shoulder: "hombro izq.",
  right_shoulder: "hombro der.",
  left_elbow: "codo izq.",
  right_elbow: "codo der.",
  left_wrist: "muñeca izq.",
  right_wrist: "muñeca der.",
  left_hip: "cadera izq.",
  right_hip: "cadera der.",
  left_knee: "rodilla izq.",
  right_knee: "rodilla der.",
  left_ankle: "tobillo izq.",
  right_ankle: "tobillo der.",
  head: "cabeza",
  neck: "cuello",
  hip: "centro de cadera (predicho por la red)",
  left_big_toe: "dedo gordo izq.",
  right_big_toe: "dedo gordo der.",
  left_small_toe: "dedo chico izq.",
  right_small_toe: "dedo chico der.",
  left_heel: "talón izq.",
  right_heel: "talón der.",
};

const SEGMENTOS: Record<string, string> = { pelvis: "pelvis", thorax: "tórax", head: "cabeza", hands: "manos" };

const FIJAS: Record<string, Etiqueta> = {
  frame: { nombre: "cuadro", unidad: "", dec: 0 },
  t_s: { nombre: "tiempo", unidad: "s", dec: 3 },
  plausibility_flags: { nombre: "banderas de plausibilidad (0 = limpio)", unidad: "", dec: 0 },
  body_height_px: { nombre: "altura del cuerpo", unidad: "px", dec: 0 },
  elbow_left_deg: { nombre: "codo izquierdo", unidad: "°", dec: 1 },
  elbow_right_deg: { nombre: "codo derecho", unidad: "°", dec: 1 },
  knee_left_deg: { nombre: "rodilla izquierda", unidad: "°", dec: 1 },
  knee_right_deg: { nombre: "rodilla derecha", unidad: "°", dec: 1 },
  hip_left_deg: { nombre: "cadera izquierda (hombro-cadera-rodilla)", unidad: "°", dec: 1 },
  hip_right_deg: { nombre: "cadera derecha (hombro-cadera-rodilla)", unidad: "°", dec: 1 },
  shoulder_left_deg: { nombre: "hombro izquierdo (codo-hombro-cadera)", unidad: "°", dec: 1 },
  shoulder_right_deg: { nombre: "hombro derecho (codo-hombro-cadera)", unidad: "°", dec: 1 },
  trunk_lean_deg: { nombre: "tronco vs vertical (+ = hombros a la derecha de la imagen)", unidad: "°", dec: 1, signo: true },
  shoulder_line_deg: { nombre: "línea de hombros vs horizontal", unidad: "°", dec: 1, signo: true },
  hip_line_deg: { nombre: "línea de caderas vs horizontal", unidad: "°", dec: 1, signo: true },
  arm_left_vs_vertical_deg: { nombre: "brazo izquierdo vs vertical", unidad: "°", dec: 1, signo: true },
  arm_right_vs_vertical_deg: { nombre: "brazo derecho vs vertical", unidad: "°", dec: 1, signo: true },
  hands_x_vs_hip_bh: { nombre: "manos vs centro de cadera (x)", unidad: "alturas", dec: 3, signo: true },
  hands_height_pct: { nombre: "altura de manos sobre los tobillos", unidad: "%", dec: 1 },
  hands_speed_bh_s: { nombre: "velocidad de manos", unidad: "alturas/s", dec: 2 },
  hands_speed_cm_s: { nombre: "velocidad de manos", unidad: "cm/s", dec: 0 },
  shoulder_line_rate_deg_s: { nombre: "rotación aparente de la línea de hombros", unidad: "°/s", dec: 0, signo: true },
  hip_line_rate_deg_s: { nombre: "rotación aparente de la línea de caderas", unidad: "°/s", dec: 0, signo: true },
  arm_left_rate_deg_s: { nombre: "rotación del brazo izquierdo", unidad: "°/s", dec: 0, signo: true },
};

export const DURACIONES: Record<string, string> = {
  address_to_top_ms: "backswing (address → top)",
  top_to_impact_ms: "downswing (top → impacto)",
  impact_to_follow_end_ms: "impacto → fin del follow-through",
  tempo_ratio: "tempo (backswing ÷ downswing)",
};

export const EVENTOS: Record<string, string> = { address: "address", top: "top", impact: "impacto", follow_end: "fin" };

export function etiqueta(col: string): Etiqueta {
  const fija = FIJAS[col];
  if (fija) return fija;
  let m = col.match(/^(\w+)_d([xy])_vs_address_(pct|cm)$/);
  if (m) {
    const eje = m[2] === "x" ? "dx (+ = derecha)" : "dy (+ = sube)";
    return { nombre: `${SEGMENTOS[m[1]] ?? m[1]} vs address · ${eje}`, unidad: m[3] === "cm" ? "cm" : "% altura", dec: 1, signo: true };
  }
  m = col.match(/^(\w+)_(x|y|score)$/);
  if (m && PUNTOS[m[1]]) {
    if (m[2] === "score") return { nombre: `${PUNTOS[m[1]]} · confianza`, unidad: "", dec: 2 };
    return { nombre: `${PUNTOS[m[1]]} · ${m[2]}`, unidad: "px", dec: 0 };
  }
  return { nombre: col, unidad: "", dec: 2 };
}

const formatos = new Map<string, Intl.NumberFormat>();

export function fmt(v: number | null | undefined, dec = 1, signo = false): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return "—";
  const k = `${dec}${signo ? "+" : ""}`;
  let f = formatos.get(k);
  if (!f) {
    f = new Intl.NumberFormat("es-AR", { minimumFractionDigits: dec, maximumFractionDigits: dec, signDisplay: signo ? "exceptZero" : "auto" });
    formatos.set(k, f);
  }
  return f.format(v);
}

export function fmtCol(col: string, v: number | null | undefined): string {
  const e = etiqueta(col);
  const s = fmt(v, e.dec, e.signo);
  return s === "—" || !e.unidad ? s : e.unidad === "°" || e.unidad === "%" ? `${s}${e.unidad}` : `${s} ${e.unidad}`;
}
