// Las columnas retiradas, contra los datos reales de la demo, sin abrir el navegador.
//
//     cd web && node --experimental-strip-types src/lib/retirados.verificar.mjs
//
// Importa la MISMA lista y la MISMA función de filtro que usan `TablaEventos`,
// `TablaCuadros` y `Avisos` (de ahí el `--experimental-strip-types`: node 22+ le
// saca los tipos a `retirados.ts` al cargarlo) y comprueba, sobre los tres
// trabajos de `web/public/demo/`, que el filtro saca **exactamente** las claves
// de ADR-018 y **ninguna otra**. Las dos mitades importan por igual: esconder de
// más rompería el principio del encargo 01 —todo lo que el motor mide se
// muestra— tanto como esconder de menos dejaría en pantalla los 3662 °/s de
// «rotación aparente de caderas», que el arnés midió como 80× el valor real.
//
// La lista esperada está escrita ACÁ otra vez, a mano, desde `DECISIONES.md`
// ADR-018 (:482 y :506-508). Es a propósito: comparar el módulo contra sí mismo
// no comprueba nada. Si alguien agrega una clave a `retirados.ts` sin pasar por
// un ADR, este script se pone en rojo.
//
// No hay infraestructura de tests en `web/` y agregarla es ADR-015 (nada nuevo
// sin preguntar), así que se corre a mano y sus números van al informe — el
// mismo patrón que `pose3d.verificar.mjs`. Va en `.mjs` por lo mismo que aquél:
// importar `./retirados.ts` con extensión desde un `.ts` pediría
// `allowImportingTsExtensions` en el `tsconfig.json`, que es de todos.

