"use client";

// Reproductor propio sobre <video> + requestVideoFrameCallback (ADR-014): pausa,
// arrastre con un paso por cuadro, cámara lenta 0,1×–1×, cuadro a cuadro en las
// dos direcciones y zoom con paneo. Sin librería: ninguna de las evaluadas
// (Video.js, Plyr, Vidstack, react-player) da cuadro a cuadro real; todas
// terminan en un seek a (n + 0,5) / fps, que es lo que se hace acá con la
// verificación del cuadro que llegó (`mediaTime`). Ver ESTADO.md.
//
// Provisorio: hoy reproduce `overlay.mp4` ya dibujado. El visor definitivo
// dibuja el esqueleto desde `pose.npz` en un canvas dentro de `marcoRef`, el
// mismo div que se transforma para el zoom (por eso el zoom no va en el <video>).

import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from "react";
import type { EventoId, Eventos } from "@/lib/api";
import { EVENTOS, fmt } from "@/lib/etiquetas";

export interface ReproductorHandle {
  irACuadro(n: number): void;
}

interface Props {
  src: string;
  fps: number;
  cuadros: number;
  eventos: Eventos;
  onCuadro?: (n: number) => void;
}

const VELOCIDADES = [0.1, 0.2, 0.25, 0.5, 0.75, 1];
const ZOOM_MAX = 4;
const ALTO_MAX = 0.78; // fracción del alto de la ventana
export const COLOR_EVENTO: Record<EventoId, string> = { address: "#facc15", top: "#38bdf8", impact: "#f87171", follow_end: "#a3e635" };

type MetaCuadro = { mediaTime: number };
type VideoRVFC = HTMLVideoElement & {
  requestVideoFrameCallback?: (cb: (now: number, meta: MetaCuadro) => void) => number;
  cancelVideoFrameCallback?: (handle: number) => void;
};

function acotar(x: number, y: number, z: number, w: number, h: number) {
  return { x: Math.min(0, Math.max(w - w * z, x)), y: Math.min(0, Math.max(h - h * z, y)) };
}

const btn = "rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-sm hover:bg-zinc-800 disabled:opacity-40";

