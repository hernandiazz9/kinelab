# Reproducción desde HEAD del análisis del informe 26 sobre `cortado3-lento.mp4`

Fecha: 2026-09-16. HEAD `f866c77`, árbol limpio antes y después (`git status --short` vacío, `git diff --cached --name-only` vacío). No se tocó nada trackeado.

Salida en `/private/tmp/claude-501/-Users-heralc-Desktop-HDDev-kinelab/17afdee3-80aa-4396-8468-a0ca20cd2a23/scratchpad/audit-juicio/` (abajo `$O`).

## Rutas

| qué | ruta |
|---|---|
| take_dir | `$O/data/sessions/hernan/2026-09-15/driver/face_on/take-01` |
| analysis.json (take, `medido_aqui`) | `$O/data/sessions/hernan/2026-09-15/driver/face_on/take-01/analysis.json` (sha256 `cfbc5e45…`) |
| pose.npz | `$O/data/sessions/hernan/2026-09-15/driver/face_on/take-01/pose.npz` (sha256 `bbb57f2e…`) |
| exploración (`datos`) | `/Users/heralc/Desktop/HDDev/kinelab/data/incoming/cortado3-lento.kinelab/` (overlay.mp4, evento-*.png, datos-por-cuadro.csv, datos-eventos.json, analysis.json con `sin_verificar`) |
| logs | `$O/pytest-motor.txt`, `$O/motor-junit.xml`, `$O/pytest-truth.txt`, `$O/ingest.txt`, `$O/perception.txt`, `$O/analyze.txt`, `$O/datos.txt`, `$O/candidatos.txt`, `$O/wrist_min.txt` |
| corrida diagnóstica con código viejo | `$O/old-9704348/` (git archive de `9704348`), `$O/old-take/analysis.json` |

Clip: `data/incoming/cortado3-lento.mp4`, sha256 `6557e7b6…4a81` (igual al `sha256_original` del capture.json).

## 1 · Suites

- **Motor** `.venv/bin/pytest -q`: **345 pasados, 0 fallados, 0 errores, 0 saltados, 51,65 s** (de `motor-junit.xml`). La línea de resumen no se imprime porque `pyproject.toml` ya trae `addopts = "-q"` y el `-q` de la línea de comandos lo vuelve `-qq`; por eso se contó con `--junitxml`. Exit 0.
- **Arnés** `cd truth && .venv/bin/pytest -q`: **43 pasados en 11,77 s (y 11,23 s en una segunda corrida)**, 0 rojos. **Pero el proceso termina con exit 134** en las dos corridas: `libc++abi: terminating due to uncaught exception of type std::__1::system_error: recursive_mutex lock failed: Invalid argument`, después del resumen. Ningún test falla; es un aborto al cerrar el intérprete. Causa no investigada (no verificado de qué librería nativa viene).

## 2 · Ingesta

**Desvío necesario:** el comando tal como está escrito falla desde HEAD: `error: [Errno 2] No such file or directory: …/audit-juicio/data/capture-paths.yaml`. `kinelab/ingest/__main__.py:103` lee `capture-paths.yaml` de `--data`, no del repo. Se copió `git show HEAD:data/capture-paths.yaml` a `$O/data/capture-paths.yaml` (sha256 `8d0123c0…ce52`, idéntico al del repo) y se re-corrió el mismo comando. (El informe 26 usó `--data /tmp/k26`, que hoy no existe; no se puede saber qué tenía adentro.)

Salida: `hevc 1080x1920 · 2977 cuadros · reproducción 30.0169 fps · captura 240.15 fps · 12.3964 s reales` · **gate: OK**. `verdict: ok`, `reasons: []`.

