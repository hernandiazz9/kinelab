# Estado del trabajo

Dónde quedó el repo al cerrar la última sesión. Se lee **después** de los seis
documentos de `AGENTS.md` y se actualiza al cerrar cada sesión.

## 12 de septiembre de 2026 — segunda sesión: Fase 0 de agente, cerrada

### Hecho y commiteado

- `65fb73b` — la semilla: los seis documentos, `ARRANQUE.md` y `banco/`.
- `1638b7e` — el código de la Fase 0, escrito sin probar.
- `2508edc` — mensaje de arranque.
- **Este commit** — la Fase 0 de agente cerrada (ESPECIFICACION.md 0.1–0.5):
  venv, 94 tests en verde, tres bugs corregidos en el código sin probar, los
  fixtures de ffmpeg arreglados, `data/capture-paths.yaml` vacío con su
  ejemplo comentado, `docs/checklist-captura.md`, `README.md`.

| Qué | Estado |
|---|---|
| `.venv` con `python3.12`, `pip install -e ".[dev]"` | hecho; `kinelab-fps-truth --help` y `kinelab-ingest --help` corren |
| `tests/test_fps_truth.py` | 20 tests. El central: `test_declared_fields_do_not_separate_slowed_from_resampled` |
| `tests/test_capture_paths.py` | 27 tests, incluidos los dos YAML del repo |
| `tests/test_gate.py` | 47 tests: los 9 chequeos, la sesión en disco (`take-01` → `take-02`), el CLI |
| `pytest -q` | 94 pasan, 0 skips, ~3 s (los clips sintéticos son de 96×96) |
| `data/capture-paths.yaml` | `schema_version: "1.0.0"`, `paths: []`. Lo llena el cronómetro. |
| `data/examples/capture-paths.example.yaml` | dos caminos comentados campo por campo: Video 1080p120 y Slo-Mo 1080p240 |
| `docs/checklist-captura.md` | imprimible; secciones A–G de configuración a verificación |

### Bugs encontrados en el código sin probar (corregidos, con test)

1. **`validate_slug` rechazaba el guion bajo**, así que `--vista face_on` y
   `down_the_line` eran imposibles de ingestar: ningún clip de golf podía
   entrar. Ahora `^[a-z0-9][a-z0-9_-]*$`. El id de camino de captura conserva
   su patrón propio (sólo guiones).
2. **La rotación tenía dos convenciones a la vez.** La rama de `side_data_list`
   tomaba el número de ffprobe tal cual (antihorario: un iPhone en vertical da
   `-90` → 270) y la rama del tag `rotate` lo tomaba horario (el mismo clip da
   90). Convención fijada y documentada en `Declared` y en `CONTRATO.md`:
   **horaria, iPhone en vertical = 90**; el valor de ffprobe se invierte.
3. **`count_frames` leía el CSV por posición.** Ahora pide
   `-of compact=p=0:nk=0` y lee `pts_time` por clave, con
   `best_effort_timestamp_time` de respaldo.

### Riesgos de la sesión anterior: confirmados y descartados (ffmpeg 9.0.1)

- **Orden de columnas del CSV** — descartado como riesgo: ffprobe 9 pone
  `pts_time` antes que `best_effort_timestamp_time`, así que la heurística
  funcionaba. Se endureció igual (bug 3).
- **`setpts=8*PTS` + `-fps_mode passthrough` + libx264** — confirmado que
  funciona: 960 cuadros, `r_frame_rate=30/1`, `avg_frame_rate=230400/7673`
  (30,03), deltas uniformes de 33,3 ms. `-r 30` da **122** cuadros, no 120.
  La tesis de CAPTURA.md se reproduce en el test central.
- **`-metadata:s:v:0 rotate=90` con `-c copy`** — confirmado que ffmpeg 9 no
  escribe nada: ni matriz de display ni tag. Reemplazado en el fixture por
  `-display_rotation -90 -i clip -c copy`, que escribe la matriz
  (`rotation: -90` en ffprobe = 90° horario). El fixture ahora es 64×96 para
  que la inversión de `display_size` sea visible.
- **La coma dentro de `setpts='PTS+(mod(N,2)*0.003)/TB'`** — no molesta: las
  comillas simples son el quoting del filtergraph. Pero **el fixture VFR no
  producía tasa variable**: `showinfo` tras el filtro muestra el jitter y el
  archivo sale con deltas uniformes, con libx264, libx265, `hevc_videotoolbox`
  y hasta `rawvideo`, en `.mov`, `.mp4` y `.mkv`. Causa medida: aun con
  `-fps_mode passthrough`, ffmpeg 9 usa `1/fps` como time base del encoder y
  redondea cada PTS a la grilla del cuadro; `-enc_time_base 1/90000` lo
  conserva. El fixture se reemplazó por dos tramos (120 fps + 60 fps)
  concatenados con `-c copy`: ratio 2,0, 480 cuadros. **Lección para la Fase
  4:** cualquier retiming con `setpts` que deba conservar timestamps no
  uniformes necesita `-enc_time_base`; `-fps_mode passthrough` solo no alcanza.
