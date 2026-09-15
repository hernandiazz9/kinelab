"use client";

// Los dos cuadros entre los que cayó el impacto, lado a lado. El motor estima el
// instante ENTRE ellos (`eventos_subcuadro`): entre uno y el otro no hay nada
// filmado, así que lo único honesto es mostrar los dos y decir dónde cae la cuenta.
// Sin interpolar nada: eso es otro trabajo y va rotulado aparte.
//
// Cada cuadro es un <video> pausado en (n + 0,5) / fps —el medio del cuadro, nunca el
// borde— y, si el navegador tiene `requestVideoFrameCallback`, se verifica cuál
// mostró con el `mediaTime`, igual que en el Reproductor.
//
// `primerCuadro`: el cuadro del ORIGEN que es el t=0 del archivo (0 salvo que el
// archivo sea un recorte al tramo; ver Reproductor.tsx). Los números que se muestran
// son los del origen, siempre.

import { useEffect, useRef, useState } from "react";
import { fmt } from "@/lib/etiquetas";

type MetaCuadro = { mediaTime: number };
type VideoRVFC = HTMLVideoElement & {
  requestVideoFrameCallback?: (cb: (now: number, meta: MetaCuadro) => void) => number;
  cancelVideoFrameCallback?: (handle: number) => void;
};

function Cuadro({ src, fps, n, primerCuadro, nota, resaltar }: { src: string; fps: number; n: number; primerCuadro: number; nota: string; resaltar: boolean }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [llego, setLlego] = useState<number | null>(null);

  useEffect(() => {
    const v = videoRef.current as VideoRVFC | null;
    if (!v) return;
    let vivo = true;
    let handle = 0;
    const marcar = (mediaTime: number) => {
      if (vivo) setLlego(primerCuadro + Math.round(mediaTime * fps));
    };
    const ir = () => {
      v.currentTime = (n - primerCuadro + 0.5) / fps;
      if (typeof v.requestVideoFrameCallback === "function") handle = v.requestVideoFrameCallback((_now, meta) => marcar(meta.mediaTime));
    };
    const alSeek = () => {
      if (typeof v.requestVideoFrameCallback !== "function") marcar(v.currentTime);
    };
    if (v.readyState >= 1) ir();
    else v.addEventListener("loadedmetadata", ir, { once: true });
    v.addEventListener("seeked", alSeek);
    return () => {
      vivo = false;
      v.cancelVideoFrameCallback?.(handle);
      v.removeEventListener("loadedmetadata", ir);
      v.removeEventListener("seeked", alSeek);
    };
  }, [src, fps, n, primerCuadro]);

  return (
    <figure className="min-w-0">
      <div className={`overflow-hidden rounded-lg border bg-black ${resaltar ? "border-red-500" : "border-zinc-800"}`}>
        <video ref={videoRef} src={src} muted playsInline preload="auto" className="mx-auto max-h-[60vh] w-full object-contain" />
      </div>
      <figcaption className="mt-1 text-center text-sm">
        cuadro {n} · {fmt(n / fps, 3)} s<span className="block text-xs text-zinc-400">{nota}</span>
        {llego !== null && llego !== n && <span className="block text-xs text-amber-300">el navegador mostró el cuadro {llego}</span>}
      </figcaption>
    </figure>
  );
}

export default function DosCuadros({ src, fps, antes, despues, fraccion, primerCuadro = 0 }: { src: string; fps: number; antes: number; despues: number; fraccion: number | null; primerCuadro?: number }) {
  const pct = fraccion === null ? null : Math.round(fraccion * 100);
  return (
    <div className="rounded-lg border border-zinc-800 p-3">
      <p className="mb-2 text-sm text-zinc-300">
        Entre estos dos cuadros no hay nada filmado: a {fmt(fps, 3)} fps pasan {fmt(1000 / fps, 1)} ms entre uno y el otro.
        {pct !== null && ` El impacto estimado cae a ${pct} % del camino, más cerca del cuadro ${pct < 50 ? antes : despues}.`}
      </p>
      <div className="grid grid-cols-2 gap-3">
        <Cuadro src={src} fps={fps} n={antes} primerCuadro={primerCuadro} nota="antes del instante estimado" resaltar={pct !== null && pct < 50} />
        <Cuadro src={src} fps={fps} n={despues} primerCuadro={primerCuadro} nota="después del instante estimado" resaltar={pct !== null && pct >= 50} />
      </div>
    </div>
  );
}
