"use client";

// El swing en 3-D, girable. Aparece SÓLO cuando el trabajo tiene `pose3d.json`,
// que hoy escribe un solo lugar: `truth/kinelab_truth/mocap.py`, a partir de un
// mocap medido con marcadores ópticos. De un video de celular no sale, y no es
// una limitación de esta pantalla: una cámara sola no mide profundidad
// (ADR-010, nivel 3 del contrato). Los rótulos que lo dicen vienen dentro del
// archivo, escritos por quien produjo el dato: acá no se compone ninguna frase.
//
// Sin dependencias nuevas (ADR-015): canvas 2-D y la misma proyección pinhole
// del arnés, que el archivo declara en `camaras.<vista>.modelo` y que un test
// del arnés (`truth/tests/test_pose3d.py`) verifica contra el `pose.npz` dentro
// de 1 px. Si el dibujo de acá y los números del motor no coincidieran, uno de
// los dos miente; el test es el que avisa.
//
// Nada de WebGL ni de librería 3-D: son 26 puntos y 29 segmentos por cuadro.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { COLOR_EVENTO } from "@/components/Reproductor";
import { EVENTOS, fmt } from "@/lib/etiquetas";
import { cajaDelSujeto, caminoDe, encuadreDe, fraccionProyectada, marcoCamara, posicionDe, proyectarEn, vistaDelProtocolo, type Camino, type Encuadre, type Pose3D, type V3 } from "@/lib/pose3d";

// --- dibujo -------------------------------------------------------------------

const IZQ = "#50dc50"; // los mismos colores del overlay (`kinelab/explore.py`)
const DER = "#ff8c3c";
const CENTRO = "#d4d4d8";
const COLOR_LINEA: Record<string, string> = { caderas: "#f0abfc", hombros: "#67e8f9" };
const GRILLA = { paso: 0.5, alcance: 1.5 };
// el amarillo de los ángulos del overlay plano (`kinelab/explore.py`, BGR 0,255,255)
const COLOR_ANGULO = "#ffff00";
const COLOR_PROYECTADO = "#fbbf24";
// Margen fijo para que los números de ángulo entren: fijo a propósito, así
// prender y apagar la capa no cambia el tamaño de la figura.
const MARGEN = { x: 0.13, y: 0.07, xMax: 52, yMax: 44, xMin: 22, yMin: 22 };
const VELOCIDADES = [0.1, 0.2, 0.25, 0.5, 0.75, 1];
const F_MIN = 0.3;
const F_MAX = 4;

function nombresLaterales(nombres: string[]): { izq: Set<number>; der: Set<number> } {
  const izq = new Set<number>();
  const der = new Set<number>();
  nombres.forEach((n, i) => {
    if (n.startsWith("left_")) izq.add(i);
    else if (n.startsWith("right_")) der.add(i);
  });
  return { izq, der };
}

interface Escena {
  ctx: CanvasRenderingContext2D;
  W: number;
  H: number;
  enc: Encuadre;
  f: number;
  m: { R: [V3, V3, V3]; posicion: V3 };
}

function punto(e: Escena, p: V3) {
  return proyectarEn(p, e.m, e.f, e.enc);
}

function segmento(e: Escena, a: V3, b: V3, color: string, ancho: number): void {
  const pa = punto(e, a);
  const pb = punto(e, b);
  if (pa.z <= 0.05 || pb.z <= 0.05) return; // detrás de la cámara: no se dibuja
  e.ctx.strokeStyle = color;
  e.ctx.lineWidth = ancho;
  e.ctx.beginPath();
  e.ctx.moveTo(pa.u, pa.v);
  e.ctx.lineTo(pb.u, pb.v);
  e.ctx.stroke();
}

