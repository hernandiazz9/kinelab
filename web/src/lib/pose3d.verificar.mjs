// El visor 3-D contra el arnés, sin abrir el navegador.
//
//     cd web && node --experimental-strip-types src/lib/pose3d.verificar.mjs
//
// Importa las MISMAS funciones que usa `Visor3D.tsx` (de ahí el
// `--experimental-strip-types`: node 22+ le saca los tipos a `pose3d.ts` al
// cargarlo) y comprueba dos cosas sobre el ejemplo de mocap de
// `data/exploracion/`:
//
//  1. proyectar el `pose3d.json` con cada una de las dos cámaras del protocolo
//     reproduce el `pose.npz` de esa vista dentro de 1 px — o sea que lo que
//     dibuja la pantalla es lo mismo que midió el motor;
//  2. el indicador de líneas colapsadas no se mueve con el zoom, que es lo que
//     su definición promete.
//
// Lo (1) también lo verifica `truth/tests/test_pose3d.py`, pero ahí la fórmula
// está escrita en Python: este script es el único que mira el TypeScript que de
// verdad corre en la pantalla. No hay infraestructura de tests en `web/` y
// agregarla es ADR-015 (nada nuevo sin preguntar), así que se corre a mano y sus
// números van al informe. Va en `.mjs` a propósito: en `.ts` habría que
// importar `./pose3d.ts` con extensión y eso necesita `allowImportingTsExtensions`
// en el `tsconfig.json`, que es de todos.

import { readFileSync, statSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { caminoDe, fraccionProyectada, marcoCamara, posicionDe, proyectar } from "./pose3d.ts";

const REPO = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
const trabajo = (vista) => resolve(REPO, `data/exploracion/ejemplo-cmu-64_01-${vista}`);
const NPZ_JSON = process.env.KINELAB_NPZ2D ?? resolve(REPO, "data/exploracion/npz2d.json");
const VISTAS = ["face_on", "down_the_line"];
const VOLCADO = `.venv/bin/python -c 'import json;from pathlib import Path;from kinelab.perception.posestore import load_pose;d=Path("data/exploracion");json.dump({v: load_pose(d/f"ejemplo-cmu-64_01-{v}").keypoints.tolist() for v in ("face_on","down_the_line")}, open(d/"npz2d.json","w"))'`;

function leer(path, comoHacerlo) {
  try {
    return readFileSync(path, "utf8");
  } catch {
    throw new Error(`falta ${path}.\n  ${comoHacerlo}`);
  }
}

// El `pose.npz` es un `.npz` y node no lo lee: hay que volcarlo a JSON antes.
const comoVolcar = `Volcá los keypoints 2-D del pose.npz a JSON, desde la raíz del repo:\n\n  ${VOLCADO}\n`;
const npz = JSON.parse(leer(NPZ_JSON, comoVolcar));

// Un volcado más viejo que el ejemplo compara contra otra corrida, y el error
// de más de 1 px diría "el visor miente" cuando el que está viejo es el volcado.
for (const vista of VISTAS) {
  if (statSync(NPZ_JSON).mtimeMs < statSync(`${trabajo(vista)}/pose3d.json`).mtimeMs) {
    throw new Error(`${NPZ_JSON} es más viejo que el ejemplo de ${vista}: volvé a volcarlo.\n  ${comoVolcar}`);
  }
}

let peorDeTodo = 0;
for (const archivoDe of VISTAS) {
  const d = JSON.parse(
    leer(
      `${trabajo(archivoDe)}/pose3d.json`,
      `Regenerá el ejemplo:\n\n  cd truth && .venv/bin/python -m kinelab_truth.mocap 64_01 --vista ${archivoDe} --out ../data/exploracion/ejemplo-cmu-64_01-${archivoDe} --etiqueta ejemplo\n`,
    ),
  );
  for (const vista of VISTAS) {
    const cam = d.camaras[vista];
    // el mismo camino que toma el botón «ver como <vista>» del visor: si la
    // vuelta por azimut / elevación perdiera algo, se vería acá
    const { camino, objetivo, distancia } = caminoDe(cam);
    const m = marcoCamara(posicionDe(objetivo, distancia, camino), objetivo);
    let peor = 0;
    for (let t = 0; t < d.frames; t++) {
      for (let j = 0; j < d.nombres.length; j++) {
        const q = proyectar(d.puntos[t][j], m, camino.f, 1, cam.ancho, cam.alto);
        const e = npz[vista][t][j];
        peor = Math.max(peor, Math.hypot(q.u - e[0], q.v - e[1]));
      }
    }
    peorDeTodo = Math.max(peorDeTodo, peor);
    console.log(`  ${archivoDe} → ver como ${vista}: peor error ${peor.toFixed(3)} px  (az ${camino.az.toFixed(2)}° · el ${camino.el.toFixed(2)}° · f ${camino.f.toFixed(1)} px)`);
    if (peor >= 1) throw new Error(`${archivoDe} → ${vista}: ${peor.toFixed(3)} px. El visor y el arnés no coinciden: uno de los dos miente.`);
  }

  // el indicador, en el address y desde las dos vistas del protocolo
  const address = d.eventos?.address ?? d.eventos_3d.address;
  for (const vista of VISTAS) {
    const { camino, objetivo, distancia } = caminoDe(d.camaras[vista]);
    const m = marcoCamara(posicionDe(objetivo, distancia, camino), objetivo);
    const lineas = Object.entries(d.indicador.lineas).map(([nombre, par]) => {
      const x = fraccionProyectada(d.puntos[address], d.nombres.indexOf(par[0]), d.nombres.indexOf(par[1]), m, camino.f);
      return `${nombre} ${x === null ? "—" : (x * 100).toFixed(1) + " %"}`;
    });
    console.log(`  ${archivoDe} · indicador en el address (cuadro ${address}) desde ${vista}: ${lineas.join(" · ")}`);
  }
}

// El indicador promete no depender de la focal: si dependiera, acercarse con la
// rueda cambiaría el porcentaje y el número dejaría de querer decir lo que dice.
{
  const d = JSON.parse(readFileSync(`${trabajo("face_on")}/pose3d.json`, "utf8"));
  const { camino, objetivo, distancia } = caminoDe(d.camaras.face_on);
  const girado = { ...camino, az: camino.az - 37, el: camino.el + 12 }; // un ángulo que no es de ningún protocolo
  const m = marcoCamara(posicionDe(objetivo, distancia, girado), objetivo);
  const t = d.eventos_3d.top_far;
  const a = d.nombres.indexOf("left_hip");
  const b = d.nombres.indexOf("right_hip");
  const base = fraccionProyectada(d.puntos[t], a, b, m, girado.f);
  if (base === null) throw new Error("la línea de caderas no se pudo medir en el top");
  for (const factor of [0.3, 0.5, 2, 4]) {
    const con = fraccionProyectada(d.puntos[t], a, b, m, girado.f * factor);
    if (con === null || Math.abs(con - base) > 1e-9) throw new Error(`el indicador cambió con la focal × ${factor}: ${base} → ${con}`);
  }
  console.log(`  el indicador no se mueve con el zoom (az ${girado.az.toFixed(0)}° · el ${girado.el.toFixed(0)}°): ${(base * 100).toFixed(1)} % con las cinco focales`);
}

console.log(`  ok · el peor error de las cuatro combinaciones es ${peorDeTodo.toFixed(3)} px, y es el redondeo a milímetros del archivo`);
