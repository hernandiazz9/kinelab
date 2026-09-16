# Inventario de lo abierto — verificado contra HEAD `f866c77` (2026-09-16)

Fuentes: informes 18, 24, 25, 26; mensaje de `03aea3f` (encargo 16); `docs/PLAN.md`.
No se tocó el repo. Suites corridas sobre `git archive HEAD` en el scratchpad:
**motor 345 en verde** (345 puntos, 0 F/E, exit 0; `scratchpad/audit-juicio/pytest-head.txt`),
**arnés 43 passed en 11,02 s**. El front no se abrió: lo de pantalla está verificado leyendo código.

## 1 · Le muestra al usuario algo falso (hoy)

| # | qué | dónde, en HEAD | esfuerzo |
|---|---|---|---|
| 1 | Cartel «±1 cuadro» fijo; la banda al lado puede ser ±4 | `web/src/components/Metricas.tsx:42`; el motor ya escribe el tol real en `uncertainty.method` (`kinelab/metrics/core.py:241`, `±{tol_max} cuadro(s)`) y el tipo lo trae (`web/src/lib/api.ts:222`) | una línea |
| 2 | **Sin anotar:** los trabajos guardados y la demo siguen mostrando los números muertos de la ganancia. `TablaEventos.tsx:144` pinta `PICOS[k] ?? k` → sin etiqueta sale el id crudo con su valor; `TablaCuadros` lista todas las columnas del CSV | 19/19 `data/exploracion/*/analysis.json` en 1.0.0 o 1.2.0 con `summary.gain`; sus `datos-eventos.json` traen `shoulder/hip/arm_left_rate_deg_s` en `picos`; 3/3 en `web/public/demo/` igual (`vid1`: `hip_line_rate_deg_s` 3662,0) | mediano (re-analizar) |
| 3 | Trabajos y demo con top viejo | `vid1` (`72d91d03…`, en `data/exploracion` y en la demo): top 722 con `tol_frames` **1** (el informe 18 midió 4 con HEAD); `cortado` (`17ed40a4…`): top 39 con `method: direction_change` (anterior a ADR-017) | mediano |
| 4 | CSV y overlay salen de otra señal de manos que los eventos | `kinelab/explore.py:164` `swing_signals(pose, fps)` → `wrist_score_min` 0,0 (`analysis.py:60`); los eventos usan 0,55 (`analysis.py:164`, `sports/golf/events.py:61`). **Corrección al informe 18:** en HEAD no es "peso igual" sino "pesado por confianza sin umbral" (`analysis.py:66` pasa `pose.scores`). Afecta `hands_*` del CSV, `picos` (`explore.py:376`) y el texto del overlay (`explore.py:242`) | una línea |

## 2 · Riesgo de medición

- `tol_frames` no llega a la pantalla de exploración: `datos-eventos.json` no lo lleva (`explore.py:379`), 0 apariciones en `web/src`; duraciones y tempo de `TablaEventos` sin banda. (18, pregunta 2.)
- Impacto sub-cuadro mostrado como `± ms` de ruido (`web/src/app/page.tsx:321`) mientras el sesgo contra la pelota medido es −11,3 ms (n = 1, informe 24). Pendiente de material.
- Escalón de media empuñadura al dejar una muñeca afuera: sigue (`kinelab/events/signal.py:104-112`), fijado por test en 5/8 cuadros (`tests/test_eventos_senal.py:165`). Decisión del orquestador.
- Top sin error contra GolfDB (ESPECIFICACION 2.5): no hay código; `sports/golf/events.py:64` dice "recalibrar con GolfDB".
- Primeros `judgment_allowed: true` (`cortado3-lento`, informe 26 §4) sin revisar (22,6 cm de sway al impacto; SD 1292 ms de `follow_duration_ms`).
- 240,15 fps es n = 1; faltan el original sin recortar, un clip con cronómetro andando y ≥ 25 s, el delta de arranque de Slow motion y explicar el audio a 12 000 Hz. `data/incoming/` sólo tiene los tres recortes. No verificable en código.
- Calibración heredada contra verificada por clip: `capture.json` no lo distingue (`kinelab/ingest/gate.py`, sin campo). Toca el contrato.

## 3 · Reproducibilidad y proceso

- **Encargo 16:** sin informe (no hay `docs/informes/*-16-*`), sin sección en `ESTADO.md` (secciones: 18, 26, 25, 24, 23…) y sin sus dos corridas reales del punto 6 (`datos` sobre `~/Desktop/cortado.mp4` y `data/incoming/vid1.mp4`, los siete valores en cm contra el 14). Los dos videos existen. No se corrieron en esta auditoría.
- Los números del 26 §4 se midieron sobre un árbol a medio editar; el 16 y el 18 ya están en HEAD y nadie los volvió a medir.
- `cortado3-lento` no se guardó en `data/sessions/` (no existe la carpeta). Sigue abierto dónde se guardan las tomas.
- `docs/PLAN.md` desactualizado: 16, 18, 25 y 26 siguen `[en curso]`; 19, 20 y 22 aparecen dos veces; "Por arreglar en el 16 · `analysis.py:195`" ya está hecho.
- `kinelab/events/order.py` huérfano (ningún import en el repo). Su test **ya se borró** en `03aea3f`; queda el `git rm` y la mención "orden de picos" en `kinelab/events/__init__.py:1-2`.
- Historia de git: 50 blobs, 20,16 MiB de `web/public/demo/` (commits `c7997da`, `620b61a`, `1b0a640`); `1b0a640` (mensaje del 24) lleva las 38 bajas del 25; `eed337c` (26) lleva el renombre de `truth/tests/test_gain_subframe.py`.
- Publicar (25): `data/publicados.json` marca 3 trabajos publicados con `despliegue: null` ("--solo-construir"); el comando nunca corrió contra Vercel. `SITIO` es la URL de un despliegue concreto, con hash, no el alias estable (`kinelab/tools/publicar.py:80`). El despliegue no informa progreso. El sitio en vivo no se verificó.
- **Sin anotar:** `ESPECIFICACION.md:144` (3.2) y `:192` (Fase 5) siguen nombrando la ganancia como métrica, sin la nota de ADR-018. `CONTEXTO.md:55` y `CONTRATO.md:539` la mantienen a propósito como concepto (ADR-018, «Lo que NO cambia»).
- Gate de encuadre en px (17): el umbral sigue en `None` (`sports/golf/config.py:21-26`); `mdc.yaml:109` propone 717 px.
- `docs/checklist-captura.md:7` sigue siendo la hoja del iPhone. El id `s22ultra-slomo-fhd240-recorte-mac` va a quedar viejo.

## Cerrado en HEAD (anotado como abierto en su momento)

- Aviso falso con camino calibrado (24): arreglado en `kinelab/analysis.py:226-239`, con test en `tests/test_fase2.py:336`.
- La ganancia y `sequence_order` (24): ya no están en el código. `rg` sólo los encuentra en tests que exigen que el schema los rechace, en comentarios, en ADR-018 y, a propósito, en `truth/reports/mdc-2026-09-15.json:6781`.
- Test del camino calibrado (24): `tests/test_capture_paths.py:181`.
- `cartado2-lenta` (24): medido por el 26; el cronómetro está detenido.
- Contenido de `truth/tests/test_subframe_encuadre.py` sin commitear (26): entró en `03aea3f`.
