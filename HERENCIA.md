# kinelab — Herencia

Dos prototipos anteriores, del mismo equipo, para pádel:

- **A** — `/Users/heralc/Desktop/HDDev/BMPadel/biomech/` · MediaPipe + Streamlit.
  Un clip, un golpe, un análisis. Tiene un catálogo de golpes con procedencia
  anotada por rango.
- **B** — `/Users/heralc/Desktop/HDDev/padel-coach/` · Next.js + FastAPI +
  SQLite + RTMPose-s. Producto completo de punta a punta, auditado con
  evidencia medida el 12 de septiembre de 2026.

Lo que sigue es qué se porta, qué no, y qué se aprendió pagando. Las
referencias `archivo:línea` son de esos repos en esa fecha.

---

## Se porta (con atribución al archivo y línea de origen, y con tests propios)

### De B, motor

| Pieza | Origen | Por qué sobrevive |
|---|---|---|
| Wrapper de pose sobre `rtmlib.Body` con detector cada N cuadros | `analyzer/padel_analyzer/pose.py:57-112` | ~55 líneas genéricas, nada de pádel adentro. |
| **Guardia anti cajas fantasma**: nunca pasarle el cuadro entero al estimador | `pose.py:89, 96-103` | Sin esto, RTMPose inventa un esqueleto sobre una cancha vacía y lo reusa varios cuadros. |
| Selección y seguimiento de un sujeto (más grande → cercanía → tope de salto 0,5 alturas → re-adquisición a 15 cuadros) | `pose.py:152-216` | La heurística es genérica; sólo el peso por pierna está sintonizado a cancha. |
| Relleno de huecos acotado: interpola rachas ≤ 5 cuadros, nunca extrapola bordes | `pose.py:219-246` | Función pura numpy sobre `(T, J, 2)`. |
| Cache de pose en disco + payload sin `NaN` | `posestore.py:23-70` | **La pieza clave del repo.** Desacopla percepción de métricas. |
| **Escala por cuadro** (`body_height_series`) | `kinematics.py:180-212` | Nació de un bug de ×2,8 (ver Cementerio). Robusta a agachadas y saltos. |
| Suavizado Savitzky–Golay con ventana derivada del fps, y velocidades normalizadas | `kinematics.py:327-408` | Correcto. Pero el corte del filtro pasa a ser parámetro explícito del JSON. |
| `locate_impact`: buscar el contacto dentro de una ventana de ±0,4 s alrededor del pico, no en el pico exacto | `events.py:100-120` | Corrige un error de diseño documentado (ver Cementerio). |
| Escritura de video robusta: `VideoWriter` → pipe `rawvideo` a ffmpeg | `overlay.py:57-171` | El OpenCV del venv no abre `mp4v`. |
| Clips por repetición con cámara lenta y pausa en el impacto, **en la misma pasada de decodificación** | `overlay.py:323-403` | Una sola decodificación para N clips. |
| Lámina comparativa de varias repeticiones normalizada por tamaño de cuerpo | `compare.py:92-153` | El mejor artefacto de coaching del repo. Para Fase 5. |
| Ajuste manual con recálculo completo desde la pose y escritura atómica | `adjust.py:132-234` | Conserva el valor detectado original. **Agregar** chequeo de colisión de cuadro (ver Cementerio). |
| Validación de rutas anti path-traversal, y sus 14 tests | `service.py:235-266`, `tests/test_service.py` | Lo mejor testeado del repo. |
| Sondeo de video y transcode de rescate si OpenCV no abre el archivo | `video.py:55-136` | Capacidad genérica nacida de un tropiezo. |
| Detección de cámara en movimiento con `phaseCorrelate` | `pipeline.py` | Avisó correctamente en 2 de 10 tomas. |
| Ensamblado del JSON con regla "un `null` nunca se omite" | `report.py:125-215` | Respetada de punta a punta. |
| CLI sin servidor | `__main__.py` | `python -m kinelab analyze …` |

### De B, web (Fase 4)