- **`nb_frames` como string de dígitos** — confirmado en `.mov` y `.mp4`.
- **`recording_date` con fecha QuickTime** — `2026-09-14T10:32:11.000000Z`
  parsea (test). Los clips sintéticos no traen `creation_time`; cae a la fecha
  de modificación. Lo que escribe un `.MOV` real de iPhone queda por ver.

### Huecos encontrados en los documentos

- `CONTRATO.md` decía `data/` ignorado salvo `schemas/` y `examples/`, pero
  `capture-paths.yaml` tiene que viajar con el repo (el `.gitignore` ya lo
  hacía). Corregido el texto. El ejemplo de `capture.json` no tenía
  `duration_playback_s`, `original_name` ni los nueve chequeos: actualizado
  con la salida real, y documentados `passed: null` y la convención de
  rotación.
- `DECISIONES.md` ADR-003 etiqueta la spec de Apple como **[pares]**; por la
  leyenda del propio archivo es **[fabricante]**. No se tocó: es una decisión.
- ESPECIFICACION.md 0.4 dice "codec HEVC" y el gate implementa
  `codec_matches_path` (contra el camino). Ya estaba anotado; los tests
  necesitan la segunda forma para los caminos sintéticos en H.264.

### Lo que sólo un clip real puede verificar

- La firma de ffprobe de un `.MOV` de iPhone: edit list, `creation_time`,
  matriz de display en vertical (y que la convención horaria dé 90).
- Que el gate rechace el File → Export del mismo swing (aceptación de Fase 0).
- Los bitrates reales de 1080p120 (el presupuesto viene de un sitio comercial).
- Si el iPhone cambia campo de visión o estabilización entre modos.

### Entorno verificado

`python3.12` = 3.12.14 · `python3` = 3.9.6 (no usar) · ffmpeg / ffprobe 9.0.1
con `libx264`, `libx265`, `hevc_videotoolbox` · pydantic 2.13.5 · pytest 9.1.1
· Mac Apple M3 Pro (arm64).

### Pendiente del humano (Fase 0, pasos 0.6–0.8)

Todo está en `docs/checklist-captura.md`. En resumen:

1. Teléfono: HEVC, 1080p120, Mantener originales.
2. Cronómetro: 10 s, AirDrop, `fps_truth --duracion-real <s> --nominal 120`,
   anotar en `data/capture-paths.yaml`.
3. Sesión: un golfista, `face_on` y `down_the_line`, 10–20 swings por vista,
   80–90% del alto, 2–3 s quieto en address antes de cada swing. Más un clip
   exportado con File → Export para que el gate lo rechace.
4. `python -m kinelab.ingest` por clip. Aceptación: `gate: OK` en los buenos,
   `RECHAZADO` con razón en el exportado.

---

## Mensaje de arranque para la próxima sesión

Pegar en una sesión nueva de Claude Code abierta en `/Users/heralc/Desktop/HDDev/kinelab`,
**después** de haber filmado el cronómetro y la primera sesión.

> Estás en `/Users/heralc/Desktop/HDDev/kinelab`. Antes de escribir una línea,
> leé completos y en este orden: `AGENTS.md`, `CONTEXTO.md`, `DECISIONES.md`,
> `ESPECIFICACION.md`, `CONTRATO.md`, `CAPTURA.md`, `HERENCIA.md`, y por último
> `ESTADO.md`. La Fase 0 de agente está cerrada y probada (94 tests). Yo hice
> la parte humana: hay clips reales en `data/sessions/` y el cronómetro está en
> `data/capture-paths.yaml`.
>
> Primero, en no más de diez líneas: qué dice `capture.json` de cada clip
> real, si la Fase 0 cumple su criterio de aceptación (cada clip con
> `fps_real` de un camino calibrado, `codec: hevc`, `vfr_ratio ≤ 1,10`, y el
> clip exportado desde Fotos rechazado con razón legible), y qué de la lista
> "Lo que sólo un clip real puede verificar" de `ESTADO.md` se confirmó o no.
> Si algo no cumple, se arregla eso primero; no se empieza la Fase 1 sobre
> clips que no pasaron el gate.
>
> Si cumple, arrancá la **Fase 1** por el orden de la spec: 1.1 es portar de
> `padel-coach` (rutas en `HERENCIA.md`) con atribución y tests propios; antes
> de eso, confirmá que los dos repos de origen están accesibles y leé en su
> repo los archivos que `HERENCIA.md` §Se porta enumera para 1.1. No propongas
> dependencias fuera del stack de `DECISIONES.md` ADR-015 sin preguntar.
> Commit al cerrar cada bloque; `ESTADO.md` al cerrar la sesión.
