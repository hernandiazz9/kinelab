# Estado real de las Fases 0–5 contra su criterio de aceptación

Auditoría del 16/9/2026 sobre HEAD `f866c77` (árbol limpio). Vara: sólo las
secciones «Aceptación» de `ESPECIFICACION.md`. Nada del repo se modificó.

Estados: **cumplido** · **parcial** · **no cumplido** · **no aplica todavía**.

## Resumen sin optimismo

El proyecto está **en Fase 0, sin cerrar**. El material que pide su aceptación
—una sesión real de 10–20 swings por vista, en `face_on` **y** `down_the_line`,
cada clip con `capture.json` del gate— no existe: `data/sessions/` no existe en
el repo. Hay **un** clip que pasa el gate (`cortado3-lento.mp4`, 9 de 9 chequeos),
de **una** vista (`face_on`), de **un** golfista, con **una** calibración
(n = 1, 240,15 fps ± 0,60) medida sobre **otro** clip y sobre un recorte de la Mac,
no sobre el archivo del teléfono. En la hoja de contactos de ese clip se ven, a
ojo, tres swings; el motor analiza dos.

El código de las Fases 1 a 4 existe por una desviación anotada (ESTADO.md, 12/9,
«Fases 1, 2 y 3 construidas sin material real»). Cumple los criterios que no
dependen de material (schema, corrección manual, regla del MDC en código,
determinismo), y le faltan los que sí: gate de encuadre, SynthPose, GolfDB,
métricas de nivel 1 sin construir, barridos de oclusión y desenfoque, intrínsecos
medidos, ingesta, `master.mp4` y visor desde datos. Fase 5: nada.

## Tabla