| Pieza | Origen | Nota |
|---|---|---|
| Transcodificación + sondeo con ffprobe | `web/src/lib/media.ts` | Prefiere `avg_frame_rate` sobre `r_frame_rate` — correcto — pero **ninguno es la verdad** (ver CAPTURA). |
| Servido de media con Range/206 | `web/src/app/api/media/[...path]/route.ts:58-127` | 206/416 correctos. Sin ETag. |
| Guardas de rol en toda la API | `web/src/lib/guard.ts` | Cubre también los archivos de video. |
| **Cuadro a cuadro real**: botones ◀▶, flechas, slider de paso 1 | `web/src/components/ImpactAdjuster.tsx:188-334` | **Es el único visor real del repo.** Se extiende; no se escribe otro. |
| Canvas sobre el video manejado por `requestVideoFrameCallback` | `web/src/components/PoseViewer.tsx:32-235` | El enfoque es correcto. Tres defectos a corregir al portar: dibuja el `t` **pedido** y no el `mediaTime` presentado (`:214`); `setTimeout(60)` fijo en vez de esperar el cuadro; un `setState` por cuadro presentado (`:103`). |
| Galería de repeticiones con descartar/restaurar | `RepGallery.tsx:27-202` | Reemplazó una tabla de 16 columnas ilegible. |
| Devolución del coach que sobrevive al refresh durante el análisis | `FeedbackForm.tsx` | Fase 5. |
| Modelo de datos SQLite + migraciones | `lib/db.ts`, `lib/schema.ts` | **Cambiar**: una sola versión de análisis por toma no alcanza. |

### De B, documentos

- La estructura de `CONTRACT.md` y, sobre todo, su sección **«Desviaciones»**.
  Es de donde salió casi todo el valor de la auditoría.
- `docs/COMO-LEER-EL-ANALISIS.md` como modelo de cómo explicarle un número al
  entrenador. El contenido se reescribe; el tono se conserva.
- `docs/ESTUDIO-MERCADO.md`: el relevamiento de competencia y el semáforo de
  herramientas. **Corregir** el semáforo: puso el retraso de cadena cinética
  en verde, "sale hoy".

### De A

- El **patrón** de `strokes.py`: cada rango de referencia con su procedencia
  anotada en el comentario (medido / literatura de tenis / estimación propia).
  Los números no se portan; la disciplina sí, y pasa a ser el campo
  `procedencia` del registro.
- `_detect_impacts` con `scipy.signal.find_peaks` y sus tres umbrales
  documentados (`distance`, `prominence`, `height` relativos al pico). Sirve
  como base de la segmentación; los umbrales se fijan midiendo.
- La honestidad del README sobre limitaciones. Mantener esa disciplina.

### Del scratchpad de la investigación → `banco/`

Scripts ya portados con rutas parametrizadas (`KINELAB_BENCH_DIR`):

- `fps_truth.sh` — la prueba de que el fps del archivo miente. Base de
  `kinelab/tools/fps_truth.py`.
- `bench.py`, `bench2.py` — RTMPose s/m/x/w por proveedor; baseline de 1 hilo
  comparable con i7-11700.
- `bench3.py` — CoreML fp16: entrada sin normalizar → `NaN`.
- `bench4.py` — bbox suelto vs ajustado sobre un frame real.
- `coreml_opts.py` — `MLComputeUnits`: la ganancia no viene del Neural Engine.
- `threads.py` — saturación en 5 hilos.
- `scale_sweep.py` — sujeto de 512 a 35 px: los keypoints se mueven < 1,8 px.
- `degrade.py` — desenfoque de 21 px y su efecto por modelo.

Necesitan los modelos ONNX en `$KINELAB_BENCH_DIR/models/` (se descargan una
vez, se fijan por hash).

---

## Prohibido portar (bajo ningún nombre)

