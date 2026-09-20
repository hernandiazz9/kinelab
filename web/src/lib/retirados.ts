// Lo que un contrato anterior dejó adentro de los datos de un trabajo: las
// claves que ADR-018 retiró, y la versión de `analysis.json` con la que se
// calculó. Están las dos acá porque son la misma pregunta —qué de este archivo
// ya no vale— y porque la lista tiene que existir en UN solo lugar: se aplica
// en tres tablas distintas.
//
// ADR-018 sacó `summary.gain` y `events[].sequence_order` del contrato, del
// motor y del CSV, y con ellos las tres columnas `*_rate_deg_s`, que salían de
// la misma función (`line_angle_rate`) y son el mismo artefacto: el arnés midió
// 11110 °/s contra 139,6 verdaderos en la línea de caderas desde
// `down_the_line`, con la proyección colapsada a 3,6 px. No es una velocidad
// angular: es el largo proyectado del segmento disfrazado de °/s. Un rótulo
// honesto sobre un número que no mide nada sigue siendo un número que no mide
// nada, así que no se muestra.
//
// Un trabajo calculado antes del bump a 2.0.0 los sigue trayendo en su
// `datos-eventos.json` (`columnas` y `picos`) y en su `datos-por-cuadro.csv`,
// que son archivos ya escritos en disco: esto es lo que hace la pantalla
// mientras no se re-analicen.
//
// Esto NO es una lista blanca de "lo que la pantalla conoce". Todo lo que el
// motor mide se muestra, con su identificador crudo si no tiene nombre legible
// (es el principio del encargo 01). Acá entra sólo lo que una decisión escrita
// retiró, por su nombre.

/** Las claves de ADR-018, por nombre. `gain` y `sequence_order` hoy no aparecen
 *  en ningún dato de la pantalla; están para que no aparezcan si alguien las
 *  vuelve a agregar. */
export const RETIRADOS: readonly string[] = ["hip_line_rate_deg_s", "shoulder_line_rate_deg_s", "arm_left_rate_deg_s", "gain", "sequence_order"];

export function esRetirado(clave: string): boolean {
  return RETIRADOS.includes(clave);
}

/** La misma lista, sin las claves retiradas. `clave` dice dónde mirar el nombre
 *  en cada elemento: una columna es su propio nombre, un pico es `[nombre, valor]`. */
export function sinRetirados<T>(items: readonly T[], clave: (item: T) => string): T[] {
  return items.filter((item) => !esRetirado(clave(item)));
}

/** Las retiradas que ESTE trabajo trae, sin repetir y en el orden de `RETIRADOS`.
 *  Vacío = el trabajo está limpio y no hay nada que avisar. */
export function retiradosEn(claves: Iterable<string>): string[] {
  const hay = new Set<string>();
  for (const c of claves) if (esRetirado(c)) hay.add(c);
  return RETIRADOS.filter((c) => hay.has(c));
}

/** La frase, tal cual, para cuando el trabajo trae alguna. Los nombres van
 *  aparte: no se muestran sus valores, pero sí cuáles son — están en el CSV que
 *  se puede descargar, y esconder su existencia sería otra falsedad. */
export const AVISO_RETIRADOS = "este trabajo se calculó con un contrato anterior y trae campos que ya no son una medición; no se muestran";

// --- la versión del contrato con la que se calculó el trabajo ------------------------

/** La versión vigente de `analysis.json` (CONTRATO.md §Versionado). */
export const CONTRATO_VIGENTE = "2.2.0";

function partes(v: string): number[] {
  return v.split(".").map((x) => Number.parseInt(x, 10));
}

/** `true` si `version` es anterior a `CONTRATO_VIGENTE`. Una versión ilegible no
 *  se declara vieja: no se inventa un veredicto sobre un dato que no se entiende. */
export function contratoAnterior(version: string | null | undefined): boolean {
  if (!version) return false;
  const a = partes(version);
  const b = partes(CONTRATO_VIGENTE);
  if (a.some((n) => !Number.isFinite(n))) return false;
  for (let i = 0; i < b.length; i++) {
    const x = a[i] ?? 0;
    if (x !== b[i]) return x < b[i];
  }
  return false;
}