const Reproductor = forwardRef<ReproductorHandle, Props>(function Reproductor({ src, fps, cuadros, eventos, onCuadro }, ref) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const cajaRef = useRef<HTMLDivElement>(null);
  const marcoRef = useRef<HTMLDivElement>(null);
  const pedidoRef = useRef<number | null>(null);
  const ultimoRef = useRef(-1);
  const onCuadroRef = useRef(onCuadro);
  const zoomRef = useRef(1);
  const panRef = useRef({ x: 0, y: 0 });
  const tamanoRef = useRef<{ w: number; h: number } | null>(null);
  const arrastreRef = useRef<{ x: number; y: number; px: number; py: number; movido: boolean } | null>(null);

  const [cuadro, setCuadro] = useState(0);
  const [reproduciendo, setReproduciendo] = useState(false);
  const [velocidad, setVelocidad] = useState(1);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [aviso, setAviso] = useState<string | null>(null);
  const [tamano, setTamano] = useState<{ w: number; h: number } | null>(null);
  const [aspecto, setAspecto] = useState<number | null>(null);

  useEffect(() => {
    onCuadroRef.current = onCuadro;
  }, [onCuadro]);

  // --- tamaño del recuadro: el alto lo limita la ventana, el ancho lo limita la columna ---
  useEffect(() => {
    if (aspecto === null) return;
    const el = cajaRef.current?.parentElement;
    if (!el) return;
    const medir = () => {
      const h = Math.max(160, Math.min(window.innerHeight * ALTO_MAX, el.clientWidth / aspecto));
      const w = h * aspecto;
      const t = { w: Math.round(w), h: Math.round(h) };
      tamanoRef.current = t;
      setTamano(t);
      const p = acotar(panRef.current.x, panRef.current.y, zoomRef.current, t.w, t.h);
      panRef.current = p;
      setPan(p);
    };
    const ro = new ResizeObserver(medir); // dispara una vez al observar
    ro.observe(el);
    window.addEventListener("resize", medir);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", medir);
    };
  }, [aspecto]);

  // --- el cuadro presentado, desde el mediaTime que el navegador dice haber mostrado ---
  useEffect(() => {
    const v = videoRef.current as VideoRVFC | null;
    if (!v) return;
    let vivo = true;
    const alCuadro = (mediaTime: number) => {
      const n = Math.min(cuadros - 1, Math.max(0, Math.round(mediaTime * fps)));
      if (n !== ultimoRef.current) {
        ultimoRef.current = n;
        setCuadro(n);
        onCuadroRef.current?.(n);
      }
      const pedido = pedidoRef.current;
      if (pedido !== null) {
        pedidoRef.current = null;
        setAviso(pedido === n ? null : `Pedí el cuadro ${pedido} y el navegador mostró el ${n}.`);
      }
    };
    if (typeof v.requestVideoFrameCallback === "function") {
      let handle = 0;
      const loop = (_now: number, meta: MetaCuadro) => {
        if (!vivo) return;
        alCuadro(meta.mediaTime);
        handle = v.requestVideoFrameCallback!(loop);
      };
      handle = v.requestVideoFrameCallback(loop);
      return () => {
        vivo = false;
        v.cancelVideoFrameCallback?.(handle);
      };
    }
    // Sin rVFC (no es Chrome): currentTime en timeupdate/seeked; puede ir un cuadro desfasado.
    const onT = () => alCuadro(v.currentTime);
    v.addEventListener("timeupdate", onT);
    v.addEventListener("seeked", onT);
    return () => {
      vivo = false;
      v.removeEventListener("timeupdate", onT);
      v.removeEventListener("seeked", onT);
    };
  }, [fps, cuadros, src]);

  useEffect(() => {
    const v = videoRef.current;
    if (v) v.playbackRate = velocidad;
  }, [velocidad, src]);

  const irACuadro = useCallback(
    (n: number) => {
      const v = videoRef.current;
      if (!v || cuadros <= 0) return;
      const m = Math.min(cuadros - 1, Math.max(0, Math.round(n)));
      v.pause();
      if (m === ultimoRef.current && Math.abs(v.currentTime - (m + 0.5) / fps) < 0.25 / fps) return;
      pedidoRef.current = m;
      v.currentTime = (m + 0.5) / fps; // el medio del cuadro m: nunca el borde entre dos
    },
    [cuadros, fps],
  );

  useImperativeHandle(ref, () => ({ irACuadro }), [irACuadro]);

  const alternar = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) {
      if (v.ended || ultimoRef.current >= cuadros - 1) v.currentTime = 0;
      void v.play();
    } else v.pause();
  }, [cuadros]);

  // --- zoom con paneo: el punto bajo el cursor se queda quieto ---
  const aplicarZoom = useCallback((nuevo: number, cx?: number, cy?: number) => {
    const t = tamanoRef.current;
    if (!t) return;
    const z0 = zoomRef.current;
    const z = Math.min(ZOOM_MAX, Math.max(1, nuevo));
    const px = cx ?? t.w / 2;
    const py = cy ?? t.h / 2;
    const p = acotar(px - (px - panRef.current.x) * (z / z0), py - (py - panRef.current.y) * (z / z0), z, t.w, t.h);
    zoomRef.current = z;
    panRef.current = p;
    setZoom(z);
    setPan(p);
  }, []);

  useEffect(() => {
    const caja = cajaRef.current;
    if (!caja) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const r = caja.getBoundingClientRect();
      aplicarZoom(zoomRef.current * Math.exp(-e.deltaY * 0.0015), e.clientX - r.left, e.clientY - r.top);
    };
    caja.addEventListener("wheel", onWheel, { passive: false });
    return () => caja.removeEventListener("wheel", onWheel);
  }, [aplicarZoom]);

  const onPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    arrastreRef.current = { x: e.clientX, y: e.clientY, px: panRef.current.x, py: panRef.current.y, movido: false };
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const a = arrastreRef.current;
    const t = tamanoRef.current;
    if (!a || !t) return;
    const dx = e.clientX - a.x;
    const dy = e.clientY - a.y;
    if (!a.movido && Math.hypot(dx, dy) < 4) return;
    a.movido = true;
    if (zoomRef.current <= 1) return;
    const p = acotar(a.px + dx, a.py + dy, zoomRef.current, t.w, t.h);
    panRef.current = p;
    setPan(p);
  };
  const onPointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    const a = arrastreRef.current;
    arrastreRef.current = null;
    e.currentTarget.releasePointerCapture(e.pointerId);
    if (a && !a.movido) alternar(); // un clic sin arrastre: reproducir / pausar
  };

  // --- teclado: flechas, espacio, zoom ---
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA" || tag === "BUTTON") return;
      const paso = e.shiftKey ? 10 : 1;
      switch (e.key) {
        case "ArrowLeft":
          irACuadro(ultimoRef.current - paso);
          break;
        case "ArrowRight":
          irACuadro(ultimoRef.current + paso);
          break;
        case "Home":
          irACuadro(0);
          break;
        case "End":
          irACuadro(cuadros - 1);
          break;
        case " ":
          alternar();
          break;
        case "+":
        case "=":
          aplicarZoom(zoomRef.current * 1.25);
          break;
        case "-":
          aplicarZoom(zoomRef.current / 1.25);
          break;
        case "0":
          aplicarZoom(1);
          break;
        default:
          return;
      }
      e.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [irACuadro, alternar, aplicarZoom, cuadros]);

  const evLista = (Object.keys(EVENTOS) as EventoId[]).filter((k) => eventos[k] !== undefined);
  const enEvento = evLista.find((k) => eventos[k] === cuadro);
  const ultimo = Math.max(0, cuadros - 1);

  return (
    <div className="flex select-none flex-col gap-2">
      <div className="flex w-full justify-center">
        <div
          ref={cajaRef}
          className="relative overflow-hidden rounded-lg bg-black"
          style={{ width: tamano?.w ?? "100%", height: tamano?.h ?? 320, cursor: zoom > 1 ? "grab" : "pointer", touchAction: "none" }}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={() => (arrastreRef.current = null)}
        >
          <div ref={marcoRef} className="absolute inset-0" style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`, transformOrigin: "0 0" }}>
            <video
              key={src}
              ref={videoRef}
              src={src}
              muted
              playsInline
              preload="auto"
              className="absolute inset-0 h-full w-full object-contain"
              onLoadedMetadata={(e) => {
                const v = e.currentTarget;
                if (v.videoWidth && v.videoHeight) setAspecto(v.videoWidth / v.videoHeight);
              }}
              onPlay={() => setReproduciendo(true)}
              onPause={() => setReproduciendo(false)}
            />
          </div>
          {zoom > 1 && <div className="pointer-events-none absolute right-2 top-2 rounded bg-black/60 px-2 py-0.5 text-xs">{fmt(zoom, 1)}× · arrastrá para mover</div>}
        </div>
      </div>

      {/* línea de tiempo: un paso por cuadro, con las marcas de evento debajo */}
      <div className="relative pb-5 pt-1">
        <input
          type="range"
          className="linea-de-tiempo block"
          style={{ width: "calc(100% - 14px)", marginLeft: 7 }}
          min={0}
          max={ultimo}
          step={1}
          value={cuadro}
          onChange={(e) => irACuadro(Number(e.target.value))}
          aria-label="línea de tiempo, un paso por cuadro"
        />
        {evLista.map((k) => {
          const f = eventos[k]!;
          const frac = ultimo > 0 ? f / ultimo : 0;
          return (
            <button
              key={k}
              type="button"
              onClick={() => irACuadro(f)}
              className="absolute top-5 -translate-x-1/2 text-[11px] leading-none"
              style={{ left: `calc(7px + (100% - 14px) * ${frac})`, color: COLOR_EVENTO[k] }}
              title={`${EVENTOS[k]} · cuadro ${f}`}
            >
              ▲ {EVENTOS[k]}
            </button>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button type="button" className={btn} onClick={() => irACuadro(cuadro - 1)} title="un cuadro atrás (←)">
          ◀ cuadro
        </button>
        <button type="button" className={`${btn} min-w-28`} onClick={alternar} title="espacio">
          {reproduciendo ? "⏸ pausa" : "▶ reproducir"}
        </button>
        <button type="button" className={btn} onClick={() => irACuadro(cuadro + 1)} title="un cuadro adelante (→)">
          cuadro ▶
        </button>
        <label className="ml-2 flex items-center gap-1 text-sm">
          velocidad
          <select className="rounded border border-zinc-700 bg-zinc-900 px-1 py-1" value={velocidad} onChange={(e) => setVelocidad(Number(e.target.value))}>
            {VELOCIDADES.map((v) => (
              <option key={v} value={v}>
                {String(v).replace(".", ",")}×
              </option>
            ))}
          </select>
        </label>
        <span className="ml-2 flex items-center gap-1 text-sm">
          zoom
          <button type="button" className={btn} onClick={() => aplicarZoom(zoomRef.current / 1.25)} disabled={zoom <= 1}>
            −
          </button>
          <span className="w-10 text-center tabular-nums">{fmt(zoom, 1)}×</span>
          <button type="button" className={btn} onClick={() => aplicarZoom(zoomRef.current * 1.25)} disabled={zoom >= ZOOM_MAX}>
            +
          </button>
          <button type="button" className={btn} onClick={() => aplicarZoom(1)} disabled={zoom <= 1}>
            1:1
          </button>
        </span>
        <span className="ml-2 flex items-center gap-1 text-sm">
          ir a
          {evLista.map((k) => (
            <button key={k} type="button" className={btn} style={{ borderColor: COLOR_EVENTO[k] }} onClick={() => irACuadro(eventos[k]!)}>
              {EVENTOS[k]}
            </button>
          ))}
        </span>
        <span className="ml-auto font-mono text-sm tabular-nums">
          cuadro {cuadro} / {ultimo} · {fmt(cuadro / fps, 3)} s{enEvento && <span style={{ color: COLOR_EVENTO[enEvento] }}> · {EVENTOS[enEvento].toUpperCase()}</span>}
        </span>
      </div>
      {aviso && <p className="text-xs text-amber-300">{aviso}</p>}
      <p className="text-xs text-zinc-500">← → cuadro a cuadro · shift + flecha: 10 cuadros · espacio o clic en el video: reproducir / pausar · rueda sobre el video o + −: zoom · arrastrar: mover · 0: sin zoom</p>
    </div>
  );
});

export default Reproductor;