| Pieza | Origen | Por qué |
|---|---|---|
| `references.py` y el `score` | B `references.py:20-199` | Ningún rango viene de un estudio citado; el score dio 38–58 en todo y 58 a un hombre hablando. Los chequeos que pasan son los que aprueba una persona parada. |
| `kinetic_chain_lag_ms` | B `events.py` | El 80% de las lecturas reales es 0 ms: el piso de cuantización, no una medición. Y el orden no discrimina nivel ni en tenis ni en golf. |
| `shoulder_rotation_deg` desde una cámara de costado | B `kinematics.py:93-101` | Geométricamente degenerada en la vista que el propio proyecto recomendaba: 2–23° reales contra 15–60° esperados. |
| Observaciones en texto autogeneradas | B `metrics.py:205-300` | Bien escritas, y por eso peligrosas: describen con seguridad números que no la merecen. |
| Centro de pala por extrapolación del antebrazo ×1,7 | B `kinematics.py:124-140` | La calibración sobre "27 impactos" no es reproducible: no hay script, dato ni test. Con el codo cerrado dibuja la pala sobre la cabeza. En golf, el shaft se detecta. |
| El criterio de fase "25% del pico de velocidad" | A `app.py`, B `events.py` | Sin respaldo en ninguna fuente. El método validado es la inflexión de la segunda derivada. |
| Los rangos numéricos de `strokes.py` | A | Tenis prestado y estimación propia, contra un estimador con ±25° de error. |
| El video anotado pre-renderizado como vista principal | A y B `overlay.mp4` | Irreversible por toma: no se puede apagar, ampliar ni recorrer sin volver a renderizar. |
| Un segundo visor | B `PoseViewer.tsx` como componente separado | Había que extender el que tenía cuadro a cuadro. Se porta su técnica, no su existencia aparte. |
| Aumentador de marcadores LSTM de Stanford (`marker-augmentation`, `Pose2Sim/markerAugmentation.py`) | externo | El preprint que lo cita mide al modelo original en **40,4° de error medio y 252° de máximo** fuera de su distribución de entrenamiento. Un swing es el caso fuera de distribución por excelencia. Y no funciona con COCO-17. |
| Sports2D como motor | externo | Declara validez sólo para movimiento en un plano 2D filmado en paralelo; un swing queda fuera. `process()` no devuelve nada; 2.706 líneas en una función; sin detección de eventos; `except` desnudo que devuelve `NaN`; un test sin aserciones; Alpha. Sí se pueden vendorizar piezas BSD-3 sueltas — **excepto** `convert_px_to_meters`, que depende de una tabla de profundidades hardcodeada y tiene un bug de factor 10.000 en la versión de PyPI. |

---

## Cementerio

Lo que se intentó y falló, con la lección. Cada entrada le ahorra días al que
viene.

### Supuestos que resultaron falsos

**1. Que el material podía esperar.** Ninguno de los dos prototipos tuvo un solo
video real del deporte. B se validó con descargas de YouTube (tres con
`handler_name = "ISO Media file produced by Google Inc."`), una de ellas un
hombre hablando a cámara durante 337 s del que salieron 19 "bandejas", y un
recorte de un `overlay.mp4` anterior re-analizado — el analizador corrió pose
sobre su propio dibujo. **Lección:** la Fase 0 es el material.

**2. Que el fps del archivo era un dato.** Las tomas de B iban de 8,33 a 60 fps
y el código calculaba igual. **Lección:** fps como compuerta, tasa real por
cronómetro.

**3. Que un ángulo absoluto era una medición.** En B, mover el impacto dos
cuadros a 60 fps cambió el codo hasta 25,6°; había codos de 2,5° y 5,2°
entrando al promedio. **Lección:** delta intra-repetición, plausibilidad
anatómica antes del promedio, MDC antes del juicio.

**4. Que la secuencia cinemática era la métrica estrella.** Retractada dos
veces: en tenis (los pros picotean la pelvis después del tronco) y en golf
(47 golfistas a 240 Hz: el timing no varía con el nivel). **Lección:**
ganancia, no orden.

**5. `rtmlib.PoseTracker` como tracker.** Cuando no había cajas le pasaba el
cuadro entero al estimador, que inventaba un esqueleto y lo reusaba cuatro
cuadros. Reemplazado por un lazo propio en B `f773364`. **Lección:** una
librería puede tener un modo de degradación silencioso peor que no tener
nada.

**6. Una sola mediana de altura de cuerpo para todo el video.** En B daba
135 px de mediana con el jugador midiendo 380 px en el impacto: error de
×2,8, "altura de contacto = 291% del cuerpo". **Lección:** la más
transferible de todas — una constante de normalización estimada una vez no
falla: devuelve números plausibles multiplicados por un factor. Lo delató un
valor imposible.

**7. Evaluar la regla del golpe en el cuadro exacto del pico de velocidad.** En
un golpe aéreo el pico cae en el acompañamiento, con la mano ya bajo el
hombro: la regla tiraba el golpe real y dejaba un pico peor. **Lección:** un
filtro booleano en un instante mal elegido no pierde el golpe, lo reemplaza.

**8. Que altura de contacto ≈ 1,0 era la cabeza.** Error de factor 2 en la
interpretación de la propia unidad; todas las observaciones sobre altura de
contacto fueron falsas mientras duró. **Lección:** cada unidad normalizada
lleva su definición de divisor y origen escrita al lado.

**9. Que un modelo más grande arreglaría los ángulos imposibles.** Medido: no.
El bbox y el desenfoque mueven el codo más que el tamaño del sujeto, y tres
modelos discrepan 13,6° en el mismo cuadro. **Lección:** calidad de bbox y
plausibilidad, no checkpoint.

