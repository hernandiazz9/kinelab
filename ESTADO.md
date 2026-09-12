# Estado del trabajo

Dónde quedó el repo al cerrar la última sesión. Se lee **después** de los seis
documentos de `AGENTS.md` y se actualiza al cerrar cada sesión.

## 12 de septiembre de 2026 — sesión que sembró el repo

### Hecho y commiteado

- `65fb73b` — la semilla: `AGENTS.md`, `CONTEXTO.md`, `DECISIONES.md`,
  `ESPECIFICACION.md`, `CONTRATO.md`, `CAPTURA.md`, `HERENCIA.md`, `ARRANQUE.md`
  y `banco/` (scripts de medición con rutas parametrizadas por
  `KINELAB_BENCH_DIR`).
- Este commit — el código de la Fase 0 (parte de agente) **escrito pero nunca
  ejecutado**. Pasó sólo `python3.12 -m py_compile`. No se creó el venv, no se
  instaló nada, no hay tests. Tratarlo como código no confiable hasta que los
  tests digan otra cosa.

| Archivo | Qué es |
|---|---|
| `pyproject.toml` | deps Fase 0: pydantic, pyyaml; dev: pytest. Scripts `kinelab-fps-truth`, `kinelab-ingest`. |
| `kinelab/sport.py` | `SportConfig` (gestures, views, fps_min). El motor define la forma; `sports/` la instancia. |
| `kinelab/tools/fps_truth.py` | `probe_declared`, `count_frames`, `analyze(path, real_duration_s, nominal_fps)`, CLI. Veredictos: `cfr_a_tasa_de_captura` · `estirado` · `destruido` · `vfr` · `sin_duracion_real`. |
| `kinelab/ingest/capture_paths.py` | modelos pydantic `CapturePath` / `CapturePaths` + `load_capture_paths`. Valida ids únicos y `stretch_factor ≈ fps_real / fps_playback`. |
| `kinelab/ingest/gate.py` | `run_gate` con 9 chequeos en orden fijo, `Check.passed: bool | None`, `CaptureJson`, `build_capture_json`. |
| `kinelab/ingest/session.py` | `take-NN` con mkdir atómico, sha256, copia del original, fecha de la sesión. |
| `kinelab/ingest/__main__.py` | `ingest_clip(...)` + CLI. Salida 0 ok · 2 rechazado · 1 error previo al gate. |
| `sports/golf/config.py` | `GOLF`: gestos driver/iron/wedge · vistas face_on/down_the_line · fps_min 100. |
| `tests/conftest.py` | fixture `clips` (7 clips sintéticos con ffmpeg) y `capture_paths_yaml` (4 caminos de prueba). |

### Decisiones tomadas al codificar (los documentos ya las reflejan)

- Un camino de captura registra **dos tasas**: `fps_real` (captura, del
  cronómetro) y `fps_playback` (reproducción, de los PTS), más
  `stretch_factor`. El gate compara la reproducción del clip contra la del
  camino; el motor pasa a tiempo real con el factor. `CONTRATO.md` y
  `CAPTURA.md` actualizados.
- El chequeo de codec es `codec_matches_path` (contra `camino.codec_expected`),
  no `codec_hevc`. Se agregó `gesture_known`.
- `Check.passed` puede ser `None` = no evaluable (por ejemplo, camino
  desconocido). No cuenta como fallo, pero queda visible.
- `capture.json.duration_s` es la duración **real** (`frames / fps_real`);
  `duration_playback_s` es la del contenedor. En un Slo-Mo estirado ×8 difieren
  ×8.
- El motor no importa `sports`; sólo el CLI (`kinelab/ingest/__main__.py`)
  resuelve el deporte por id.

### Falta para cerrar la Fase 0 (agente)

