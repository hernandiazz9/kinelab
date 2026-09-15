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
//     su definición promete;
//  3. el encuadre automático mete al sujeto entero —los 26 puntos de los 448
//     cuadros— adentro del canvas, en un barrido de ángulos de cámara, que es
//     lo que el encargo 23 fue a arreglar (los pies quedaban cortados);
//  4. la capa de ángulos muestra el número del archivo y no uno compuesto acá:
//     el proyectado que aparece al llegar a una vista del protocolo sale de
//     `angulos_proyectados[vista]`, y `vistaDelProtocolo` reconoce esa vista
//     después de la vuelta por azimut / elevación que hace el botón.
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
import { cajaDelSujeto, caminoDe, encuadreDe, fraccionProyectada, marcoCamara, posicionDe, proyectar, proyectarEn, vistaDelProtocolo } from "./pose3d.ts";

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

// El encuadre: la figura entera adentro del canvas, en TODOS los cuadros y en
// cualquier ángulo. Los márgenes son los de `Visor3D.tsx`.
{
  const d = JSON.parse(readFileSync(`${trabajo("face_on")}/pose3d.json`, "utf8"));
  const { camino, objetivo, distancia } = caminoDe(d.camaras.face_on);
  const W = 337;
  const H = 599; // el canvas de una columna angosta: alto 0,78 de la ventana, aspecto 1080×1920
  const mx = Math.max(22, Math.min(52, W * 0.13));
  const my = Math.max(22, Math.min(44, H * 0.07));
  let peorSobra = Infinity;
  let peorEn = "";
  for (let az = -180; az < 180; az += 15) {
    for (let el = -20; el <= 60; el += 10) {
      const m = marcoCamara(posicionDe(objetivo, distancia, { az, el, f: camino.f }), objetivo);
      const caja = cajaDelSujeto(d.puntos, m, camino.f);
      const enc = encuadreDe(caja, W, H, mx, my, 1);
      let sobra = Infinity;
      for (let t = 0; t < d.frames; t++) {
        for (let j = 0; j < d.nombres.length; j++) {
          const q = proyectarEn(d.puntos[t][j], m, camino.f, enc);
          if (q.z <= 0.05) continue;
          sobra = Math.min(sobra, q.u, W - q.u, q.v, H - q.v);
        }
      }
      if (sobra < peorSobra) {
        peorSobra = sobra;
        peorEn = `az ${az}° · el ${el}°`;
      }
    }
  }
  if (peorSobra < 0) throw new Error(`el sujeto se sale del canvas por ${(-peorSobra).toFixed(1)} px en ${peorEn}`);
  console.log(`  encuadre: en 24 × 9 ángulos, el punto más al borde de los 448 × 26 queda a ${peorSobra.toFixed(1)} px del canvas (${peorEn}); margen pedido ${mx.toFixed(0)} × ${my.toFixed(0)} px`);
  // Y lo de antes, para tener contra qué: escala fija `canvas ÷ cuadro del
  // protocolo` y centrado en el punto principal, que es dibujar el cuadro de
  // 1080×1920 tal cual. Ahí lo que se sale del cuadro se sale de la pantalla.
  const s0 = W / d.camaras.face_on.ancho;
  const antes = (az, el, f) => {
    const m0 = marcoCamara(posicionDe(objetivo, distancia, { az, el, f }), objetivo);
    let fuera = 0;
    let cuadros = new Set();
    for (let t = 0; t < d.frames; t++) {
      for (let j = 0; j < d.nombres.length; j++) {
        const q = proyectar(d.puntos[t][j], m0, f, s0, W, H);
        if (q.u < 0 || q.u > W || q.v < 0 || q.v > H) {
          fuera++;
          cuadros.add(t);
        }
      }
    }
    return { fuera, cuadros: cuadros.size };
  };
  for (const vista of VISTAS) {
    const c = caminoDe(d.camaras[vista]).camino;
    const r = antes(c.az, c.el, c.f);
    console.log(`  sin encuadre, con la cámara en ${vista}: ${r.fuera} de ${d.frames * d.nombres.length} puntos afuera del canvas, en ${r.cuadros} de ${d.frames} cuadros`);
  }
  let peorAntes = 0;
  for (let az = -180; az < 180; az += 15) {
    for (let el = -20; el <= 60; el += 10) peorAntes = Math.max(peorAntes, antes(az, el, camino.f).fuera);
  }
  console.log(`  sin encuadre, en el peor de los 24 × 9 ángulos: ${peorAntes} puntos afuera`);

  // El encuadre no pelea con el zoom: acercarse agranda la figura y la deja
  // centrada donde estaba. Si el factor se perdiera, la rueda no haría nada o
  // se llevaría al sujeto fuera del recuadro.
  {
    const m = marcoCamara(posicionDe(objetivo, distancia, camino), objetivo);
    const caja = cajaDelSujeto(d.puntos, m, camino.f);
    const medir = (k) => {
      const enc = encuadreDe(caja, W, H, mx, my, k);
      let u0 = Infinity;
      let u1 = -Infinity;
      let v0 = Infinity;
      let v1 = -Infinity;
      for (let t = 0; t < d.frames; t++) {
        for (let j = 0; j < d.nombres.length; j++) {
          const q = proyectarEn(d.puntos[t][j], m, camino.f * k, enc);
          u0 = Math.min(u0, q.u);
          u1 = Math.max(u1, q.u);
          v0 = Math.min(v0, q.v);
          v1 = Math.max(v1, q.v);
        }
      }
      return { alto: v1 - v0, cu: (u0 + u1) / 2, cv: (v0 + v1) / 2 };
    };
    const uno = medir(1);
    for (const k of [0.3, 0.5, 2, 4]) {
      const z = medir(k);
      if (Math.abs(z.alto / uno.alto - k) > 0.02) throw new Error(`con la rueda × ${k} la figura quedó × ${(z.alto / uno.alto).toFixed(3)}`);
      if (Math.abs(z.cu - W / 2) > 1 || Math.abs(z.cv - H / 2) > 1) throw new Error(`con la rueda × ${k} la figura se descentró a (${z.cu.toFixed(1)}, ${z.cv.toFixed(1)}) en un canvas de ${W} × ${H}`);
    }
    console.log(`  el zoom sigue siendo zoom: × 0,3 a × 4 agrandan la figura ese mismo factor y la dejan centrada (1:1 = ${uno.alto.toFixed(0)} px de alto)`);
  }

  // Cuánto mide el sujeto en el recuadro, antes y después: el encuadre paga el
  // margen de los números con tamaño, y conviene saber cuánto.
  const alto = (m, f, enc) => {
    let v0 = Infinity;
    let v1 = -Infinity;
    for (let t = 0; t < d.frames; t++) {
      for (let j = 0; j < d.nombres.length; j++) {
        const q = enc ? proyectarEn(d.puntos[t][j], m, f, enc) : proyectar(d.puntos[t][j], m, f, s0, W, H);
        v0 = Math.min(v0, q.v);
        v1 = Math.max(v1, q.v);
      }
    }
    return v1 - v0;
  };
  for (const vista of VISTAS) {
    const c = caminoDe(d.camaras[vista]).camino;
    const m = marcoCamara(posicionDe(objetivo, distancia, c), objetivo);
    const enc = encuadreDe(cajaDelSujeto(d.puntos, m, camino.f), W, H, mx, my, c.f / camino.f);
    console.log(`  alto de la caja del sujeto en un recuadro de ${W} × ${H}, desde ${vista}: ${alto(m, c.f, null).toFixed(0)} px sin encuadre → ${alto(m, c.f, enc).toFixed(0)} px con encuadre`);
  }
}

