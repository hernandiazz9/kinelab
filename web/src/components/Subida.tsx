"use client";

// Subir un video: el archivo, la altura del atleta y CON QUÉ SE FILMÓ.
//
// El camino de captura no es un detalle de formulario: es lo que decide si el
// eje del tiempo está medido o supuesto (ADR-016). Se elige antes de subir, se
// recuerda (el teléfono no cambia entre clips) y el default es el genérico
// "no sé", que analiza igual y deja el supuesto escrito.

import { useEffect, useState, type FormEvent } from "react";
import { CAMINO_DESCONOCIDO, caminoRecordado, getConfig, type CaminoCaptura } from "@/lib/api";
import { etiquetaCamino } from "@/lib/etiquetas";

interface Props {
  ocupado: boolean;
  camino: string;
  onCamino: (id: string) => void;
  onSubir: (archivo: File, alturaM: number | null) => void;
}

export default function Subida({ ocupado, camino, onCamino, onSubir }: Props) {
  const [archivo, setArchivo] = useState<File | null>(null);
  const [altura, setAltura] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [caminos, setCaminos] = useState<CaminoCaptura[]>([]);
  const [errorCaminos, setErrorCaminos] = useState<string | null>(null);

  // Un Slo-Mo sin cronómetro no se puede analizar: el factor de estiramiento es
  // desconocido y cualquier tiempo sería ficción (ADR-016). Se lista igual,
  // deshabilitado, para que se vea que existe y por qué todavía no sirve.
  const sinCronometro = (c: CaminoCaptura) => !c.calibrated && c.mode === "slomo";

  // El camino recordado se confirma acá y no antes: recién con la lista del
  // backend se sabe si el que quedó en `localStorage` sigue existiendo. Uno que
  // ya no está se ignora en silencio y queda el genérico, en vez de mandar una
  // subida que el backend va a rechazar con un 400.
  useEffect(() => {
    getConfig()
      .then((c) => {
        setCaminos(c.capture_paths);
        const guardado = caminoRecordado();
        const valido = c.capture_paths.find((p) => p.id === guardado && !sinCronometro(p));
        if (valido) onCamino(valido.id);
      })
      .catch((e: Error) => setErrorCaminos(e.message));
  }, [onCamino]);

  const enviar = (e: FormEvent) => {
    e.preventDefault();
    if (!archivo) {
      setError("Elegí un video primero.");
      return;
    }
    let a: number | null = null;
    if (altura.trim()) {
      a = Number(altura.trim().replace(",", "."));
      if (!Number.isFinite(a) || a < 0.5 || a > 2.6) {
        setError("La altura va en metros, entre 0,5 y 2,6 (por ejemplo 1,75).");
        return;
      }
    }
    setError(null);
    onSubir(archivo, a);
  };

  const elegido = caminos.find((c) => c.id === camino);

  return (
    <form onSubmit={enviar} className="flex flex-wrap items-end gap-3">
      <label className="flex flex-col gap-1 text-sm">
        video del swing
        <input
          type="file"
          accept="video/*,.mov,.mp4,.m4v"
          disabled={ocupado}
          onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
          className="block max-w-xs text-sm file:mr-3 file:rounded file:border-0 file:bg-zinc-800 file:px-3 file:py-1.5 file:text-zinc-100 hover:file:bg-zinc-700"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        altura del atleta (m, opcional)
        <input
          type="text"
          inputMode="decimal"
          placeholder="1,75"
          value={altura}
          disabled={ocupado}
          onChange={(e) => setAltura(e.target.value)}
          className="w-28 rounded border border-zinc-700 bg-zinc-900 px-2 py-1.5"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        ¿con qué se filmó?
        <select
          value={camino}
          disabled={ocupado || caminos.length === 0}
          onChange={(e) => onCamino(e.target.value)}
          className="max-w-xs rounded border border-zinc-700 bg-zinc-900 px-2 py-1.5 disabled:opacity-40"
        >
          {caminos.length === 0 && <option value={camino}>{errorCaminos ? "no se pudo leer capture-paths.yaml" : "cargando…"}</option>}
          {caminos.map((c) => (
            <option key={c.id} value={c.id} disabled={sinCronometro(c)}>
              {etiquetaCamino(c)}
              {sinCronometro(c) && " — hace falta el cronómetro"}
            </option>
          ))}
        </select>
      </label>
      <button type="submit" disabled={ocupado || !archivo} className="rounded bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500 disabled:opacity-40">
        Subir video
      </button>
      {error && <span className="text-sm text-red-300">{error}</span>}
      {errorCaminos && <span className="text-sm text-red-300">No se pudieron leer los caminos de captura: {errorCaminos}</span>}
      <span className="basis-full text-xs text-zinc-500">
        Sin altura, los desplazamientos y la velocidad de las manos quedan sólo en % de la altura del cuerpo, no en cm.
        {elegido && !elegido.calibrated && (
          <>
            {" "}Con un camino {elegido.id === CAMINO_DESCONOCIDO ? "desconocido" : "declarado"} y sin cronómetro filmado, la tasa de cuadros del archivo se asume igual a la de captura: los
            tiempos son descriptivos y ninguna métrica puede ser juicio.
          </>
        )}
      </span>
    </form>
  );
}