1. Venv con `python3.12` (el `python3` del sistema es **3.9**), `pip install -e ".[dev]"`.
2. Los tests, contra los fixtures de `conftest.py`:

   **`tests/test_fps_truth.py`**
   - `real240_h264`: 960 cuadros, `fps_playback ≈ 240` (±1), `vfr_ratio ≤ 1,10`.
   - `slowed30_h264`: **960** cuadros, `fps_playback ≈ 30`, `declared.r_frame_rate ≈ 30`.
   - `resampled30_h264`: **≈120** cuadros (±2), `fps_playback ≈ 30`, `declared.r_frame_rate ≈ 30`.
   - El test central: estirado y remuestreado son **indistinguibles** por
     `r_frame_rate`, `avg_frame_rate` y `delta_median` (diferencias < 0,5 fps
     y < 1e-4 s), y ambos con `vfr_ratio ≤ 1,10` — y el conteo de cuadros
     (960 vs ≈120) sí los distingue.
   - `analyze(real_duration_s=4.0)`: real → `cfr_a_tasa_de_captura`,
     captura ≈ 240, factor ≈ 1; estirado → `estirado`, captura ≈ 240, factor
     ≈ 8; remuestreado con `nominal_fps=240` → `destruido`, captura ≈ 30.
   - Sin duración real → `sin_duracion_real`.
   - `hevc120_vfr` → `vfr_ratio > 1,10`, veredicto `vfr` (skip si no hay encoder HEVC).
   - `hevc120_rot90` → `rotation_deg == 90` y `display_size` invertido (skip
     si el fixture no existe o ffprobe no reporta rotación).
   - `main([..., "--json"])` → 0 y JSON parseable; clip inexistente → 2.

   **`tests/test_capture_paths.py`**: carga del YAML de fixture (4 caminos,
   `get`); `paths:` vacío o `None` → 0 caminos sin error; id repetido →
   `ValueError`; `stretch_factor` inconsistente → `ValueError`; campo extra →
   error (`extra="forbid"`).

   **`tests/test_gate.py`**
   - `hevc120` en `test-hevc-120-cfr`, `driver`, `face_on` → `ok`;
     `capture.json` escrito y parsea a `CaptureJson`; `sha256` coincide con el
     original copiado; `fps_real 120`; `duration_s ≈ 4`.
   - `real240_h264` en `test-hevc-120-cfr` → `reject`, `codec_matches_path`,
     "H.264" en la razón.
   - `real240_h264` en `test-h264-240-cfr` → `ok`.
   - `slowed30_h264` en `test-h264-240-cfr` → `reject`, `fps_matches_path`.
   - `slowed30_h264` en `test-h264-slomo-240-to-30` → `ok`, `stretch_factor 8`,
     `duration_s ≈ 4` (no 32).
   - `real30_h264` en `test-h264-30-cfr` → `reject`, `fps_min_for_gesture`,
     "tiempos" en la razón.
   - camino desconocido → `reject`, `capture_path_known`; los chequeos que
     dependen del camino con `passed is None`.
   - `hevc120_short` → `reject`, `duration_plausible`.
   - `hevc120_vfr` → `reject`, `vfr_ratio_le_1_10`.
   - vista inválida → `view_declared`; gesto inválido → `gesture_known`.
   - `ingest_clip` dos veces → `take-01` y `take-02`; el original copiado con
     extensión en minúsculas; un rechazo también deja carpeta y `capture.json`.
   - `main()` del CLI: 0 en ok, 2 en rechazo, 1 si el clip no existe.

3. `data/capture-paths.yaml` (vacío: `schema_version` y `paths: []`),
   `data/examples/capture-paths.example.yaml` comentado con el ejemplo de
   `CONTRATO.md`, `docs/checklist-captura.md` imprimible derivado de
   `CAPTURA.md`, `README.md` corto que apunte a `AGENTS.md`.
4. `pytest` en verde. Commit. Actualizar este archivo.
5. **Parar** y decirle al humano qué filmar, con qué ajustes, cómo transferir y
   qué comando corre para verificar cada clip.

### Riesgos conocidos del código sin probar

- `count_frames` pide `frame=pts_time,best_effort_timestamp_time` en CSV; el
  orden de columnas lo decide ffprobe. El parser toma el primer valor numérico
  de cada línea. Verificar con un clip real que no mezcle columnas.
- `setpts=8*PTS` + `-fps_mode passthrough` + libx264: confirmar que salen 960
  cuadros y `r_frame_rate ≈ 30`. Si libx264 reordena o descarta, ajustar.
- `-metadata:s:v:0 rotate=90` con `-c copy` en `.mov`: en ffmpeg 9 puede no
  producir side data de rotación. El fixture lo tolera; el test tiene que
  skipear si `rotation_deg == 0`.
- El filtro `setpts='PTS+(mod(N,2)*0.003)/TB'` va entre comillas simples y se
  pasa sin shell; si ffmpeg se queja de la coma, escaparla como `\,`.
- `Declared.nb_frames_declared` asume que ffprobe devuelve `nb_frames` como
  string de dígitos; en `.mov` suele venir, en otros contenedores puede faltar
  (queda `None`, que es lo esperado).
- `recording_date` usa `datetime.fromisoformat` sobre `creation_time`; el
  formato de QuickTime (`2026-09-14T10:32:11.000000Z`) tiene seis decimales y
  `Z`: se reemplaza `Z` por `+00:00`, debería parsear en 3.12. Probarlo.

### Entorno verificado

`python3.12` = 3.12.14 · `python3` = 3.9.6 (no usar) · ffmpeg / ffprobe 9.0.1 ·
encoders `libx264`, `libx265`, `h264_videotoolbox`, `hevc_videotoolbox` ·
`-fps_mode` disponible. Mac Apple M3 Pro (arm64).

### Pendiente del humano (Fase 0, pasos 0.6–0.8)

- Confirmar el teléfono. El protocolo asume iPhone 17 Pro / 18 Pro (Video
  normal a 1080p120). Con otro modelo, el cronómetro decide.
- Un golfista, un trípode, un cronómetro con milisegundos, una mañana al aire
  libre. Dos vistas, 10–20 swings por vista.