| chequeo | pasó | valor | esperado |
|---|---|---|---|
| capture_path_known | sí | s22ultra-slomo-fhd240-recorte-mac | — |
| codec_matches_path | sí | hevc | hevc |
| vfr_ratio_le_1_10 | sí | 1,0027 | ≤ 1,1 |
| fps_matches_path | sí | 30,017 fps | 30,0169 fps ± 2 % |
| fps_min_for_gesture | sí | 240,15 fps | ≥ 100 fps |
| duration_plausible | sí | 12,396 s | 3–180 s |
| rotation_normalized | sí | 90° | — |
| view_declared | sí | face_on | face_on, down_the_line |
| gesture_known | sí | driver | driver, iron, wedge |

`fps_provenance: medido_aqui`, `fps_source: capture-paths.yaml:s22ultra-slomo-fhd240-recorte-mac`, `stretch_factor` 8,0005, `recorded_at` 2026-09-15T17:26:40Z (de ahí la fecha `2026-09-15` del take_dir).

## 3 · Percepción y análisis

Flags sin cambios con el contrato 2.0.0 (`--help` de los tres). `perception`: 45,0 s de pared.

- Proveedor **CoreMLExecutionProvider**, onnxruntime 1.30.0, rtmlib 0.0.16, `intra_op_num_threads` 5, `det_frequency` 10, rtmpose-m-halpe26 (sha256 `26f3a19e…`), detector yolox-m-coco (sha256 `21ff6cfd…`), `code_sha` f866c777.
- 2977 cuadros · detección 100,0 % (2977/2977) · cuerpo **690,87 px mediana (636,43–832,39 px) = 35,98 % del alto** (1920 px) · cámara 1,347 px · plausibilidad: 27 cuadros rechazados, todos `ELBOW_RANGE`.
- Checks de Fase 1: `detection_rate` ok, `single_subject` ok, `body_height_frac` sin evaluar (umbral sin medir).
- **Determinismo:** `datos` volvió a correr el modelo; `keypoints`, `scores`, `bbox`, `timestamps_s` y `plausibility` salieron **bit-idénticos** a los del take (sólo cambia `run_at`).

`analyze --altura-m 1.75`: calidad `confiable`, `reasons: []`, **`warnings: []`**, `deviations: []`, schema 2.0.0, registry 0.2.0.

### quality.scale_px

`{"value": 783.9, "frame": 1594, "method": "max_stature_chain_px · mediana de 2 repeticiones"}` (px).

### Repeticiones

2 aceptadas, **1 descartada `sin_address`**. El analysis.json no dice cuál; se identificó con un script de sólo lectura (`$O/candidatos.py`): tres candidatos de segmentación, 0 descartes de segmentación; el descartado es el **pico en cuadro 120 (t = 0,500 s, 4,295 bh/s, ventana 0–480)**: `stable_window_end` no encuentra quietud antes del pico porque está al principio del clip.

| rep | evento | cuadro | t (s) | tol_frames | método |
|---|---|---|---|---|---|
| 1 | address | 1052 | 4,3806 | 1 | stable_window |
| 1 | top | 1284 | 5,3467 | 1 | direction_change_farthest |
| 1 | impact | 1364 | 5,6798 | 1 | peak_window (sub-cuadro: 1364 + 0,1468 → 5,680395 s, ±0,6964 cuadros = ±2,9 ms; MDC 2,927 ms `medido_aqui`) |
| 1 | follow_end | 1978 | 8,2365 | 2 | stable_window |
| 2 | address | 2322 | 9,6690 | 1 | stable_window |
| 2 | top | 2548 | 10,6100 | 1 | direction_change_farthest |
| 2 | impact | 2624 | 10,9265 | 1 | peak_window (sub-cuadro: 2624 + 0,0884 → 10,926872 s, ±0,1578 cuadros = ±0,657 ms) |
| 2 | follow_end | **null** | — | — | — |

Rep 1: ventana 1052–1978, pico 4,758 bh/s. Rep 2: ventana 2322–2970 (sin follow_end, termina en `c.end`), pico 4,848 bh/s.

### Métricas (todas `fps_provenance: medido_aqui`)

`judgment_allowed` = jA. Incertidumbre = ±tol_frames en cada evento ancla a 240,15 fps.