| Fase | Criterio | Estado | Evidencia | Qué falta |
|---|---|---|---|---|
| 0 | Existe una carpeta de clips reales; cada uno con `capture.json` con `fps_real` de camino calibrado, `codec: hevc`, `vfr_ratio ≤ 1,10` | **parcial** | Un solo `capture.json` de gate real: `data/incoming/cronometro-26/cortado3-capture.json` (`verdict ok`, `fps_real` 240,15 `medido_aqui`, `hevc`, `vfr_ratio` 1,0027, 2977 cuadros, 12,3964 s reales). Re-corrido hoy a HEAD por otro agente: `audit-juicio/ingest.txt` → `gate: OK`. Los 23 `capture.json` de `data/exploracion/` y `data/incoming/*.kinelab/` son modo exploración, sin gate: 17 con camino declarado, 5 con el id viejo `exploracion` y 1 calibrado (`Cortado-lenta`); 9 son `h264` y los 2 de mocap dicen `ninguno`. `data/sessions/` no existe. | La sesión de 0.8: 10–20 swings por vista, `face_on` y `down_the_line`, ingestada en `data/sessions/`. Cronómetro andando en cada toma (el de `cartado2-lenta` estaba detenido, informe 26 §1) y el original sin recortar de `DCIM/Camera` para calibrar el camino del teléfono y no el recorte. `down_the_line`: cero clips. |
| 0 | El gate rechaza con razón legible el mismo swing exportado desde Fotos con File → Export | **no cumplido** | Sólo proxies sintéticos: `tests/test_gate.py::test_slowed_clip_on_cfr_path_fails_fps_match`, `test_30fps_clip_fails_fps_min_for_golf`, `test_h264_where_hevc_expected_is_rejected_with_readable_reason`. Rechazos reales existen, pero por otras causas: `vid1/2/3` por `fps_min_for_gesture` 60,03 < 100 (informe 11), `Cortado-lenta` por `duration_plausible` 2,49 s (informe 24). | Filmar un swing, exportarlo por la vía degradada que corresponda al teléfono real (el S22 es Android: no hay Fotos → File → Export; el análogo sería Galería/WhatsApp como video) y pasar **ese mismo** swing por el gate, original y degradado. |
| 0 | Cero líneas de código de pose, métricas o interfaz | **no cumplido** | Existen `kinelab/perception/`, `kinelab/metrics/`, `sports/golf/metrics.py`, `service/`, `web/`. Desviación de proceso anotada en ESTADO.md §«12 de septiembre — tercera sesión». | Irreversible; sólo queda anotado. |
| 1 | `pose.npz` para cada clip real, con provenance completa | **parcial** | Los 8 clips reales en disco tienen `pose.npz` con `model`, `checkpoint_sha256`, `provider`, `onnxruntime_version`, `input_size`, `keypoint_set` (script sobre `data/*/*/pose.npz`: 0 campos faltantes en los 21 de CoreML; los 2 de mocap no llevan modelo, por construcción). El `pose.npz` de la toma con gate de `cortado3` que citó el informe 26 (`pose_sha256 2b4714…`) no está en disco; existe uno re-corrido hoy (`audit-juicio/data/sessions/…/take-01/pose.npz`, sha `bbb57f2e…`). `master_sha256: null` en todos. | La carpeta de clips de Fase 0 (no existe), y su `pose.npz` en `data/sessions/`. |
| 1 | Dos corridas del mismo clip con el mismo proveedor dan `pose.npz` idénticos | **cumplido** (con matiz) | Verificado en esta auditoría: `keypoints`, `scores`, `bbox` y `plausibility` idénticos (`np.array_equal`, diferencia máxima 0,0 px) entre corridas independientes con CoreML de `cortado.mp4` (5 corridas, 12/9–14/9), `vid1` (4), `20260907_170638` (4), `vid3` (3, dos con el mismo `code_sha` 7f34c34), `Cortado-lenta` (2) y `cortado3-lento` (exploración 15/9 contra la toma con gate de hoy). Sólo difieren `run_at`, `code_sha` y, cuando cambió el fps, `timestamps_s`/`framing`. | No hay test automático; el archivo no es idéntico byte a byte (lleva `run_at` a propósito); no se probó el proveedor CPU. |
| 1 | El gate rechaza un clip con el sujeto al 15 % del alto del cuadro | **no cumplido** | `body_height_frac` sale `passed: null`, «umbral sin medir», en todas las tomas (p. ej. `cortado3-capture.json`). `tests/test_perception.py::test_framing_report_and_checks` fija que sin umbral no se evalúa. El umbral de 717 px está propuesto en `sports/golf/mdc.yaml §framing` con la advertencia «PROPUESTA, no umbral. El gate NO lo lee»; encargo 17 pendiente (PLAN). | Fijar el umbral (encargo 17) y un test con un clip con el sujeto al 15 % que salga `reject`. |
| 1 | El reporte SynthPose vs RTMPose existe, con número por keypoint | **no cumplido** | PLAN §Aparcado: «SynthPose (1.5) después de los intrínsecos reales». ESTADO 12/9: «no hecho: SynthPose necesita torch». Ningún informe lo produce. | Todo el paso 1.5. |
| 1 | Un clip sintético con la imagen sin normalizar produce una aserción, no un `pose.npz` lleno de NaN | **parcial** | `tests/test_perception.py::test_pose_guards_preprocess_and_nan`: imagen sin normalizar → `PreprocessError`; salida NaN → `PoseNaNError`. Con una sesión ONNX falsa y una imagen suelta. | Test con un **clip** sintético por `run_perception` (y con el modelo real en CoreML, que es donde se midió el NaN silencioso) comprobando que no se escribe `pose.npz`. |
| 2 | `analysis.json` valida contra el schema | **cumplido** | `tests/test_fase2.py::test_analyze_and_adjust_end_to_end`, `test_repo_example_is_valid`, `test_schema_rejects_renamed_field`. Validado en esta auditoría con `kinelab.contract.validate.validate_analysis`: 0 errores en `cronometro-26/cortado3-analysis.json`, en `vid1/vid2/vid3.kinelab/analysis.json` y en el re-corrido de hoy. | Nada para el criterio. Nota: los 19 `analysis.json` de `data/exploracion/` e `incoming/Cortado-lenta.kinelab` (1.0.0/1.2.0) no validan contra 2.0.0 (2 a 28 errores cada uno) y siguen en la lista de trabajos. |
| 2 | Error de eventos contra GolfDB reportado por evento en cuadros | **no cumplido** | Existe `kinelab/tools/golfdb_eval.py` y `test_golfdb_stats` sobre datos inventados; el dataset no está descargado (ESTADO 12/9), PLAN: «[pendiente] golfdb-error-de-eventos (2.5), después de decidir con Hernán». Informes 15 y 18: «El error del top sigue sin medirse contra GolfDB». | Descargar GolfDB, correr la medición y el reporte con sesgo y límites de acuerdo por evento. |
| 2 | Clip sin gesto → 0 repeticiones, sin excepción | **cumplido** (sintético) | `tests/test_fase2.py::test_still_and_walking_give_zero_reps` (quieto y caminando → `[]`); `tests/test_perception.py::test_explore_mode_writes_everything_even_without_a_person` (video con persona quieta → eventos `{}`, sin excepción). | Ningún clip real sin gesto probado (el 0 de `vid3` es un swing que el motor no encontró, no un clip sin gesto). |
| 2 | Ajuste manual de un evento hace round-trip y conserva el valor detectado | **cumplido** (sintético) | `test_manual_edits_keep_detected_and_reject_collisions` y `test_analyze_and_adjust_end_to_end` (`python -m kinelab adjust`, `frame_detected` conservado, versión anterior archivada). | No se probó sobre una toma real. |
| 2 | Mover dos repeticiones al mismo cuadro falla con razón | **cumplido** (sintético) | Mismo test: `EventCollisionError` al mover el address de la rep 2 (129) antes del impacto de la rep 1 (130); CLI devuelve 1 y no toca el archivo. | — |
| 3 | Cada métrica de nivel 1 tiene MDC medido y está en el registro con sus seis cosas | **parcial** | 12 métricas vivas en `sports/golf/metrics.py` con `mdc`, `views`, `fps_min` leídos de `sports/golf/mdc.yaml` (arnés, nivel 0, 16 semillas); dos rodillas muertas por el arnés; ganancia muerta (ADR-018). | (a) Nivel 1 de `CONTRATO.md §Niveles` sin construir: **geometría del shaft por evento** y **deltas de postura respecto del address**, sin entrada ni muerte anotada. (b) `hands_speed_curve_top_to_impact` sale en `summary` con `level: 1` y `mdc: null`. (c) El MDC es **nivel 0** (proyección + ruido, sin estimador) con cámara `iphone17pro-1080p120`, `provenance: sin_verificar`, distorsión 0: no son intrínsecos medidos del teléfono real (3.1). (d) Test con ángulo no trivial por métrica: no encontrado para cada una (hay 37° en `tests/test_escala.py` para desplazamientos). |
| 3 | La regla del MDC está en código: sin MDC o MDC > rango no puede ser juicio | **cumplido** (con matiz) | `kinelab/metrics/registry.py::judgment_allowed` (exige `mdc is not None`, `fps_min`, `medido_aqui`, vista, `mdc <= range_width`); `tests/test_fase2.py::test_registry_rules_and_judgment` (caso MDC 5 > rango 4 → False). | Matiz: con `Reference("descriptive", …)` sin rango, la regla devuelve `True`. Por eso las 11 métricas de `cortado3` salen `judgment_allowed: true` con referencia «sin rango de referencia; se muestra como descriptiva». No hay test del caso `mdc=None`. |
| 3 | Cada uno de los cuatro bugs inyectados hace fallar al menos un test | **parcial** | Mutaciones sueltas documentadas: signo de Y y eje en el sub-cuadro (informe 02, `test_impact_subframe_changes_with_the_wrong_axis_and_with_y_flipped`); radianes y izquierda/derecha en `truth/` (informe 23, 9 de 9); grados en `test_angle_deg_matches_trigonometry_in_degrees`; espejo en `tests/test_keypoints.py`. | No hay una corrida de los **cuatro** (signo de Y, grados/radianes, fps ±1, izquierda/derecha) sobre las métricas del registro; ESTADO 12/9: «mutation manual de la invariante 15 no hecha sistemáticamente». fps ±1 no aparece documentado. Tampoco hay Hypothesis ni goldens (ADR-011, capas 2 y 4). |
| 3 | Un sujeto quieto produce cero métricas, no métricas en null | **parcial** | Código: con 0 repeticiones `summary.metrics` queda `{}` (`vid3.kinelab/analysis.json`: `rep_count 0`, `metrics {}`). Test sólo a nivel de segmentación (`test_still_and_walking_give_zero_reps`). | Test de punta a punta: `analyze` sobre una toma con sujeto quieto que verifique `reps == []` y `summary.metrics == {}`. |
| 3 | El nivel 0 del arnés no se acepta sólo con el caso nominal: la tabla tiene los barridos | **parcial** | `truth/reports/mdc-2026-09-15.json`: 44 condiciones en las dos vistas: azimut 0/15/30/45/60/90, elevación 0/15/30/45, distancia 2/4/6/8 m, tamaño ×1/0,5/0,25/0,11, ruido 0/0,003/0,006/0,012, fps 240/120/60/30. | Oclusión y desenfoque por sub-cuadros (3.1) ausentes (sin coincidencias en `truth/kinelab_truth/harness.py`); azimut 75° ausente; intrínsecos sin medir. |
| 4 | Importar → gate → analizar → visor, de punta a punta, sobre los clips reales | **no cumplido** | La pantalla corre modo exploración (`capture.json` «EXPLORACIÓN: sin gate»); no hay ingesta 4.3 (PLAN §Aparcado: la página vieja del gate «se borra con la ingesta 4.3»); no hay `master.mp4` (`master_sha256: null` en todo `pose.npz` y `analysis.json`); visor desde datos = encargo 21 pendiente. | 4.2 `master.mp4`, 4.3 ingesta con veredicto antes de analizar, 4.4 visor desde `pose.npz`, y la corrida sobre los clips de Fase 0. |
| 4 | El cuadro dibujado es el presentado, verificado por `mediaTime`; retroceder un cuadro cambia número e imagen juntos | **parcial** | `web/src/components/Reproductor.tsx` y `DosCuadros.tsx` usan `requestVideoFrameCallback` y `mediaTime`. | Sin verificar (el front no se abrió, regla de trabajo). Hoy reproduce `overlay.mp4` horneado (Reproductor.tsx:10, «Provisorio»), no un dibujo sobre el `master`. |
| 4 | Un clip rechazado muestra la razón antes de cualquier número | **parcial** | API: `tests/test_service.py::test_ingest_reject_is_still_200_with_reasons`; exploración muestra avisos primero (`Avisos.tsx`, informe 09). | La pantalla actual no corre el gate; no hay flujo de ingesta con rechazo en el front; no verificado en navegador. |
| 4 | El zoom a 4× no pixela el trazo | **no cumplido** | `ZOOM_MAX = 4` en `Reproductor.tsx:40`, pero el trazo está dentro de los píxeles de `overlay.mp4`: ampliarlo amplía el video. | Visor desde datos con canvas vectorial (encargo 21). No verificado a ojo. |
| 5 | El entrenador mira diez swings y dice qué va a corregir, señalando cuadro, número y banda | **no cumplido** | Sin comparación lado a lado (`compare.py` sin portar), sin lectura de repetibilidad en la pantalla. PLAN: «Fase 5 … No antes de clips por el gate y del visor desde datos». Hay un solo clip con gate y 2 swings analizables. | Toda la fase, y antes diez swings que pasen el gate. |

