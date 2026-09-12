# kinelab

Motor de medición del movimiento humano a partir de video de celular. Para un
entrenador, en su Mac, sin nube. Agnóstico al deporte; golf primero.

**Empezá por [`AGENTS.md`](AGENTS.md).** Dice qué leer, en qué orden, y cuáles
son las reglas de trabajo. Los seis documentos que enumera son la fuente de
verdad; `ESTADO.md` dice dónde quedó el trabajo.

```bash
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev,service]"
.venv/bin/pytest -q
```

## Interfaz de exploración (subir un video → palitos + toda la data)

Dos procesos, en dos terminales. La primera vez, en `web/`: `pnpm install`
(Node 22+, pnpm).

```bash
.venv/bin/python -m service          # backend FastAPI en http://127.0.0.1:8765
```

```bash
cd web && pnpm dev                   # frontend Next.js en http://localhost:3000
```

Abrir http://localhost:3000. Una pantalla: elegir el video, la altura del
atleta en metros (opcional: sin ella no hay centímetros), «Subir video». Se ve
el progreso (subiendo → cargando el modelo → detectando la pose → calculando →
dibujando) y al terminar:

- arriba, el video con los palitos en un reproductor con pausa, arrastre con
  un paso por cuadro, velocidad 0,1×–1×, cuadro a cuadro en las dos direcciones
  (flechas), zoom hasta 4× con la rueda o los botones y paneo arrastrando;
- las fotos de address, top e impacto (clic: ese cuadro en el reproductor);
- toda la data por evento en tablas, duraciones, picos, diferencias contra el
  address, y la tabla completa por cuadro con filtro de columnas y descarga
  del CSV, del JSON y del video.

El frontend habla con el backend por `/api/*` (proxy en `web/next.config.ts`),
así que no hace falta CORS. Los trabajos quedan en `data/exploracion/<id>/`
(ignorado por git); el último se vuelve a mostrar al recargar la página.

Lo mismo sin interfaz: `.venv/bin/python -m kinelab datos VIDEO.mp4 --altura-m 1.75`.

El modo exploración corre sin gate y sin MDC: son números descriptivos para
mirar, no para juzgar. Y reproducir el `overlay.mp4` ya dibujado es un paso
provisorio (contradice la invariante 10 de `CONTEXTO.md`); el visor definitivo
dibuja desde `pose.npz` sobre el video original.

Nombre provisorio. Cambiarlo es un `sed`.