| métrica | unidad | MDC | rep 1 valor [baja, alta] | jA | rep 2 valor [baja, alta] | jA |
|---|---|---|---|---|---|---|
| backswing_duration_ms | ms | 12,601 | 966,1 [961,9; 970,2] | true | 941,1 [936,9; 945,2] | true |
| downswing_duration_ms | ms | 12,996 | 333,1 [329,0; 337,3] | true | 316,5 [312,3; 320,6] | true |
| tempo_ratio | ratio | 0,065 | 2,9 [2,852; 2,949] | true | 2,974 [2,922; 3,027] | true |
| follow_duration_ms | ms | 11,505 | 2556,7 [2548,4; 2565,1] (±2 cuadros) | true | null — "sin evento follow_end en esta repetición" | false |
| pelvis_sway_top_cm | cm | 2,841 | 3,7 [3,2; 3,7] | true | −7,1 [−7,5; −6,8] | true |
| pelvis_sway_impact_cm | cm | 2,416 | 22,6 [22,1; 22,9] | true | 7,7 [7,7; 7,9] | true |
| pelvis_lift_top_cm | cm | 2,769 | −4,3 [−5,5; −3,7] | true | −5,5 [−6,0; −4,9] | true |
| thorax_sway_top_cm | cm | 3,388 | 3,5 [2,9; 3,5] | true | −5,1 [−5,4; −4,9] | true |
| thorax_lift_top_cm | cm | 2,819 | 5,0 [4,0; 5,0] | true | 2,4 [1,2; 2,6] | true |
| pelvis_thrust_top_cm | cm | 2,61 | null — "vista face_on no válida para esta métrica (válidas: down_the_line)" | false | null — ídem | false |
| head_sway_top_cm | cm | 3,779 | 4,9 [4,1; 5,0] | true | −4,6 [−4,8; −4,4] | true |
| head_lift_top_cm | cm | 4,382 | −2,0 [−3,5; −2,0] | true | −0,8 [−1,7; −0,4] | true |

Métricas en cm llevan `confidence` (keypoint_scores_at_anchors): rep 1 pelvis 0,695/0,708, tórax 0,736, cabeza 0,819; rep 2 pelvis 0,714/0,718, tórax 0,729, cabeza 0,811. Todas `metric_version` 1.1.0 (cm) o 1.0.0 (tiempos), `level` 1, `fps_min_met` true.

Observación de forma, sin juicio: en varias métricas el valor coincide con un extremo de su propio intervalo (p. ej. pelvis_sway_top 3,7 en [3,2; 3,7]). Es lo que escribe el archivo; no se verificó si es esperable del método.

Resumen (summary): backswing mediana 953,6 ms (n 2, SD 17,678 ms); downswing 324,8 ms (SD 11,738); tempo 2,937 (SD 0,052); follow 2556,7 ms (**n 1**, SD null); pelvis_sway_top −1,7 cm (SD 7,637); pelvis_sway_impact 15,15 cm (SD 10,536); pelvis_lift_top −4,9 cm (SD 0,849); thorax_sway_top −0,8 cm (SD 6,081); thorax_lift_top 3,7 cm (SD 1,838); head_sway_top 0,15 cm (SD 6,718); head_lift_top −1,4 cm (SD 0,849); hands_speed_curve_top_to_impact DTW normalizado 0,0397 (n 2).

## 4 · Exploración (`datos`)

1 min 39 s. Mismos cuadros de eventos que el take, mismos valores de rep 1, pero `fps_provenance: sin_verificar` y `judgment_allowed: false` en todo (como corresponde: `datos` no corre el gate), con dos warnings de exploración. Picos: `hands_speed_bh_s` 4,85 · `hands_speed_cm_s` 848,35. Ojo: la línea de consola imprime `impact_to_follow_end_ms` 2556,7.

## 5 · Comparación con el informe 26 (rep 1)

