"use client";

import { useState, type FormEvent } from "react";

interface Props {
  ocupado: boolean;
  onSubir: (archivo: File, alturaM: number | null) => void;
}

export default function Subida({ ocupado, onSubir }: Props) {
  const [archivo, setArchivo] = useState<File | null>(null);
  const [altura, setAltura] = useState("");
  const [error, setError] = useState<string | null>(null);

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
      <button type="submit" disabled={ocupado || !archivo} className="rounded bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500 disabled:opacity-40">
        Subir video
      </button>
      {error && <span className="text-sm text-red-300">{error}</span>}
      <span className="basis-full text-xs text-zinc-500">Sin altura, los desplazamientos y la velocidad de las manos quedan sólo en % de la altura del cuerpo, no en cm.</span>
    </form>
  );
}