## Cómo se obtuvieron los números de esta auditoría

- Veredictos de `capture.json`: script Python sobre `find data -name capture.json`.
- Provenance y determinismo: script con `numpy.load` sobre `data/*/*/pose.npz`,
  agrupando por `source_name` y comparando con `np.array_equal(..., equal_nan=True)`.
- Validación de `analysis.json`: `kinelab.contract.validate.validate_analysis` a HEAD.
- Barridos del arnés: claves `results[].condition` de `truth/reports/mdc-2026-09-15.json`.
- Hoja de contactos: `ffmpeg -i data/incoming/cortado3-lento.mp4 -vf "fps=0.5,scale=-2:240,tile=10x5"`
  → `audit-juicio/cortado3-hoja.jpg` (50 cuadros, uno cada 2 s de reproducción = 0,25 s reales).
- Corrida de hoy a HEAD de `cortado3` (ingest/perception/analyze): la hizo **otro
  agente** en esta misma carpeta (`ingest.txt`, `perception.txt`, `analyze.txt`,
  `data/sessions/…/take-01/`); yo sólo la leí.

## Lo que la corrida a HEAD cambia respecto del informe 26

- Rep 1: 11 de 12 métricas con `judgment_allowed: true` (igual que el informe).
- Rep 2: **10 de 12**: `follow_end` ya no se detecta (`follow_duration_ms` null,
  «sin evento follow_end en esta repetición»). El informe 26 decía 11 de 12 en las dos.
- `summary.follow_duration_ms`: n 1 (el informe 26 tenía n 2 con SD 1292 ms).
- Top de la rep 2: cuadro 2548 (informe 26: 2549). Address e impacto iguales.
- Los números del informe 26 no eran reproducibles desde HEAD; el propio ESTADO lo avisaba.

## Lo que no se pudo verificar

- Nada de la pantalla (regla: no se abre el front).
- Si los 240,15 fps valen para `cortado3-lento.mp4`: no tiene cronómetro propio;
  el gate verifica la reproducción (30,017 contra 30,0169 fps), no la captura.
- El conteo de swings de `cortado3` es a ojo sobre la hoja de contactos (tres
  visibles, el primero ya en curso en el cuadro 0), no una medición.
- Las suites no se corrieron acá (las corre otro agente).