| dato | informe 26 | HEAD | ¿igual? |
|---|---|---|---|
| backswing | 966,1 ms | 966,1 ms | sí |
| downswing | 333,1 ms | 333,1 ms | sí |
| tempo | 2,9 | 2,9 | sí |
| **follow** | **2560,9 ms** | **2556,7 ms** | **no (−4,2 ms = 1 cuadro)** |
| pelvis_sway_top | 3,7 cm | 3,7 cm | sí |
| pelvis_sway_impact | 22,6 cm | 22,6 cm | sí |
| pelvis_lift_top | −4,3 cm | −4,3 cm | sí |
| thorax_sway_top / lift | 3,5 / 5,0 cm | 3,5 / 5,0 cm | sí |
| head_sway_top / lift | 4,9 / −2,0 cm | 4,9 / −2,0 cm | sí |
| pelvis_thrust_top | null (vista) | null (vista) | sí |
| repeticiones | 2, 1 descartada sin_address | 2, 1 descartada sin_address | sí |
| follow_end detectado | sí | sí en rep 1, **no en rep 2** | parcial |
| cuerpo | 690,9 px = 36,0 % | 690,87 px = 35,98 % | sí |
| SD follow entre reps | 1292 ms | **null (n = 1)** | **no** |
| warnings | [] | [] | sí |

### Por qué cambió (verificado en parte)

Se corrió el analyze del commit `9704348` (último commit antes de 16/18 commiteados; extraído con `git archive` a `$O/old-9704348`, sin tocar el repo) sobre el **mismo pose.npz**. Ese código reproduce exactamente los números del informe 26: rep 1 follow_end **1979** → 2560,9 ms; rep 2 follow_end **2800** → 732,9 ms; follow SD **1292,591 ms**. Aclaración: el informe 26 corrió sobre un árbol con cambios sin commitear, no sobre `9704348`; que coincidan es evidencia de que esos cambios no movían estos números, no una prueba de que el árbol fuera ese.

Diferencias `9704348` → HEAD con el mismo pose:
- rep 1: follow_end 1979 → 1978 (1 cuadro). **Causa no aislada**: persiste con `wrist_score_min = 0`, así que viene de otro cambio de 16/18.
- rep 2: top 2549 → 2548; follow_end 2800 → **null**; backswing 945,2 → 941,1 ms; downswing 312,3 → 316,5 ms; tempo 3,027 → 2,974; follow 732,9 ms → null; pelvis_sway_top −7,8 → −7,1; pelvis_sway_impact 8,2 → 7,7; pelvis_lift_top −6,4 → −5,5; thorax_sway_top −5,2 → −5,1; thorax_lift_top 1,3 → 2,4; head_sway_top −4,7 → −4,6; head_lift_top −0,7 → −0,8 cm.
- **follow_end de la rep 2 desaparece por `wrist_score_min = 0,55` (encargo 18, `54532d1`)** — verificado con `$O/wrist_min.py` (sólo lectura): con HEAD y `wrist_score_min = 0` vuelve a aparecer follow_end en 2797 (top 2549); con 0,55 es null. Umbral de quietud 0,1998 bh/s (2,5 × piso de ruido 0,0799 bh/s), ventana exigida `follow_still_s` 0,3 s = 72 cuadros. Mi recuento aproximado (still ≤ umbral, que puede no ser idéntico al criterio de `stable_window_start`) da como racha quieta más larga tras el impacto de la rep 2: 55 cuadros (229 ms) con 0,55 y 90 cuadros (375 ms) con 0. Después del impacto de la rep 2 quedan 352 cuadros (1,47 s) de clip.

## No verificado

- Si el follow_end correcto de la rep 2 existe o no en el video (no se miraron cuadros; queda para los auditores con el overlay).
- De dónde sale el cuadro de diferencia en el follow_end de la rep 1.
- El aborto `libc++abi` del arnés al cerrar.
- Nada de lo anterior dice si 22,6 cm o cualquier otro valor es correcto: sólo que HEAD los reproduce.
