# Estado del trabajo

Dónde quedó el repo al cerrar la última sesión. Se lee **después** de los seis
documentos de `AGENTS.md` y se actualiza al cerrar cada sesión.

## 12 de septiembre de 2026 — tercera sesión: Fases 1, 2 y 3 construidas sin material real

### Desviación de proceso, anotada

A pedido explícito del entrenador ("avanzá full en las fases"), se construyó
código de las Fases 1, 2 y 3 **sin clips reales que hayan pasado el gate**, contra
lo que fija `ESPECIFICACION.md` ("una fase por vez", "material antes que
código"). Se hizo con datos sintéticos y con un clip heredado de pádel para
probar la cadena de percepción. Todo criterio de aceptación que necesita
material real sigue **abierto** y está listado abajo. Regla de trabajo nueva:
el agente crea con tests mínimos; el entrenador prueba el front y las corridas
reales. Sin navegador ni workflows de subagentes (quemaron el límite de sesión
sin producir nada).

### Commits de esta sesión

- `8ede11a` Fase 0 de agente cerrada (94 tests, fps_truth, gate, checklist).
- `e1b4b89` `service/`: página HTML local para pasar clips por el gate
  (adelanto de 4.3 a pedido). `python -m service` → http://127.0.0.1:8765.
- `ed2b865` Fase 1: `kinelab/perception/` completo, `python -m kinelab.perception`.
- `5f7efaa` Fase 2: `kinelab/events/`, `kinelab/contract/`,
  `kinelab/metrics/registry.py`, `sports/golf/events.py`, `python -m kinelab analyze|adjust`.
- Fase 3: `kinelab/metrics/` (sextuplo, ±1 cuadro, repetibilidad, ganancia),
  `sports/golf/metrics.py` + `sports/golf/mdc.yaml`, `truth/` (arnés con su venv),
  `truth/reports/mdc-2026-09-12.json`.

### Qué hay, qué prueba cada cosa

| Pieza | Comando | Probado con |
|---|---|---|
| Verdad del fps | `.venv/bin/python -m kinelab.tools.fps_truth CLIP --duracion-real S --nominal 120` | clips sintéticos (tests) |
| Gate de ingesta | `.venv/bin/python -m kinelab.ingest CLIP --atleta a --gesto driver --vista face_on --camino ID` | clips sintéticos (tests) |
| Página del gate | `.venv/bin/python -m service` (opcional `--data DIR --port N`) | TestClient (34 tests); **nunca abierta en un navegador** |
| Modelos | `.venv/bin/python -m kinelab.perception.models [--download]` | los dos verifican por hash en `models/` |
| Percepción | `.venv/bin/python -m kinelab.perception TAKE_DIR [--cpu] [--overwrite]` | estimador falso (tests) + **una corrida real** sobre `padel-coach/samples/demo_h264.mp4`: 230 cuadros en 10 s con CoreML, 82 % de detección, gate rechaza por varias personas (correcto) |
| Análisis | `.venv/bin/python -m kinelab analyze TAKE_DIR` | swing sintético (`tests/helpers/synth_swing.py`) |
| Corrección manual | `.venv/bin/python -m kinelab adjust TAKE_DIR --rep 1 --event top --frame F` | sintético; round-trip y colisión |
| Arnés de verdad | `cd truth && .venv/bin/python -m kinelab_truth` (12 s) | escribe `sports/golf/mdc.yaml` y `truth/reports/`; tests: `cd truth && .venv/bin/pytest -q` (4) |
| Calibrar la cámara real | `cd truth && .venv/bin/python -m kinelab_truth.calibrate FOTOS --cols 9 --rows 6 --square-mm 25 --id iphone17pro-1080p120 --out cameras/iphone17pro-1080p120.yaml` | sin correr: necesita fotos de un tablero con el teléfono |
| Modo exploración | `.venv/bin/python -m kinelab datos VIDEO --altura-m 1.75` | probado con dos clips reales de Hernán (WhatsApp 29 fps y un vertical de iPhone 30 fps): overlay, fotos por evento, CSV por cuadro y JSON por evento |
| Suite | `.venv/bin/pytest -q` | 166 tests en verde, ~9 s |

### Decisiones tomadas al codificar (no estaban en los documentos)

- **Señal maestra del swing: el centro de las dos muñecas** (las manos van
  juntas en el grip): independiente de la lateralidad, más estable que una
  muñeca sola. `sports/golf/events.py` lo documenta.
- **Impact** = cuadro más cercano a la posición de las manos en address, dentro
  de ±0,25 s del pico de velocidad de las manos (el palo vuelve a la pelota).
  **Top** = último cambio de signo de la velocidad de las manos proyectada
  sobre el eje principal de la trayectoria address→impact. **Address** =
  último cuadro de la ventana de quietud (< 0,15 alturas/s durante ≥ 0,5 s)
  antes del pico, refinado hacia atrás hasta donde la velocidad deja de bajar.
  Todos los umbrales son `estimacion` y viven en `GolfEventParams`.
- Ventana de agudeza de la segmentación en golf: 3 s (con 1 s, heredado de
  pádel, un swing continuo de ~2 s parece "sostenido" y se descarta).
- `pose.npz` guarda la pose CRUDA del sujeto elegido; relleno de huecos,
  filtrado y máscaras son derivados que se aplican al leer.
- `rotation_deg` horario; `iter_frames` no rota dos veces si OpenCV ya aplicó
  la rotación de metadatos (regla por tamaño y `CAP_PROP_ORIENTATION_AUTO`).
- Umbral de encuadre `body_height_frac_min = None` hasta medirlo: el chequeo
  se reporta `passed: null` con razón "umbral sin medir".
- Modelos: `rtmpose-m-halpe26` (OpenMMLab, sha256 `26f3a19e…`) y `yolox_m`
  0.1.1rc0 de Megvii entrenado en COCO (sha256 `21ff6cfd…`). Los YOLOX de
  Human-Art que rtmlib trae por defecto quedan fuera (ADR-010). **Pendiente de
  licencia:** los datos de entrenamiento "body7" de RTMPose incluyen Halpe;
  su licencia figura como `sin_verificar` en `models.py`.
- OpenCV: `opencv-python` y `opencv-contrib-python` fijados a 4.14.0.94 los
  dos (rtmlib exige ambos; instalan el mismo `cv2`).
- Medido: CoreML compila la sesión en 3,6 s y después tarda 4,7 ms por
  recorte (CPU: 15 ms). Con CoreML, una entrada sin normalizar da scores todos
  NaN: por eso `estimator.py` asierta el rango de entrada y chequea NaN.
- ffmpeg 9: aun con `-fps_mode passthrough`, redondea los PTS al time base del
  encoder (1/fps); `-enc_time_base 1/90000` los conserva. Importa para la
  Fase 4 (master.mp4) y para cualquier retiming.
- **Métricas en cm** necesitan la altura declarada del atleta
  (`data/athletes/<slug>.yaml` con `altura_m`, o `--altura-m`); sin ella
  quedan en `null` con razón. La conversión usa la altura del cuerpo en px del
  cuadro de address.
- **Tabla del arnés (nivel 0, cámara `sin_verificar`, ruido 0,6 % de la altura
  del cuerpo, 16 semillas):** duraciones MDC ≈ 13 ms a 240 fps y `fps_min`
  120; sway/lift/thrust MDC 2,5–4,5 cm por repetición; sway sólo `face_on`,
  thrust sólo `down_the_line`, lifts ambas; **las deltas de flexión de rodilla
  mueren** (declaradas en `face_on`, la flexión ocurre en profundidad). Las
  tolerancias de sesgo (2 cm, 25 ms, 5°) y de MDC (5 cm, 30 ms, 15°) son
  estimaciones declaradas en `truth/kinelab_truth/harness.py`. El arnés sólo
  puede quitar vistas de las que el deporte declara, nunca agregar.
- La ganancia de velocidad angular (pelvis→tórax→brazo) se calcula desde el
  giro aparente de las líneas de cadera/hombros en el plano de imagen; NO está
  validada por el arnés (no es una métrica registrada) y desde `face_on` la
  rotación axial se ve como escorzo, no como giro: sospechosa. Queda en
  `summary.gain` como descriptiva hasta que el arnés la evalúe.

### Lo que sólo material real puede cerrar (abierto)

- Fase 0: filmar cronómetro y sesión; `capture-paths.yaml` sigue vacío.
- Fase 1: umbral de encuadre medido; que la convención de rotación dé 90 en
  un `.MOV` real en vertical; `creation_time` de QuickTime; el determinismo
  CoreML sobre un clip de golf; reporte SynthPose vs RTMPose (1.5, no hecho:
  SynthPose necesita torch, fuera de ADR-015 salvo en `truth/`).
- Fase 2: error contra GolfDB (2.5): la herramienta existe
  (`kinelab.tools.golfdb_eval`), el dataset no está descargado; todos los
  parámetros de `GolfEventParams` y `GOLF_SEGMENTATION` son estimaciones.
- La página `service/` no se abrió en un navegador: **probarla vos** (abajo).
- Fase 3: intrínsecos reales del teléfono (tablero); nivel 1 de validación
  (movimiento humano real) y SynthPose; oclusión y desenfoque no están en el
  barrido; mutation manual de la invariante 15 no hecha sistemáticamente.

### Para que pruebes vos (cuando quieras)

1. `.venv/bin/python -m service` y abrir http://127.0.0.1:8765. Sección 1:
   subir cualquier `.mov`/`.mp4` y ver la tabla de fps; sección 2 se habilita
   cuando `data/capture-paths.yaml` tenga un camino.
2. Con un clip de golf real ingestado (`gate: OK`):
   `.venv/bin/python -m kinelab.perception data/sessions/.../take-01` y después
   `.venv/bin/python -m kinelab analyze data/sessions/.../take-01`. Mirar
   `analysis.json`: `events[]` por repetición y `quality.verdict`.
3. Si un evento está mal: `python -m kinelab adjust TAKE --rep N --event top --frame F`.

### Entorno verificado

`python3.12` = 3.12.14 · ffmpeg / ffprobe 9.0.1 · onnxruntime 1.30.0
(CoreMLExecutionProvider) · rtmlib 0.0.16 · OpenCV 4.14.0.94 · numpy 2.5.3 ·
scipy 1.18.1 · pydantic 2.13.5 · fastapi 0.141.1 · Mac Apple M3 Pro.

### Siguiente

**Interfaz de exploración** (pedido de Hernán): una pantalla con un botón para
subir un video, que corra `python -m kinelab datos` y muestre el `overlay.mp4`
con un reproductor con cámara lenta y cuadro a cuadro, las fotos por evento y
toda la data en tablas. El prompt completo para esa sesión está en
`docs/prompts/interfaz-exploracion.md`. La página actual de `service/` no le
sirve y se reemplaza por una app Next.js en `web/`.

Con clips reales: pasarlos por percepción y análisis, medir el umbral de
encuadre, calibrar la cámara con tablero y re-correr el arnés. Sin clips: Fase 4
(servicio con jobs, `master.mp4` H.264 CFR, visor desde datos sobre
`service/`), y evaluar la ganancia en el arnés.

---

## Mensaje de arranque para la próxima sesión

> Estás en `/Users/heralc/Desktop/HDDev/kinelab`. Leé `AGENTS.md`, `CONTEXTO.md`,
> `DECISIONES.md`, `ESPECIFICACION.md`, `CONTRATO.md`, `CAPTURA.md`,
> `HERENCIA.md` y por último `ESTADO.md`. Regla de trabajo: creá con tests
> mínimos, sin navegador ni subagentes; yo pruebo el front y las corridas
> reales. Si hay clips reales en `data/sessions/`, empezá por pasarlos por
> percepción y análisis y decime qué sale. Si no, seguí con la Fase 4 según
> `ESTADO.md` §Siguiente. Commit al cerrar cada bloque; `ESTADO.md` al cerrar.
