# 09 — Ficha del archivo, selector de camino, y el aviso antes de cualquier número

Para correr: `/encargo 09` en una sesión nueva. Leé antes los informes del
04, 06 y 08 en `docs/informes/`.

## Contexto

Hernán sube clips del Galaxy S22 o de donde sea. ADR-016 (encargo 06) deja
declarar el camino de captura sin cronómetro: el motor marca cada número como
`sin_verificar` y no hay juicio. La regla del ADR es que ese aviso se lea
**antes** de cualquier número. Y desde el 04 el motor corrige el fps cuando el
primer delta de PTS es el arranque de la cámara (`fps_note` en
`capture.json`), y la pantalla no lo dice en ningún lado. Esta pantalla sigue
siendo la de mirar datos: sin atletas, sesiones ni gate.

Leer: `service/app.py` (`PUT /api/fps-truth`, `GET /api/config`,
`PUT /api/datos`), `service/exploracion.py`, `kinelab/explore.py` (la firma
de `explore()` con `camino`, las etapas, y qué escribe en
`datos-eventos.json`: `camino`, `camino_calibrado`, `fps_provenance`,
`fps_aviso`), `kinelab/tools/fps_truth.py` (`to_dict()`),
`data/capture-paths.yaml`, `web/src/app/page.tsx`,
`web/src/components/Subida.tsx`, `ListaTrabajos.tsx`, `TablaEventos.tsx`,
`web/src/lib/api.ts`, `tests/test_service.py`.

## Qué existe ya

- `PUT /api/fps-truth` devuelve el `to_dict()` de `fps_truth`: codec, tamaño,
  rotación, cuadros, fps bruto y efectivo, ratio bruto y sin el primer delta,
  `delta_first_s`, la nota.
- `GET /api/config` lista los caminos de `capture-paths.yaml` con
  `calibrated`. Hoy hay tres declarados: `desconocido-video`,
  `s22ultra-video-fhd60-cable`, `s22ultra-video-fhd30-cable`.
- `python -m kinelab datos VIDEO --camino ID` (default `desconocido-video`).
  `analysis.json` (archivo del trabajo) lleva `warnings[0]` con el aviso y
  cada una de las 12 métricas con `null_reason` y `fps_provenance`.
  `capture.json` (archivo del trabajo) lleva `fps_note`.
- La lista de trabajos del 08, `?trabajo=`, y la forma de `trabajo.json`.

## Encargo

1. **Selector antes de subir**, al lado de la altura: "¿Con qué se filmó?",
   con los caminos de `GET /api/config` (etiqueta legible: dispositivo, modo,
   y "sin cronómetro" si no está calibrado) y "No sé" = `desconocido-video`,
   que es el default. Se recuerda en `localStorage`.
2. `PUT /api/datos?camino=ID` → `explore(camino=…)`; `trabajo.json` guarda
   el camino. Un id inexistente → 400 con la lista. Un camino `slomo` sin
   calibrar → 400 con la misma frase que da el gate (ADR-016): no se arranca
   un trabajo cuyo eje de tiempo no se conoce.
3. **La ficha del archivo como primera etapa del trabajo**, sin subir dos
   veces: el trabajo corre `fps_truth` antes de la pose y publica en
   `GET /api/datos/{id}` un bloque `archivo` (codec, tamaño y rotación,
   cuadros, duración, fps de reproducción efectivo y bruto si difieren,
   tasa variable sí/no, primer delta y la nota). La pantalla lo muestra
   apenas está, mientras sigue la pose, y queda arriba del resultado.
4. **Los avisos primero.** Arriba del resultado, antes del reproductor:
   el aviso del camino (`fps_aviso`) y, si existe, la corrección del fps
   (`fps_note`), en un bloque que no se pueda perder. La procedencia
   (`sin_verificar`) al lado del fps en la cabecera del trabajo y en la fila
   de la lista.
5. **"Con este archivo"**: un bloque con las 12 métricas del registro, cada
   una como calculada (valor y unidad) o no calculada (su `null_reason`
   textual), leído de `analysis.json`. Es la forma honesta de "el análisis
   depende de la calidad": métrica por métrica, con la razón.

NO: no gate ni atletas ni sesiones; no tocar el motor (`kinelab/`) salvo que
`explore()` no exponga la etapa de la ficha, y entonces sólo eso, dicho en el
informe; no rediseñar; nada de puntajes ni semáforos.

## Cómo se prueba

- `tests/test_service.py`: `PUT` con camino válido, inexistente y `slomo`
  declarado (armá uno en un yaml de prueba); el bloque `archivo` aparece
  antes de que termine la pose (estimador falso); `trabajo.json` con camino.
- `.venv/bin/pytest -q` en verde. `cd web && pnpm lint && pnpm build`.
- Por el proxy con `curl`: subir `~/Desktop/20260907_170638.mp4` con
  `s22ultra-video-fhd30-cable` y verificar en el JSON la ficha (29,998
  efectivo, 29,436 bruto, primer delta 0,201 s), el aviso y las 12 métricas
  con su razón. Subir `~/Desktop/cortado.mp4` con "No sé".
- Para Hernán: el selector, la ficha mientras carga, los avisos arriba, y
  el bloque de métricas, con los dos clips.

## En paralelo

El 07 toca `truth/`, `data/examples/`, `kinelab/explore.py` (arrancar de un
`pose.npz`); el 10 toca `kinelab/metrics/registry.py`, `tests/test_fase2.py`
y `CONTRATO.md` §sextuplo. Si necesitás algo de `explore.py`, que sea
mínimo y en la etapa de la ficha; anotalo.