function dibujarGrilla(e: Escena): void {
  const { paso, alcance } = GRILLA;
  for (let k = -alcance; k <= alcance + 1e-9; k += paso) {
    const eje = Math.abs(k) < 1e-9;
    const color = eje ? "#3f3f46" : "#232327";
    segmento(e, [k, 0, -alcance], [k, 0, alcance], color, eje ? 1.6 : 1);
    segmento(e, [-alcance, 0, k], [alcance, 0, k], color, eje ? 1.6 : 1);
  }
  // los dos ejes del marco que el archivo declara, rotulados en la escena
  const th = Math.max(11, Math.round(e.H / 60));
  e.ctx.font = `${th}px system-ui, sans-serif`;
  const poner = (p: V3, texto: string, color: string) => {
    const q = punto(e, p);
    if (q.z <= 0.05) return;
    e.ctx.fillStyle = color;
    e.ctx.textAlign = "center";
    e.ctx.fillText(texto, q.u, q.v);
  };
  poner([alcance + 0.22, 0, 0], "objetivo →", "#71717a");
  poner([0, 0, alcance + 0.22], "pelota", "#71717a");
  // una regla de medio metro sobre el eje del objetivo
  segmento(e, [0, 0.012, -alcance], [paso, 0.012, -alcance], "#a1a1aa", 2.5);
  poner([paso / 2, 0.12, -alcance], `${fmt(paso, 1)} m`, "#a1a1aa");
}

function dibujarEsqueleto(e: Escena, d: Pose3D, pts: number[][], lateral: { izq: Set<number>; der: Set<number> }): void {
  // de atrás hacia adelante, para que lo cercano tape lo lejano
  const orden = d.huesos
    .map(([a, b], i) => ({ i, z: (punto(e, pts[a] as V3).z + punto(e, pts[b] as V3).z) / 2 }))
    .sort((p, q) => q.z - p.z);
  const grueso = Math.max(2, e.H / 260);
  for (const { i } of orden) {
    const [a, b] = d.huesos[i];
    const color = lateral.izq.has(a) || lateral.izq.has(b) ? IZQ : lateral.der.has(a) || lateral.der.has(b) ? DER : CENTRO;
    segmento(e, pts[a] as V3, pts[b] as V3, color, grueso);
  }
  // las dos líneas del indicador, encima y con su color: son las que colapsan
  for (const [nombre, par] of Object.entries(d.indicador.lineas)) {
    const a = d.nombres.indexOf(par[0]);
    const b = d.nombres.indexOf(par[1]);
    if (a >= 0 && b >= 0) segmento(e, pts[a] as V3, pts[b] as V3, COLOR_LINEA[nombre] ?? "#e4e4e7", grueso * 1.8);
  }
  const r = Math.max(2, e.H / 400);
  for (const p of pts) {
    const q = punto(e, p as V3);
    if (q.z <= 0.05) continue;
    e.ctx.fillStyle = "#fafafa";
    e.ctx.beginPath();
    e.ctx.arc(q.u, q.v, r, 0, Math.PI * 2);
    e.ctx.fill();
  }
}

/** Los ángulos de un archivo que los tiene. Un `pose3d.json` 1.0.0 —el que ya
 *  está publicado en la demo— no los trae, y entonces esto es `null` y no hay
 *  capa: el visor abre igual y lo dice, en vez de romperse. */
interface Angulos3D {
  doc: NonNullable<Pose3D["angulos"]>;
  tres_d: NonNullable<Pose3D["angulos_3d"]>;
  proyectados: NonNullable<Pose3D["angulos_proyectados"]>;
}

/** El número junto a la articulación, siguiendo al punto cuando la cámara gira.
 *
 *  Cuando la cámara está exactamente en una de las dos vistas del protocolo va
 *  también, debajo, lo que mediría una cámara puesta ahí y la diferencia: los
 *  dos números salen del archivo (`angulos_3d` y `angulos_proyectados`), no se
 *  calculan en la pantalla. Arriba el real, abajo el de la cámara: es el orden
 *  que dice `angulos.texto_comparacion`. */