import { readFileSync, readdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { CONTRATO_VIGENTE, RETIRADOS, contratoAnterior, esRetirado, retiradosEn, sinRetirados } from "./retirados.ts";

const REPO = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
const DEMO = resolve(REPO, "web/public/demo");

// ADR-018, copiado a mano. `gain` y `sequence_order` salieron del contrato;
// las tres `*_rate_deg_s` salen de la misma función y son el mismo artefacto.
const ESPERADAS = ["hip_line_rate_deg_s", "shoulder_line_rate_deg_s", "arm_left_rate_deg_s", "gain", "sequence_order"];

let fallas = 0;
const mal = (msg) => {
  fallas++;
  console.log(`  MAL · ${msg}`);
};

// 0 · el módulo dice lo mismo que el ADR
{
  const sobran = RETIRADOS.filter((c) => !ESPERADAS.includes(c));
  const faltan = ESPERADAS.filter((c) => !RETIRADOS.includes(c));
  if (sobran.length || faltan.length) mal(`la lista del módulo no es la de ADR-018: sobran [${sobran}], faltan [${faltan}]`);
  else console.log(`  la lista es la de ADR-018, las ${RETIRADOS.length}: ${RETIRADOS.join(" · ")}`);
  for (const c of ESPERADAS) if (!esRetirado(c)) mal(`esRetirado("${c}") dice que no`);
  // y no se lleva puesto nada que se le parezca
  for (const c of ["hip_line_deg", "shoulder_line_deg", "arm_left_vs_vertical_deg", "hands_speed_cm_s", "hip_line_rate_deg_s_", "gainz", "frame"]) {
    if (esRetirado(c)) mal(`esRetirado("${c}") dice que sí, y no es de ADR-018`);
  }
}

// 1 · los tres trabajos de la demo, columna por columna
const trabajos = readdirSync(DEMO, { withFileTypes: true })
  .filter((d) => d.isDirectory())
  .map((d) => d.name)
  .sort();
if (trabajos.length !== 3) mal(`se esperaban 3 trabajos en ${DEMO} y hay ${trabajos.length}: ${trabajos.join(", ")}`);

/** Lo que el filtro saca de una lista de claves, comparado contra ADR-018. */
function revisar(donde, claves) {
  const quedan = sinRetirados(claves, (c) => c);
  const sacadas = claves.filter((c) => !quedan.includes(c));
  const deberia = claves.filter((c) => ESPERADAS.includes(c));
  const sobran = sacadas.filter((c) => !deberia.includes(c));
  const faltan = deberia.filter((c) => !sacadas.includes(c));
  if (sobran.length) mal(`${donde}: se sacaron claves que NO son de ADR-018: ${sobran.join(", ")}`);
  if (faltan.length) mal(`${donde}: quedaron claves de ADR-018 a la vista: ${faltan.join(", ")}`);
  if (quedan.length + sacadas.length !== claves.length) mal(`${donde}: ${claves.length} claves, ${quedan.length} + ${sacadas.length} después de filtrar`);
  console.log(`  ${donde}: ${claves.length} → ${quedan.length} (se sacan ${sacadas.length}${sacadas.length ? `: ${sacadas.join(" · ")}` : ""})`);
  return sacadas;
}

for (const id of trabajos) {
  console.log(`\n· ${id}`);
  const r = JSON.parse(readFileSync(resolve(DEMO, id, "datos-eventos.json"), "utf8"));
  const analysis = JSON.parse(readFileSync(resolve(DEMO, id, "analysis.json"), "utf8"));
  const version = analysis.header.schema_version;
  const viejo = contratoAnterior(version);
  console.log(`  analysis.json ${version} · ${r.cuadros} cuadros · ¿sale el aviso de contrato anterior? ${viejo ? "sí" : "no"}`);
  if (!viejo) mal(`${id}: ${version} es anterior a ${CONTRATO_VIGENTE} y no sale el aviso`);

  // (a) las columnas de `datos-eventos.json`, que son las de «Todas las variables
  //     en cada evento» y, por construcción (`kinelab/explore.py`), las mismas
  //     que el encabezado del CSV.
  revisar("datos-eventos.json · columnas", r.columnas);

  // (b) la tabla de picos
  const picosAntes = Object.entries(r.picos);
  const picosDespues = sinRetirados(picosAntes, ([k]) => k);
  const picosFuera = picosAntes.filter(([k]) => !picosDespues.some(([j]) => j === k));
  revisar("datos-eventos.json · picos", Object.keys(r.picos));
  for (const [k, v] of picosFuera) console.log(`    deja de mostrarse: ${k} = ${v}`);

  // (c) el encabezado del CSV, que es lo que lee `TablaCuadros`
  const cabecera = readFileSync(resolve(DEMO, id, "datos-por-cuadro.csv"), "utf8").split("\n", 1)[0].trim().split(",");
  const fueraCsv = revisar("datos-por-cuadro.csv · encabezado", cabecera);

  // (d) y las dos listas tienen que coincidir: el CSV y `columnas` son el mismo
  //     `names` de `explore.py`. Si se separaran, la tabla de arriba y la de
  //     abajo mostrarían cosas distintas y nadie se enteraría.
  const soloEnUna = [...cabecera.filter((c) => !r.columnas.includes(c)), ...r.columnas.filter((c) => !cabecera.includes(c))];
  if (soloEnUna.length) mal(`el CSV y \`columnas\` no coinciden: ${soloEnUna.join(", ")}`);

  // (e) el aviso de arriba nombra exactamente lo que se sacó
  const avisadas = retiradosEn([...r.columnas, ...Object.keys(r.picos)]);
  const sacadasTodas = [...new Set([...fueraCsv, ...picosFuera.map(([k]) => k)])].sort();
  if (avisadas.slice().sort().join("|") !== sacadasTodas.join("|")) mal(`el aviso nombra [${avisadas}] y se sacaron [${sacadasTodas}]`);
  console.log(`  el aviso de arriba nombra: ${avisadas.length ? avisadas.join(" · ") : "(nada: el trabajo está limpio)"}`);
}

// 2 · el aviso de contrato anterior, del otro lado: un `analysis.json` al día no
//     lo tiene que sacar. El ejemplo del repo es el único al día que va a git
//     (hoy 2.1.0: el encargo 33 agregó `reps[].scale_px` y `reps[].scale_source`).
{
  console.log(`\n· el aviso de contrato anterior (vigente: ${CONTRATO_VIGENTE})`);
  const p = resolve(REPO, "data/examples/analysis.example.json");
  try {
    const v = JSON.parse(readFileSync(p, "utf8")).header.schema_version;
    if (contratoAnterior(v)) mal(`data/examples/analysis.example.json es ${v} y sale el aviso de contrato anterior`);
    else console.log(`  data/examples/analysis.example.json es ${v}: no sale. Bien.`);
  } catch (e) {
    mal(`no se pudo leer ${p}: ${e.message}`);
  }
  // y los bordes, a mano
  for (const [v, esperado] of [
    ["1.0.0", true],
    ["1.2.0", true],
    ["1.9.9", true],
    // 2.0.0 y 2.0.1 pasaron a ser anteriores con el bump a 2.1.0: un trabajo suyo
    // no trae `reps[].scale_px`, así que la pantalla no muestra la escala y lo dice.
    ["2.0.0", true],
    ["2.0.1", true],
    ["2.1.0", false],
    ["2.1.1", false],
    ["3.0.0", false],
    [null, false],
    ["", false],
    ["vieja", false], // ilegible: no se declara nada
  ]) {
    if (contratoAnterior(v) !== esperado) mal(`contratoAnterior(${JSON.stringify(v)}) da ${contratoAnterior(v)} y se esperaba ${esperado}`);
  }
  console.log(`  los 11 bordes de versión dan lo esperado`);
}

// 3 · un trabajo al día no pierde nada. `data/incoming/` está fuera de git: si
//     no está, se dice y se sigue — no es la prueba, es el control.
{
  const p = resolve(REPO, "data/incoming/vid1.kinelab/datos-eventos.json");
  let r = null;
  try {
    r = JSON.parse(readFileSync(p, "utf8"));
  } catch {
    console.log(`\n· control con un trabajo al contrato vigente (${CONTRATO_VIGENTE}): falta ${p} (está fuera de git). Se rehace con:\n    .venv/bin/python -m kinelab datos data/incoming/vid1.mp4 --altura-m 1.75`);
  }
  if (r) {
    console.log(`\n· control · data/incoming/vid1.kinelab (re-analizado con HEAD)`);
    const sacadas = revisar("datos-eventos.json · columnas", r.columnas);
    const sacadasPicos = revisar("datos-eventos.json · picos", Object.keys(r.picos));
    if (sacadas.length || sacadasPicos.length) mal("un trabajo al contrato vigente no tendría que perder ninguna columna");
  }
}

if (fallas) {
  console.log(`\n${fallas} falla(s).`);
  process.exit(1);
}
console.log(`\n  ok · el filtro saca exactamente las claves de ADR-018 y ninguna otra, en los ${trabajos.length} trabajos de la demo.`);
