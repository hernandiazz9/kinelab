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
import { caminoDe, fraccionProyectada, marcoCamara, posicionDe, proyectar, type Camino, type Pose3D, type V3 } from "@/lib/pose3d";

// --- dibujo -------------------------------------------------------------------

const IZQ = "#50dc50"; // los mismos colores del overlay (`kinelab/explore.py`)
const DER = "#ff8c3c";
const CENTRO = "#d4d4d8";
const COLOR_LINEA: Record<string, string> = { caderas: "#f0abfc", hombros: "#67e8f9" };
const GRILLA = { paso: 0.5, alcance: 1.5 };
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
  s: number;
  f: number;
  m: { R: [V3, V3, V3]; posicion: V3 };
}

function segmento(e: Escena, a: V3, b: V3, color: string, ancho: number): void {
  const pa = proyectar(a, e.m, e.f, e.s, e.W, e.H);
  const pb = proyectar(b, e.m, e.f, e.s, e.W, e.H);
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
    const q = proyectar(p, e.m, e.f, e.s, e.W, e.H);
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
    .map(([a, b], i) => ({ i, z: (proyectar(pts[a] as V3, e.m, e.f, 1, 0, 0).z + proyectar(pts[b] as V3, e.m, e.f, 1, 0, 0).z) / 2 }))
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
    const q = proyectar(p as V3, e.m, e.f, e.s, e.W, e.H);
    if (q.z <= 0.05) continue;
    e.ctx.fillStyle = "#fafafa";
    e.ctx.beginPath();
    e.ctx.arc(q.u, q.v, r, 0, Math.PI * 2);
    e.ctx.fill();
  }
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
    const e: Escena = {
      ctx,
      W: tamano.w,
      H: tamano.h,
      s: tamano.w / (d.camaras[d.vista_del_trabajo]?.ancho ?? 1080),
      f: camino.f,
      m: marcoCamara(posicionDe(base.objetivo, base.distancia, camino), base.objetivo),
    };
    ctx.lineCap = "round";
    dibujarGrilla(e);
    dibujarEsqueleto(e, d, pts, lateral);
  }, [d, cuadro, camino, tamano, base, lateral]);

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
  const m = marcoCamara(posicionDe(base.objetivo, base.distancia, camino), base.objetivo);
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
      {/* Los rótulos, primero y siempre: qué es esto y qué no es. Las frases
          vienen del archivo, escritas por quien produjo el dato. */}
      <div className="rounded-lg border border-emerald-900 bg-emerald-950/30 p-3 text-sm">
        <p className="text-emerald-200">{d.rotulos.fuente}</p>
        <p className="mt-1 text-zinc-300">{d.rotulos.no_es_video}</p>
        <p className="mt-1 text-amber-200">{d.rotulos.no_con_un_celular}</p>
      </div>

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
          <div className="pointer-events-none absolute left-2 top-2 rounded bg-black/60 px-2 py-0.5 text-xs text-zinc-300">
            mocap CMU {d.trial} · marcadores ópticos · no es video
          </div>
          <div className="pointer-events-none absolute right-2 top-2 rounded bg-black/60 px-2 py-0.5 text-right text-xs tabular-nums text-zinc-300">
            azimut {fmt(camino.az, 0, true)}° · elevación {fmt(camino.el, 0, true)}°
            <span className="block text-zinc-500">0° = face_on · −90° = down_the_line</span>
          </div>
        </div>
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
        <button type="button" className={btn} onClick={() => setCamino((c) => ({ ...c, f: base.camino.f }))} disabled={Math.abs(camino.f - base.camino.f) < 1}>
          1:1
        </button>
        <span className="text-xs text-zinc-500">desde esas dos posiciones la escena se ve como el video con los palitos de esa vista</span>
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
        <p className="mt-1">{d.indicador.que_mide}. {d.rotulos.descriptivo}</p>
        <p className="mt-1">{d.atribucion}</p>
      </details>
    </div>
  );
}