function dibujarAngulos(e: Escena, d: Pose3D, a: Angulos3D, pts: number[][], cuadro: number, vista: string | null): void {
  const th = Math.max(11, Math.round(e.H / 46));
  const proy = vista ? a.proyectados[vista] : null;
  e.ctx.font = `${th}px system-ui, sans-serif`;
  e.ctx.textAlign = "left";
  e.ctx.textBaseline = "middle";

  // 1 · dónde va cada rótulo: al lado del vértice del ángulo (para los dos
  //     giros, del medio de la línea), así sigue al punto cuando se gira.
  const rotulos: { u: number; v: number; alto: number; ancho: number; lineas: [string, string][] }[] = [];
  for (const [nombre, def] of Object.entries(a.doc.definiciones)) {
    const real = a.tres_d[nombre]?.[cuadro];
    if (real === null || real === undefined) continue;
    const idx = def.anclaje.map((n) => d.nombres.indexOf(n)).filter((i) => i >= 0);
    if (idx.length === 0) continue;
    const q = idx.map((i) => punto(e, pts[i] as V3));
    if (q.some((x) => x.z <= 0.05)) continue;
    const lineas: [string, string][] = [[`${fmt(real, 1)}°`, COLOR_ANGULO]];
    const p = proy ? proy[nombre]?.[cuadro] : null;
    if (p !== null && p !== undefined) {
      // la diferencia se compara contra el valor absoluto donde el proyectado
      // no puede recuperar el signo: lo dice el propio archivo en `comparar`
      const ref = def.comparar === "abs" ? Math.abs(real) : real;
      lineas.push([`${fmt(p, 1)}°  ${fmt(p - ref, 1, true)}°`, COLOR_PROYECTADO]);
    }
    rotulos.push({
      u: q.reduce((acc, x) => acc + x.u, 0) / q.length + th * 0.6,
      v: q.reduce((acc, x) => acc + x.v, 0) / q.length - th * 0.5,
      alto: lineas.length * th * 1.15,
      ancho: Math.max(...lineas.map(([t]) => e.ctx.measureText(t).width)),
      lineas,
    });
  }

  // 2 · sin pisarse: el tronco y el giro de la línea de caderas se anclan los
  //     dos en el medio de la pelvis, y los dos hombros quedan a un dedo. El
  //     que llega segundo baja lo justo para no taparle el texto al primero.
  const puestos: typeof rotulos = [];
  for (const r of rotulos) {
    for (let vuelta = 0; vuelta < rotulos.length; vuelta++) {
      const choca = puestos.find((o) => Math.abs(o.u - r.u) < Math.max(o.ancho, r.ancho) * 0.9 && r.v < o.v + o.alto && o.v < r.v + r.alto);
      if (!choca) break;
      r.v = choca.v + choca.alto + th * 0.2;
    }
    puestos.push(r);
  }

  // 3 · dibujar: contorno negro y relleno, como el overlay plano
  for (const r of puestos) {
    r.lineas.forEach(([texto, color], i) => {
      const y = r.v + i * th * 1.15;
      e.ctx.lineWidth = Math.max(2, th / 5);
      e.ctx.strokeStyle = "rgba(0,0,0,0.9)";
      e.ctx.strokeText(texto, r.u, y);
      e.ctx.fillStyle = color;
      e.ctx.fillText(texto, r.u, y);
    });
  }
  e.ctx.textBaseline = "alphabetic";
}

// --- el componente ------------------------------------------------------------

const btn = "rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-sm hover:bg-zinc-800 disabled:opacity-40";
const ALTO_MAX = 0.78; // fracción del alto de la ventana, como el reproductor

export default function Visor3D({ url }: { url: string }) {
  const [d, setD] = useState<Pose3D | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let vivo = true;
    fetch(url, { cache: "no-store" })
      .then(async (r) => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
        return (await r.json()) as Pose3D;
      })
      .then((j) => vivo && setD(j))
      .catch((e: Error) => vivo && setError(e.message));
    return () => {
      vivo = false;
    };
  }, [url]);

  return (
    <div>
      <div className="mt-6 mb-2 flex flex-wrap items-baseline gap-x-3">
        <h2 className="text-base font-semibold">El swing en 3-D, para girarlo</h2>
        <span className="text-sm text-zinc-400">movimiento medido con marcadores; no sale de ningún video</span>
      </div>
      {error && <p className="text-sm text-red-300">No se pudo leer pose3d.json: {error}</p>}
      {!error && !d && <p className="text-sm text-zinc-400">leyendo pose3d.json…</p>}
      {d && <Escenario d={d} />}
    </div>
  );
}