**10. Que la homografía de la cancha daría metros del cuerpo.** Con la cámara a
1,4 m proyecta una cadera a 4 m como si estuviera a 12,4 m, y la muñeca queda
por encima del horizonte. **Lección:** homografía sólo para los pies; el
cuerpo se normaliza por sí mismo.

**11. Que el presupuesto de rendimiento era de esta máquina.** Toda la elección
de modelo de B se hizo con números de una MacBook Intel; la máquina real es un
M3 Pro donde `rtmpose-m` en CoreML es más rápido que `rtmpose-s` en CPU.
**Lección:** medir en la máquina y con el proveedor que se va a usar.

### Bugs concretos que quedaron en B

- **El ajuste manual permite dos repeticiones en el mismo cuadro**
  (`adjust.py:167` sólo acota a `[0, n−1]`). Pasó: dos repeticiones con
  `t_impact` idéntico, métricas idénticas, y el resumen reportó desvío 0,0°
  como consistencia perfecta.
- El visor dibuja el esqueleto del cuadro pedido sobre la imagen del cuadro
  presentado, sin aviso (`PoseViewer.tsx:214`).
- El enlace al visor no está condicionado a que exista `pose.npz`
  (`RecordingDetail.tsx:310`).
- La leyenda de la estroboscópica se dibuja superpuesta e ilegible; el trazo
  incluye saltos del tracker que nada filtra.
- Un `RuntimeWarning` de numpy se escapa por una ruta no cubierta por la
  supresión de `kinematics.py:257-261`.

### Trampas de interfaz ya pagadas

- Caja fija 16:9 para video vertical de celular: quedaba diminuto entre
  franjas negras.
- Slider de impacto con rango fijo de ±1 s: a 60 fps eran 120 pasos y un
  píxel de arrastre saltaba varios cuadros; y su rango se derivaba de su
  propio valor, recentrándose al arrastrar.
- Escribir un `ref` de React durante el render para pasar banderas al lazo de
  canvas: viola las reglas de hooks.
- `requestAnimationFrame` como sincronización principal: puede ir un cuadro
  desfasado. Sólo como fallback.
- "No sé" como pase libre: la regla de volea aceptaba cualquier pico cuando no
  podía estimar hacia dónde miraba el jugador. **Lección:** cada rama de dato
  faltante necesita su regla degradada, o las tomas peor filmadas son las que
  más falsos generan.
- La tabla de 16 métricas como vista principal: ilegible y escondía la acción
  de descartar. Cada métrica nueva degrada la vista que las lista todas.

### Gotchas de entorno

- El Python de python.org no trae raíces de certificados: `SSL_CERT_FILE` a
  `certifi` antes de importar `rtmlib`, o la descarga de modelos falla.
- `cv2.VideoWriter` con `mp4v` no abre en el OpenCV del venv (sólo
  AVFoundation). De ahí el pipe a ffmpeg.
- Dos OpenCV instalados a la vez en el venv de B (`opencv-contrib-python
  5.0.0.93` y `opencv-python 4.14.0.94`), y `requirements.txt` pinneaba sólo
  uno. El venv no coincidía con las dependencias declaradas.
- Nombres de variables de entorno de ffmpeg distintos entre analyzer
  (`FFMPEG`) y web (`FFMPEG_PATH`); el README documentaba sólo los de la web.
- `rtmlib.Body` no acepta `det_frequency` (0.0.16), contra lo que el contrato
  asumía. Dos vueltas de diseño por una firma.
- Los WebM de `MediaRecorder` traen `r_frame_rate` poco confiable (p. ej.
  `1000/1`).
- CoreML: sesión de 0,9 s (s), 1,7–2,0 s (m), 4,4 s (x) al crear por
  compilación. Reusar la sesión y habilitar el cache de modelos.
- El `bpy` de Blender para macOS arm64 exige Python 3.13 exacto. El arnés de
  verdad tiene su propio entorno por esto también.

### Lo que la investigación descartó antes de construirlo

- Detección automática de líneas de cancha en pádel: la única herramienta
  publicada declara que falla en vistas a nivel de cancha, que es el setup
  exacto.
- World landmarks 3D de MediaPipe como escala: son root-relative, no dan
  posición en la escena ni tamaño real, y son la fuente principal de error del
  modelo.
- Render sintético completo para validar: produce un piso optimista por el
  sim-to-real gap; ninguno de BEDLAM, AGORA ni SURREAL tiene golf ni pádel.
- Tempo 3:1 como objetivo; X-factor en cualquiera de sus formas; velocidad de
  muñeca absoluta en m/s desde homografía.