// La capa de ángulos: el número que dibuja sale del archivo.
{
  for (const archivoDe of VISTAS) {
    const d = JSON.parse(readFileSync(`${trabajo(archivoDe)}/pose3d.json`, "utf8"));
    const addr = d.eventos?.address ?? d.eventos_3d.address;
    for (const vista of VISTAS) {
      const { camino } = caminoDe(d.camaras[vista]);
      const reconocida = vistaDelProtocolo(camino, d.camaras);
      if (reconocida !== vista) throw new Error(`«ver como ${vista}» deja la cámara en una vista que el visor llama ${reconocida}`);
      const partes = ["elbow_right_deg", "hip_line_turn_deg"].map((k) => {
        const real = d.angulos_3d[k][addr];
        const proy = d.angulos_proyectados[vista][k][addr];
        const ref = d.angulos.definiciones[k].comparar === "abs" ? Math.abs(real) : real;
        return `${k} 3-D ${real.toFixed(1)}° · desde ${vista} ${proy.toFixed(1)}° (${(proy - ref >= 0 ? "+" : "") + (proy - ref).toFixed(1)}°)`;
      });
      console.log(`  ${archivoDe} · ángulos en el address (cuadro ${addr}): ${partes.join(" · ")}`);
    }
    // con la cámara en cualquier otro lado no hay proyectado que mostrar
    if (vistaDelProtocolo({ ...caminoDe(d.camaras.face_on).camino, az: 37 }, d.camaras) !== null) throw new Error("el visor cree que az 37° es una vista del protocolo");
  }
}

console.log(`  ok · el peor error de las cuatro combinaciones es ${peorDeTodo.toFixed(3)} px, y es el redondeo a milímetros del archivo`);