function Escenario({ d }: { d: Pose3D }) {
  const base = useMemo(() => caminoDe(d.camaras[d.vista_del_trabajo] ?? Object.values(d.camaras)[0]), [d]);
  const lateral = useMemo(() => nombresLaterales(d.nombres), [d.nombres]);
  const eventos = d.eventos ?? {};

  const cajaRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const arrastreRef = useRef<{ x: number; y: number; az: number; el: number } | null>(null);
  const cuadroRef = useRef(eventos.address ?? 0);

  const [tamano, setTamano] = useState<{ w: number; h: number } | null>(null);
  const [camino, setCamino] = useState<Camino>(base.camino);
  const [cuadro, setCuadro] = useState(eventos.address ?? 0);
  const [reproduciendo, setReproduciendo] = useState(false);
  const [velocidad, setVelocidad] = useState(0.25);
  const [verAngulos, setVerAngulos] = useState(true);

  useEffect(() => {
    cuadroRef.current = cuadro;
  }, [cuadro]);

  // --- tamaño: el alto lo limita la ventana, el ancho la columna. La relación
  //     de aspecto es la del cuadro del protocolo, así la imagen de las dos
  //     vistas del protocolo se puede comparar con el overlay de esa vista.
  const aspecto = (d.camaras[d.vista_del_trabajo]?.ancho ?? 1080) / (d.camaras[d.vista_del_trabajo]?.alto ?? 1920);
  useEffect(() => {
    const el = cajaRef.current?.parentElement;
    if (!el) return;
    const medir = () => {
      const h = Math.max(200, Math.min(window.innerHeight * ALTO_MAX, el.clientWidth / aspecto));
      setTamano({ w: Math.round(h * aspecto), h: Math.round(h) });
    };
    const ro = new ResizeObserver(medir);
    ro.observe(el);
    window.addEventListener("resize", medir);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", medir);
    };
  }, [aspecto]);

  // --- la cámara y el encuadre. La caja del sujeto se mide sobre TODOS los
  //     cuadros y con la focal base: así la figura entra entera en cualquier
  //     cuadro de la repetición, no cambia de tamaño al reproducir, y la rueda
  //     sigue acercando (el zoom multiplica el encuadre, no lo recalcula).
  const m = useMemo(() => marcoCamara(posicionDe(base.objetivo, base.distancia, { az: camino.az, el: camino.el, f: base.camino.f }), base.objetivo), [base, camino.az, camino.el]);
  const caja = useMemo(() => cajaDelSujeto(d.puntos, m, base.camino.f), [d.puntos, m, base.camino.f]);
  const enc = useMemo(() => {
    const W = tamano?.w ?? 0;
    const H = tamano?.h ?? 0;
    const mx = Math.max(MARGEN.xMin, Math.min(MARGEN.xMax, W * MARGEN.x));
    const my = Math.max(MARGEN.yMin, Math.min(MARGEN.yMax, H * MARGEN.y));
    return encuadreDe(caja, W, H, mx, my, camino.f / base.camino.f);
  }, [caja, tamano, camino.f, base.camino.f]);
  /** El archivo trae ángulos, o es de antes de que existieran. */
  const angulos: Angulos3D | null = useMemo(
    () => (d.angulos && d.angulos_3d && d.angulos_proyectados ? { doc: d.angulos, tres_d: d.angulos_3d, proyectados: d.angulos_proyectados } : null),
    [d.angulos, d.angulos_3d, d.angulos_proyectados],
  );

  /** `null` salvo que la cámara esté exactamente en una vista del protocolo. */
  const vistaActual = useMemo(() => vistaDelProtocolo(camino, d.camaras), [camino, d.camaras]);

  // --- dibujo: cada cambio de cuadro o de ángulo repinta los 26 puntos
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !tamano) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.round(tamano.w * dpr);
    canvas.height = Math.round(tamano.h * dpr);
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, tamano.w, tamano.h);
    ctx.fillStyle = "#08080a";
    ctx.fillRect(0, 0, tamano.w, tamano.h);
    const pts = d.puntos[Math.min(d.frames - 1, Math.max(0, cuadro))];
    if (!pts) return;
    const e: Escena = { ctx, W: tamano.w, H: tamano.h, enc, f: camino.f, m };
    ctx.lineCap = "round";
    dibujarGrilla(e);
    dibujarEsqueleto(e, d, pts, lateral);
    if (verAngulos && angulos) dibujarAngulos(e, d, angulos, pts, Math.min(d.frames - 1, Math.max(0, cuadro)), vistaActual);
  }, [d, cuadro, camino.f, tamano, lateral, enc, m, verAngulos, vistaActual, angulos]);

  // --- reproducción: el tiempo real manda, no el conteo de cuadros dibujados
  useEffect(() => {
    if (!reproduciendo) return;
    const t0 = performance.now();
    const desde = cuadroRef.current >= d.frames - 1 ? 0 : cuadroRef.current;
    let raf = 0;
    const paso = (t: number) => {
      const n = desde + Math.floor(((t - t0) / 1000) * d.fps * velocidad);
      if (n >= d.frames - 1) {
        setCuadro(d.frames - 1);
        setReproduciendo(false);
        return;
      }
      setCuadro(n);
      raf = requestAnimationFrame(paso);
    };
    raf = requestAnimationFrame(paso);
    return () => cancelAnimationFrame(raf);
  }, [reproduciendo, velocidad, d.fps, d.frames]);

  // --- girar y acercar
  const onPointerDown = (ev: React.PointerEvent<HTMLDivElement>) => {
    if (ev.button !== 0) return;
    arrastreRef.current = { x: ev.clientX, y: ev.clientY, az: camino.az, el: camino.el };
    ev.currentTarget.setPointerCapture(ev.pointerId);
  };
  const onPointerMove = (ev: React.PointerEvent<HTMLDivElement>) => {
    const a = arrastreRef.current;
    if (!a) return;
    setCamino((c) => ({ ...c, az: a.az - (ev.clientX - a.x) * 0.4, el: Math.min(85, Math.max(-85, a.el + (ev.clientY - a.y) * 0.3)) }));
  };
  const soltar = (ev: React.PointerEvent<HTMLDivElement>) => {
    arrastreRef.current = null;
    ev.currentTarget.releasePointerCapture?.(ev.pointerId);
  };

  useEffect(() => {
    const caja = cajaRef.current;
    if (!caja) return;
    const onWheel = (ev: WheelEvent) => {
      ev.preventDefault();
      setCamino((c) => ({ ...c, f: Math.min(base.camino.f * F_MAX, Math.max(base.camino.f * F_MIN, c.f * Math.exp(-ev.deltaY * 0.0015))) }));
    };
    caja.addEventListener("wheel", onWheel, { passive: false });
    return () => caja.removeEventListener("wheel", onWheel);
  }, [base.camino.f]);

  const irA = useCallback(
    (n: number) => {
      setReproduciendo(false);
      setCuadro(Math.min(d.frames - 1, Math.max(0, Math.round(n))));
    },
    [d.frames],
  );

  /** La cámara exactamente en los extrínsecos del protocolo de esa vista. */
  const comoVista = (vista: string) => {
    const cam = d.camaras[vista];
    if (cam) setCamino(caminoDe(cam).camino);
  };

  // El teclado se maneja en el propio recuadro y no en `window`: el reproductor
  // de arriba escucha ahí, y las flechas moverían los dos a la vez.
  const onKeyDown = (ev: React.KeyboardEvent<HTMLDivElement>) => {
    const paso = ev.shiftKey ? 10 : 1;
    if (ev.key === "ArrowLeft") irA(cuadro - paso);
    else if (ev.key === "ArrowRight") irA(cuadro + paso);
    else if (ev.key === " ") setReproduciendo((r) => !r);
    else if (ev.key === "Home") irA(0);
    else if (ev.key === "End") irA(d.frames - 1);
    else return;
    ev.preventDefault();
    ev.stopPropagation();
  };

  // --- el indicador, en el cuadro y el ángulo que se están viendo
  const pts = d.puntos[Math.min(d.frames - 1, Math.max(0, cuadro))] ?? [];
  const fracciones = Object.entries(d.indicador.lineas).map(([nombre, par]) => {
    const a = d.nombres.indexOf(par[0]);
    const b = d.nombres.indexOf(par[1]);
    return { nombre, frac: a >= 0 && b >= 0 ? fraccionProyectada(pts, a, b, m, camino.f) : null };
  });
  const colapsada = fracciones.some((f) => f.frac !== null && f.frac < d.indicador.umbral_colapso_frac);
  const enEvento = Object.entries(eventos).find(([, f]) => f === cuadro)?.[0];
  const ultimo = d.frames - 1;

  return (
    <div className="flex select-none flex-col gap-2">
      {/* Qué es esto: UNA línea a la vista y el argumento entero detrás de un
          desplegable. Antes iban los tres párrafos siempre abiertos y el texto
          ocupaba más alto que la figura (encargo 23). Las frases vienen del
          archivo, escritas por quien produjo el dato: acá no se compone
          ninguna, y el desplegable no recorta nada del argumento. */}
      <details className="rounded-lg border border-emerald-900 bg-emerald-950/30 px-3 py-2 text-sm">
        <summary className="cursor-pointer text-emerald-200 marker:text-emerald-600">
          {d.rotulos.resumen} <span className="text-amber-200 underline decoration-dotted">por qué esto no se puede hacer con un celular</span>
        </summary>
        <p className="mt-2 text-zinc-300">{d.rotulos.fuente}</p>
        <p className="mt-1 text-zinc-300">{d.rotulos.no_es_video}</p>
        <p className="mt-1 text-amber-200">{d.rotulos.no_con_un_celular}</p>
        <p className="mt-1 text-zinc-400">{d.rotulos.para_que_sirve}</p>
        <p className="mt-1 text-zinc-400">{d.rotulos.descriptivo}</p>
      </details>

      <div className="flex w-full justify-center">
        <div
          ref={cajaRef}
          tabIndex={0}
          className="relative overflow-hidden rounded-lg bg-black outline-none focus:ring-1 focus:ring-sky-700"
          style={{ width: tamano?.w ?? "100%", height: tamano?.h ?? 320, cursor: "grab", touchAction: "none" }}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={soltar}
          onPointerCancel={soltar}
          onKeyDown={onKeyDown}
        >
          <canvas ref={canvasRef} className="absolute inset-0" style={{ width: tamano?.w ?? "100%", height: tamano?.h ?? 320 }} />
          {/* El rótulo de la fuente arriba y el ángulo ABAJO: en un panel
              angosto el canvas mide ~320 px y los dos arriba se superponen. */}
          <div className="pointer-events-none absolute left-2 right-2 top-2 rounded bg-black/60 px-2 py-0.5 text-xs text-zinc-300">
            mocap CMU {d.trial} · marcadores ópticos · no es video
          </div>
          <div className="pointer-events-none absolute bottom-2 right-2 rounded bg-black/60 px-2 py-0.5 text-right text-xs tabular-nums text-zinc-300">
            azimut {fmt(camino.az, 0, true)}° · elevación {fmt(camino.el, 0, true)}°
            <span className="block text-zinc-500">0° = face_on · −90° = down_the_line</span>
          </div>
        </div>
      </div>

      {/* La capa de ángulos: su interruptor, su rótulo —permanente mientras la
          capa está prendida (punto 7 del encargo)— y, en las dos vistas del
          protocolo, qué quiere decir el segundo número. */}
      <div className="rounded-lg border border-zinc-800 p-3 text-sm">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span className="text-zinc-400">capas</span>
          <button
            type="button"
            className={`${btn} ${verAngulos && angulos ? "border-yellow-600 text-yellow-300" : "text-zinc-400"}`}
            aria-pressed={verAngulos}
            disabled={!angulos}
            onClick={() => setVerAngulos((v) => !v)}
            title={angulos ? "el número de cada ángulo al lado de su articulación" : "este archivo es anterior a la capa de ángulos"}
          >
            {verAngulos && angulos ? "☑" : "☐"} ángulos
          </button>
          {!angulos && <span className="text-xs text-zinc-500">este pose3d.json es anterior a la capa de ángulos ({d.schema}): hay que volver a generar el ejemplo.</span>}
          {verAngulos &&
            angulos &&
            (vistaActual ? (
              <span className="text-xs" style={{ color: COLOR_PROYECTADO }}>
                {angulos.doc.texto_comparacion} Cámara en <strong>{vistaActual}</strong>.
              </span>
            ) : (
              <span className="text-xs text-zinc-500">girá hasta una de las dos vistas del protocolo y al lado de cada ángulo aparece también lo que mediría una cámara puesta ahí.</span>
            ))}
        </div>
        {verAngulos && angulos && <p className="mt-1 text-xs text-amber-200">{angulos.doc.rotulo}</p>}
      </div>

      {/* El indicador: permanente, descriptivo, sin comparar contra nada. */}
      <div className="rounded-lg border border-zinc-800 p-3 text-sm">
        <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
          <span className="text-zinc-400">largo en la imagen, desde este ángulo, en el cuadro {cuadro}:</span>
          {fracciones.map(({ nombre, frac }) => (
            <span key={nombre} className="tabular-nums" style={{ color: COLOR_LINEA[nombre] ?? "#e4e4e7" }}>
              línea de {nombre} <strong>{frac === null ? "—" : `${fmt(frac * 100, 1)} %`}</strong>
            </span>
          ))}
        </div>
        <p className="mt-1 text-xs text-zinc-500">{d.indicador.texto}</p>
        {colapsada && <p className="mt-1 text-amber-200">{d.indicador.texto_colapso}</p>}
      </div>

      {/* línea de tiempo, con las marcas de evento debajo: la misma del reproductor */}
      <div className="relative pb-5 pt-1">
        <input
          type="range"
          className="linea-de-tiempo block"
          style={{ width: "calc(100% - 14px)", marginLeft: 7 }}
          min={0}
          max={ultimo}
          step={1}
          value={cuadro}
          onChange={(ev) => irA(Number(ev.target.value))}
          aria-label="línea de tiempo del swing 3-D, un paso por cuadro"
        />
        {Object.entries(eventos).map(([k, f]) => (
          <button
            key={k}
            type="button"
            onClick={() => irA(f)}
            className="absolute top-5 -translate-x-1/2 text-[11px] leading-none"
            style={{ left: `calc(7px + (100% - 14px) * ${ultimo > 0 ? f / ultimo : 0})`, color: COLOR_EVENTO[k as keyof typeof COLOR_EVENTO] ?? "#a1a1aa" }}
            title={`${EVENTOS[k] ?? k} · cuadro ${f}`}
          >
            ▲ {EVENTOS[k] ?? k}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button type="button" className={btn} onClick={() => irA(cuadro - 1)} title="un cuadro atrás">
          ◀ cuadro
        </button>
        <button type="button" className={`${btn} min-w-28`} onClick={() => setReproduciendo((r) => !r)}>
          {reproduciendo ? "⏸ pausa" : "▶ reproducir"}
        </button>
        <button type="button" className={btn} onClick={() => irA(cuadro + 1)} title="un cuadro adelante">
          cuadro ▶
        </button>
        <label className="ml-2 flex items-center gap-1 text-sm">
          velocidad
          <select className="rounded border border-zinc-700 bg-zinc-900 px-1 py-1" value={velocidad} onChange={(ev) => setVelocidad(Number(ev.target.value))}>
            {VELOCIDADES.map((v) => (
              <option key={v} value={v}>
                {String(v).replace(".", ",")}×
              </option>
            ))}
          </select>
        </label>
        {Object.keys(eventos).length > 0 && (
          <span className="ml-2 flex items-center gap-1 text-sm">
            ir a
            {Object.entries(eventos).map(([k, f]) => (
              <button key={k} type="button" className={btn} style={{ borderColor: COLOR_EVENTO[k as keyof typeof COLOR_EVENTO] ?? undefined }} onClick={() => irA(f)}>
                {EVENTOS[k] ?? k}
              </button>
            ))}
          </span>
        )}
        <span className="ml-auto font-mono text-sm tabular-nums">
          cuadro {cuadro} / {ultimo} · {fmt(cuadro / d.fps, 3)} s
          {enEvento && <span style={{ color: COLOR_EVENTO[enEvento as keyof typeof COLOR_EVENTO] }}> · {(EVENTOS[enEvento] ?? enEvento).toUpperCase()}</span>}
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-zinc-400">ver como</span>
        {Object.keys(d.camaras).map((vista) => (
          <button key={vista} type="button" className={btn} onClick={() => comoVista(vista)} title={`la cámara exactamente donde la pone el protocolo para ${vista}`}>
            {vista}
          </button>
        ))}
        <button type="button" className={btn} onClick={() => setCamino((c) => ({ ...c, f: base.camino.f }))} disabled={Math.abs(camino.f - base.camino.f) < 1} title="volver al zoom de arranque: la focal del protocolo, con la figura entera adentro del recuadro">
          1:1
        </button>
        <span className="text-xs text-zinc-500">desde esas dos posiciones la escena es la misma proyección que el video con los palitos de esa vista, encuadrada para que el sujeto entre entero en todos los cuadros (agrandar o correr una imagen no le cambia ningún ángulo)</span>
      </div>

      <p className="text-xs text-zinc-500">
        arrastrar: girar · rueda: acercar (es zoom, la cámara no se mueve) · clic en la escena y después ← → : cuadro a cuadro, shift + flecha: 10 cuadros, espacio: reproducir. {d.rotulos.para_que_sirve}
      </p>
      <details className="text-xs text-zinc-500">
        <summary className="cursor-pointer text-zinc-400">de dónde sale cada número</summary>
        <p className="mt-1">
          Marco <code>{d.marco.id}</code>, en {d.marco.unidades}: origen {d.marco.origen}; x {d.marco.ejes.x}, y {d.marco.ejes.y}, z {d.marco.ejes.z} ({d.marco.mano}).
        </p>
        <p className="mt-1">{d.suelo.nota} Medido en este swing: {fmt(d.suelo.pies_sobre_el_cero_en_el_cuadro_de_referencia_m * 100, 1)} cm.</p>
        <p className="mt-1">
          {d.frames} cuadros · {d.fps_nota} Estatura del esqueleto {fmt(d.estatura_m, 3)} m. {d.eventos ? "Los eventos marcados son los que detectó el motor sobre la proyección de esta vista." : "Este archivo no trae los eventos del motor."}
        </p>
        <p className="mt-1">
          El indicador: {d.indicador.definicion} {d.indicador.medido}
        </p>
        {angulos && (
          <>
            <p className="mt-1">
              Los ángulos, en {angulos.doc.unidad}: el de arriba se mide en 3-D sobre {angulos.doc.marco_3d} ({angulos.doc.procedencia_3d}); el de abajo, sobre {angulos.doc.marco_proyectado} ({angulos.doc.procedencia_proyectado}). {angulos.doc.nota_diferencia} {angulos.doc.nota_respecto_de}
            </p>
            <p className="mt-1">{angulos.doc.nota_nivel}</p>
            <ul className="mt-1 list-disc pl-4">
              {Object.entries(angulos.doc.definiciones).map(([nombre, def]) => (
                <li key={nombre}>
                  <span className="text-zinc-400">{def.etiqueta}</span> (<code>{nombre}</code>): {def.definicion} Proyectado: {def.proyectado}
                </li>
              ))}
            </ul>
          </>
        )}
        <p className="mt-1">{d.indicador.que_mide}. {d.rotulos.descriptivo}</p>
        <p className="mt-1">{d.atribucion}</p>
      </details>
    </div>
  );
}
