# kinelab — Decisiones (ADRs)

Las decisiones de acá están cerradas. Cada una tiene la evidencia que la
sostiene. Reabrir una es escribir un ADR nuevo que cite al viejo, nunca
trabajar alrededor.

Procedencia de la evidencia: **[aquí]** medido en la Mac de este proyecto (Apple
M3 Pro) con scripts reproducibles en `banco/`; **[pares]** literatura revisada
por pares; **[fabricante]** autovalidación publicada por un vendedor;
**[auditoría]** la auditoría con evidencia medida del prototipo `padel-coach`.

---

## ADR-001 · Motor agnóstico al deporte; el deporte es configuración

**Decisión.** `kinelab/` no contiene ninguna constante, umbral, nombre de gesto
ni rango de referencia de ningún deporte. Todo eso vive en `sports/<deporte>/`.

**Por qué.** La investigación de golf lo validó de forma explícita: lo que
cambia entre golf y pádel no son los algoritmos, sino la lista de vistas
obligatorias, el gate de encuadre y fps, las definiciones de evento y las
métricas permitidas por vista. Todo eso es config. Lo que **no** es config y
va al núcleo son dos primitivas transversales: propagación de incertidumbre
desde ±1 cuadro, y repetibilidad entre repeticiones.

**Consecuencia.** Agregar pádel es escribir `sports/padel/`, no tocar el motor.

---

## ADR-002 · Golf primero

**Decisión.** El primer deporte es golf. Pádel sólo después de que golf v1
tenga MDC medido para todas sus métricas de nivel 1.

**Por qué.** No por la biomecánica: por la física de la captura.

- **Luz.** [aquí] A 240 fps la exposición está topeada en 1/240 s; con buen
  encuadre la mano de un swing a 10 m/s barre 21 px en un cuadro. Bajar a 5 px
  exige 1/1000 s. Al aire libre con 20.000 lux el teléfono llega solo a
  1/2000 s. Una pista de pádel indoor a 500 lux (clase II EN 12193) exige
  ISO 3200 para lo mismo: ruido de sensor donde se mide.
- **Encuadre.** El golfista está quieto: el cuerpo puede ocupar 80–90% del
  cuadro. [auditoría] El prototipo de pádel medía al jugador al 11–16% del alto
  (116–135 px de cuerpo), y ahí dos píxeles de error en el codo son grados.
- **Vistas.** Face-on y down-the-line son el estándar de enseñanza y se
  obtienen a voluntad porque el gesto se repite. [auditoría] El pádel forzó
  perfil puro y colapsó la rotación de hombros a 2–23° contra un rango
  esperado de 15–60°.
- **Ground truth.** [pares] GolfDB: 1400 clips con 8 eventos etiquetados cuadro
  a cuadro con definiciones geométricas. En pádel no existe nada comparable a
  fps útiles.
- **El implemento.** Un shaft de 1066–1219 mm es un segmento largo ajustable a
  un modelo de línea; una pala de 45,5 cm no tiene geometría que ajustar.

---

## ADR-003 · Captura con la cámara nativa, en modo Video, con cronómetro

**Decisión.** Protocolo completo en `CAPTURA.md`. Lo esencial: cámara nativa
del teléfono, **modo Video 1080p120 HEVC** (no Slo-Mo), transferencia por
AirDrop con "Mantener originales", y **calibración con cronómetro filmado**
de cada combinación modo + camino antes de aceptar un solo clip.

**Por qué.**

- [pares] iPhone 17 Pro y 18 Pro graban 1080p120 como video normal (spec de
  Apple). Es CFR a tasa de captura, sin edit list, sin sidecar, sin retiming.
- [aquí] El fps del contenedor no distingue "preservado pero ralentizado" de
  "destruido": un clip de 240 fps estirado 8× reporta `r_frame_rate=30` y
  `avg_frame_rate=30,05`, idéntico a un clip realmente remuestreado, con
  deltas de PTS idénticos. Sólo el conteo de cuadros contra duración real los
  separa. Por eso la tasa real es configuración calibrada, no inferencia.
- Dos trampas silenciosas: "Más compatible" (H.264) deshabilita 240 fps por
  completo; "Transferir a Mac o PC: Automático" autoriza transcodificar.
- [sin verificar] Reportes de Slo-Mo nominal de 240 fps grabando 114–227 fps
  reales en iPhone 12–15. El cronómetro los detecta; la confianza en el nominal
  no.

**Consecuencia.** Android queda fuera del POC (hornea la ralentización en el
archivo). GoPro queda fuera hasta que el arnés pueda medir el sesgo de su lente.

---

## ADR-004 · Percepción: `rtmlib` + RTMPose-m + Halpe26 sobre CoreML

**Decisión.** Estimador `rtmpose-m` con conjunto de keypoints **Halpe26**, vía
`rtmlib`, con `CoreMLExecutionProvider` y caída a CPU. `intra_op_num_threads=5`.
Pesos fijados por hash en local. Detector entrenado en COCO (no el de Human-Art
por defecto). En paralelo, para el arnés, `SynthPose ViTPose-B` como segundo
estimador independiente.

**Por qué.**

- [aquí] `rtmpose-m` en CoreML: 3,65 ms por recorte, 2,5× más rápido que
  `rtmpose-s` en CPU (9,31 ms), y +3,6 AP. El compromiso que justificaba el
  modelo chico en el prototipo anterior se midió en una MacBook Intel y no
  existe en esta máquina.
- [aquí] El proveedor de CPU del M3 Pro es 6,5× **más lento** por hilo que los
  números publicados de un i7-11700. Todo el margen viene de CoreML — y no del
  Neural Engine (con `CPUOnly` da igual): son los kernels fp16.
- [aquí] Lo que justifica `m` no es el AP: la sensibilidad del codo a un bbox
  mal encuadrado baja de −14,5/+13,6° a −9,7/+0,4°, y la degradación por
  desenfoque de 21 px baja de −5,2° a −2,5°.
- Halpe26 agrega centro de pelvis, cuello, cabeza, talones y puntas de pie con
  el mismo backbone y costo. Wholebody-133 descartado: 8,6× más caro, agrega
  cara y manos, no agrega columna, y arrastra Human-Art y UBody.
- [pares] El conjunto de keypoints pesa más que el modelo: en OpenCapBench,
  COCO-17 da 23,4° de RMSE en flexión de cadera y 39,1° en tobillo; keypoints
  tipo mocap (SynthPose) bajan a 8,3° y 6,2°. De ahí el segundo estimador.

**Consecuencia.** `pose.npz` guarda proveedor, checkpoint (sha256), versión de
onnxruntime, tamaño de entrada y conjunto de keypoints. El determinismo se
afirma sólo por proveedor.

---

## ADR-005 · Arquitectura en cinco piezas con un contrato en el medio

**Decisión.** `kinelab/` (motor puro) · `sports/` (config) · `truth/` (arnés,
entorno propio) · `service/` (FastAPI local, delgado) · `web/` (Next.js). El
contrato (`CONTRATO.md`) es la única interfaz entre motor y todo lo demás.

**Por qué.** [auditoría] La única pieza de `padel-coach` que la auditoría marcó
como "la clave del repo" fue exactamente esta separación: la pose guardada en
`pose.npz` y todo lo demás recalculado desde ahí en milisegundos. Permite
reconstruir el motor de medición sin volver a tocar el modelo ni el video.

---

## ADR-006 · Almacenamiento: `pose.npz` + `analysis.json` + `capture.json`

**Decisión.** Por sesión: `original.<ext>` intocable, `capture.json` escrito por
la ingesta, `master.mp4` para reproducción, `pose.npz` con la percepción cruda,
`analysis.json` por capas. Índice en SQLite. Sin parquet.

**Por qué.** [aquí] 30 s a 240 fps son 32 MB en JSON ingenuo y 3,8 MB en `.npz`
float32, con lectura de 243 ms contra 4 ms. Parquet, con 132 columnas cortas,
tardó 3,2 s: gana con muchas filas y pocas columnas, no con este layout.
float64 aporta precisión siete órdenes por debajo del ruido del modelo.

---

## ADR-007 · Métricas por niveles y la regla del MDC

**Decisión.** Toda métrica tiene un nivel (1, 2, 3) y un MDC medido en el
arnés. **Si el MDC no existe o es mayor que el ancho del rango con el que se
juzga, la métrica no se muestra como juicio.** Nivel 3 no se construye.

**Por qué.** Tres líneas de evidencia independientes convergen:

- [pares] Ángulos absolutos desde pose monocular: 21,5–32,7° de error medio en
  codo, 9,3–26,3° en rodilla (benchmark de 11 estimadores). Umbral clínico: 5°.
- [auditoría] Mover el frame de impacto 2 cuadros a 60 fps cambia el codo
  hasta 25,6°. El rango con el que se lo juzgaba era 140–176°.
- [auditoría] El puntaje 0–100 del prototipo dio 38–58 en todo, y 58 —el más
  alto— a un video de un hombre hablando a cámara. Los chequeos que pasaban
  eran los que también aprueba una persona parada.

**Lo que sí está por encima del piso:** tiempos (error = cuantización de
cuadros, milisegundos), desplazamientos lineales (0,5–1,8 cm), y
repetibilidad (inmune al sesgo sistemático). Ver `CONTRATO.md` §Niveles para
la lista de golf.

---

## ADR-008 · Eventos: definiciones de GolfDB, Address determinista, Top por inflexión

**Decisión.** Las 8 definiciones geométricas de evento de GolfDB se adoptan
textualmente en `sports/golf/`. Address se define como el último cuadro de una
ventana pre-movimiento estable. Top se detecta por inflexión de la segunda
derivada de la velocidad filtrada del shaft (o de la muñeca dominante), no por
umbral porcentual ni por clasificación de cuadro. Toda métrica anclada a
evento lleva ±1 cuadro propagado. Si dos picos de velocidad caen dentro de ±2
cuadros, cualquier orden entre ellos se reporta como `indeterminado`.

**Por qué.**

- [pares] SwingNet detecta Impact al 98,4% y Mid-downswing al 98,1% — anclas
  confiables — pero Address al 31,7% y Finish al 26,5%. Address es donde vive
  el cero de sway, lift y cabeza: no puede depender de una detección.
- [pares] Top se degrada en slow-motion (75,7% contra 90,8%) porque la
  transición se vuelve más fluida. La inflexión de la derivada no tiene ese
  problema.
- [pares] Fases por inflexión de segunda derivada: ICC 0,968–0,987 contra
  anotación manual. El criterio "25% del pico" del prototipo anterior no tiene
  respaldo en ninguna fuente.
- [fabricante] Onform, líder del mercado, reporta 94,6% de acierto en el orden
  de picos **después** de excluir los que caen a menos de 2 cuadros a 120 fps.
  Se copia la exclusión.

---

## ADR-009 · Validación en escalera; el paso cero es el conjunto de keypoints

**Decisión.** Cuatro niveles: (0) cadena cinemática propia proyectada con
cámara virtual de intrínsecos **medidos**; (1) movimiento humano real de
licencia limpia (CMU Mocap, ASPset-510); (2) error del estimador contra mocap
óptico (OpenCapBench, MIT); (3) render sintético completo — **no se hace**.
Antes de todo: correr SynthPose en paralelo sobre los clips existentes.

**Por qué.** Proyectar puntos 3D mide la matemática, no el estimador. Y hay un
tercer error que domina y que la verdad sintética **no puede ver**: el
desajuste de definición entre lo que COCO llama "hombro" y el centro
articular. Renderizar video lo esconde mejor todavía, porque ground truth y
predicción comparten la definición por construcción. El nivel 3 produce un
piso optimista por el sim-to-real gap.

**Formato de reporte, fijado ahora:** interno MPJPE y PCK; al entrenador,
RMSE en grados, sesgo con límites de acuerdo de Bland-Altman, y MDC.

---

## ADR-010 · Licencias: tres preguntas por pieza

**Decisión.** Antes de agregar cualquier dependencia se contesta por separado
la licencia del código, la de los pesos y la del dataset de entrenamiento.

| Pieza | Licencia | Veredicto |
|---|---|---|
| `rtmlib`, RTMPose (código) | Apache-2.0 | Sí. Única dependencia de pose. |
| SynthPose ViTPose, ViTPose++ (código y pesos) | Apache-2.0 | Sí. Segundo estimador del arnés. |
| OpenSim, MMPose, `opencap-core` | Apache-2.0 | Sí. OpenSim es arm64 aunque el wheel diga universal2. |
| Sports2D, Pose2Sim | BSD-3 | Sí para vendorizar piezas sueltas con tests propios. **No** como motor (ver HERENCIA). |
| ByteTrack, BoT-SORT, `supervision` | MIT | Sí, desde los repos originales, para multi-persona. |
| ASPset-510 | CC0-1.0 | Sí. Único dataset deportivo sin restricción. |
| CMU Mocap | libre | Sí. Tiene golf. |
| OpenCapBench | MIT | Sí, como arnés. Sus datasets son no comerciales. |
| **Detectores por defecto de `rtmlib`** | CC BY-NC-SA 4.0 (Human-Art) | **No para comercial.** Reemplazar por YOLOX entrenado en COCO. |
| **SMPL / SMPL-X** | no comercial | **No.** Veta toda la familia de reconstrucción por malla: WHAM, HMR, 4D-Humans. |
| **AMASS** | no comercial, sin redistribución | **No.** |
| `boxmot` | AGPL-3.0 | **No.** Aunque ByteTrack y BoT-SORT originales sean MIT. |
| Ultralytics / YOLO | AGPL-3.0 | **No.** |
| Sapiens (pesos) | CC-BY-NC-4.0 | **No.** |
| `opencap-monocular` | PolyForm NC | **No.** Distinto de `opencap-core`. |
| GolfDB, SwingNet | CC BY-NC 4.0 | Sólo para **medir** el error propio. Nunca para entrenar. |
| Kinovea | GPL-2.0 | Usar como herramienta sí; enlazar o derivar código, no. |
| Marker-augmentation LSTM de Stanford | Apache-2.0 | **No portar:** 40,4° de error medio fuera de distribución, y no funciona con COCO-17. Ver HERENCIA. |

---

## ADR-011 · Tests obligatorios en el motor, en cuatro capas

**Decisión.** (1) Fixtures analíticos: landmarks construidos con trigonometría,
ángulos en 37°, 112°, 163° y barrido 1–179°, velocidad constante conocida.
(2) Property-based con Hypothesis: invariancia a traslación, escala uniforme,
rotación rígida; simetría `angle(a,b,c) == angle(c,b,a)`; rango [0, 180].
(3) Metamórficos sobre el pipeline: espejar → mismos ángulos con lateralidad
invertida; reescalar → normalizadas iguales; duplicar fps por interpolación →
mismos ángulos por repetición; concatenar el clip consigo mismo → doble de
repeticiones idénticas; persona quieta → cero repeticiones. (4) Goldens sobre
2–3 clips cortos commiteados, con tolerancia justificada por clave (0,5° en
ángulos, ±2 cuadros en eventos, 5% en velocidades), un `.md` hermano con
quién lo verificó, y `--force-regen` prohibido en CI. Y mutation manual: los
cuatro bugs inyectados de la invariante 15.

**Por qué.** [auditoría] Los 64 tests de `padel-coach` no verificaban ningún
ángulo fuera de 0/90/180, tenían tautologías que reescribían la fórmula, cero
goldens, ningún test que leyera un video y produjera un `analysis.json`, y
ningún test negativo — de ahí las 19 "bandejas" en un hombre hablando.

---

## ADR-012 · Sin puntaje, sin veredicto textual, sin rangos sin procedencia

**Decisión.** No hay número único de calidad. No hay observaciones en texto
generadas por el motor en v1. Ningún rango de referencia entra sin
`procedencia` declarada y sin la definición exacta de landmarks, plano de
proyección e instante de cálculo.

**Por qué.** [auditoría] Las observaciones del prototipo estaban bien escritas y
por eso eran peligrosas: describían con seguridad números que no la merecían.
[pares] El X-factor tiene dos definiciones incompatibles en la literatura
(torso-vs-pelvis ≈ 30°, hombros-vs-pelvis ≈ 60°): un rango sin su definición
está mal por un factor de dos. [pares] El tempo 3:1 no es un hecho: el tour
medido va de 2,80 a 5,60, y el orden por nivel está invertido respecto del
mito (hcp 25 → 1,92:1; colegial → 3,44:1). [fabricante] El esquema de Onform
(verde = media ± 1 SD del top-10) deja fuera por construcción al 32% de los
propios profesionales.

---

## ADR-013 · Herencia: portar las joyas, con atribución; no reescribir

**Decisión.** Las piezas listadas en `HERENCIA.md` §Se porta se copian con
atribución al archivo y línea de origen y se envuelven en tests propios. Las
piezas de §Prohibido no se portan bajo ningún nombre.

**Por qué.** [auditoría] `padel-coach` resolvió con código real problemas caros
— cajas fantasma, escala por cuadro, escritura de video, clips en una pasada,
validación de rutas — y su capa de medición es la que hay que rehacer. Portar
es más barato y más seguro que reescribir, y la atribución preserva el
contexto de por qué existe cada pieza.

---

## ADR-014 · Un solo visor, desde datos

**Decisión.** Se extiende el cuadro-a-cuadro real de `ImpactAdjuster` con el
canvas-sobre-video de `PoseViewer`. Dibujo **sólo** dentro de
`requestVideoFrameCallback`, con el `mediaTime` presentado. Seek a
`(n + 0,5) / fps` con verificación del cuadro llegado. Video y canvas dentro
del mismo wrapper transformado para zoom. Capas conmutables.

**Por qué.** [auditoría] El prototipo dejó dos visores a medias: uno con
frame-stepping real y sin overlay, otro con overlay y sin frame-stepping, y el
segundo dibujaba el esqueleto del cuadro pedido sobre la imagen del cuadro
presentado, sin avisar. Chrome como navegador soportado en v1; HEVC del iPhone
no se reproduce de forma portable, de ahí el `master.mp4` en H.264 CFR.

---

## ADR-015 · Stack cerrado

Python 3.12 · `rtmlib` · onnxruntime con CoreML EP · OpenCV · numpy · scipy ·
pydantic · FastAPI + uvicorn · pytest + hypothesis + pytest-regressions ·
ffmpeg/ffprobe 9 · Node 22 · pnpm · Next.js 16 (webpack) · React 19 ·
Tailwind 4 · Drizzle + better-sqlite3. `truth/` tiene su propio `pyproject`
y puede agregar lo que necesite sin tocar el del motor.

Nada más sin un ADR nuevo.

---

## ADR-016 · Caminos de captura declarados sin calibrar

**Decisión.** `capture-paths.yaml` admite caminos con `calibrated: false`:
dispositivo y modo declarados por el usuario, sin cronómetro. Sólo
`mode: video`. Para ellos `fps_real` se asume igual al `fps_playback` efectivo
(`stretch_factor` 1,0) con procedencia `sin_verificar`, y esa procedencia viaja
a `capture.json`, al `header` de `analysis.json` y a cada métrica: ninguna
métrica de un camino sin calibrar puede ser juicio (`judgment_allowed` lo
exige), y el informe lo dice antes de cualquier número. Un camino `slomo` sin
calibrar se rechaza con razón: sin cronómetro el factor de estiramiento es
desconocido y cualquier tiempo es ficción. Existe un camino genérico
`desconocido-video` para "no sé con qué se filmó". Filmar el cronómetro del
mismo dispositivo y modo convierte el camino en calibrado, y los clips se
re-analizan (invariante 18) sin volver a correr el modelo (invariante 1).

**Por qué.** El entrenador no tiene el iPhone de `CAPTURA.md`; tiene un Galaxy
S22 Ultra. ADR-003 dejó Android fuera por la ralentización horneada del modo
slow motion; el modo Video no la tiene (medido en el original de 9 s: 265
cuadros CFR a 29,998 fps tras el delta de arranque, informe del 03). Lo que el
archivo dice de sí mismo se usa; lo que no puede decir se declara como supuesto
visible, nunca se infiere. Sustituye en parte a ADR-003: Android entra como
camino declarado; como camino calibrado, sólo con cronómetro.

**Tres cosas que el código obligó a precisar** (informe
`docs/informes/2026-09-14-06-camino-declarado.md`):

- Un camino declarado puede no saber ni el fps nominal ni el codec:
  `nominal_fps` y `codec_expected` pasan a ser opcionales, y el genérico
  `desconocido-video` los tiene en `null`. `codec_matches_path` queda sin
  evaluar cuando el camino no declara codec; los seis campos del cronómetro
  (`fps_real`, `fps_playback`, `stretch_factor`, `fps_method`,
  `calibrated_on`, `calibrated_by`) tienen que estar en `null` o el archivo no
  carga: declarar no es medir.
- **El modo exploración no corre el gate: ahí la procedencia es siempre
  `sin_verificar`, incluso con un camino calibrado**, porque nadie verificó que
  el archivo vino por ese camino (eso lo hace `fps_matches_path`). Los números
  del cronómetro sí se usan si el camino los tiene — descartarlos daría tiempos
  ×8 mal en un Slo-Mo —, pero no habilitan juicio.
- El gate rechaza igual lo que tiene que rechazar. Medido en el original del
  S22 con `s22ultra-video-fhd30-cable`: 8 de 9 chequeos pasan (por primera vez
  `capture_path_known` entre ellos) y el único fallo es `fps_min_for_gesture`,
  30 fps contra los 100 que pide golf. Declarar el camino no ablanda ningún
  umbral: sólo deja escrito bajo qué supuesto se midió.

**Consecuencia.** Invariante 2 queda: "calibrada con cronómetro, o declarada
sin calibrar con procedencia `sin_verificar` y sin juicio (ADR-016)".

---

## ADR-017 · El top es el cambio de sentido más lejano, no el último

**Decisión.** Entre address e impacto, el top es el cambio de sentido de la
velocidad de las manos proyectada sobre el eje principal de la trayectoria en
el que las manos están **más lejos** de su posición de address —distancia en el
plano de imagen—, no el último. Es la misma distancia cuyo **mínimo** define el
impacto: una sola señal, dos eventos. Vale en las dos vistas. En código:
`kinelab.events.primitives.direction_change_farthest`, y el evento lo dice en
su `method` (`direction_change_farthest`). Reabre la parte de ADR-008 que
elegía el último; todo lo demás de ADR-008 sigue en pie.

**Por qué.** [aquí] El mismo swing de mocap (CMU 64_01, 448 cuadros a 120 fps)
proyectado con la cámara virtual del arnés desde las dos vistas, con la verdad
3-D al lado (`truth/kinelab_truth/mocap.py`, `events_3d`, criterio `top_far`):

| | cambios de sentido entre address e impacto | último | más lejano | verdad 3-D |
|---|---|---|---|---|
| 64_01 `face_on` | 144 (1 px), **270** (795 px) | 270 | 270 | 269 |
| 64_01 `down_the_line` | 158 (5 px), **263** (756 px), 327 (89 px) | 327 | **263** | 269 |
| 64_02 `face_on` | 181 (4 px), **305** (773 px) | 305 | 305 | 306 |
| 64_02 `down_the_line` | **304** (781 px), 373 (87 px) | 373 | **304** | 306 |

Desde `face_on` el eje principal está a ~63° de la vertical y hay dos cambios:
el último **es** el más lejano y las dos reglas coinciden. Desde
`down_the_line` el movimiento hacia el objetivo cae sobre el eje óptico, el
eje queda casi vertical, y aparece un tercero: el fondo del arco de bajada,
justo antes del impacto, a 89 px del address contra 756 px del top. Ganaba por
ser el último, y el downswing salía de **41,7 ms** (5 cuadros) en 64_01 y
**25,0 ms** en 64_02. Con la regla nueva el error del top desde esa vista pasa
de **+58 y +67 cuadros a −6 y −2**, y las duraciones dejan de ser ficción:
backswing 975,0 / downswing 575,0 ms contra los 1033,3 / 508,3 de la verdad
3-D. **El top estaba en la señal; lo perdía la regla.**

La versión continua de la definición de GolfDB —*"el instante en que el palo
cambia de dirección"*— es "se invierte el sentido **en lo más alto del
recorrido**", no "se invierte por última vez". Y coincide con `top_far`, el
criterio que el arnés ya usaba sobre las curvas 3-D desde el informe del 07.

**Lo que la regla no arregla, medido.** En los cuatro clips reales del Galaxy
S22 (todos `face_on`) el top se mueve 4–6 cuadros más temprano en tres de
ellos. La causa no es la regla: la señal es el **centro de las dos muñecas**, y
en el top la muñeca izquierda se pierde (confianza 0,34–0,54, saltos de hasta
300 px entre cuadros). Con la muñeca derecha sola —la que el modelo nunca
pierde en estos clips— hay **un solo** cambio de sentido y las dos reglas dan
**el mismo cuadro** en los cuatro: `cortado.mp4` 36, `20260907_170638.mp4` 139,
`vid1.mp4` 722, `vid2.mp4` 114. Contra esa referencia, la regla vieja erraba
+3 / +2 / +4 / +1 cuadros y la nueva −3 / −2 / **0** / +1. Donde la señal está
limpia las dos reglas coinciden; donde no, ninguna de las dos es una medición.
La calidad de la señal de manos es problema aparte y sigue abierto.

**Consecuencias.**

- La primitiva vieja (`direction_change`, "el último") **no queda en el
  motor**: se reemplaza por `direction_changes`, que enumera, más el selector.
  Una regla reabierta que sigue disponible vuelve sola.
- El primer segmento —de `after` a `after + 1`— no cuenta como cambio de
  sentido: devolvería el propio cuadro del address. [aquí] Sin ese borde, el
  segundo candidato de `vid1.mp4` (un movimiento que no es un swing) inventaba
  una repetición con top = address = 862 y backswing de 0 ms, donde antes se
  rechazaba con `sin_top`.
- Los `analysis.json` ya escritos **no se recalculan solos** (invariante 18).
  Re-analizar una toma los reescribe desde `pose.npz`, sin volver a correr el
  modelo (invariante 1), y conserva el anterior con su `engine_version`.
- Toda métrica anclada al top se mueve con él: medido en los clips reales,
  1,7–5,9 cm en los desplazamientos de pelvis, tórax y cabeza en el top. El
  top es el cero de esas métricas tanto como el address.
- **Queda anotado y sin resolver**: ADR-008 dice que el top se detecta "por
  inflexión de la segunda derivada de la velocidad filtrada"; el código detecta
  el **cambio de sentido** (cero de la velocidad proyectada), que es lo que dice
  la definición de GolfDB. ADR-017 no toca eso: sólo elige cuál de los cambios
  de sentido es el top. La primitiva `d2_inflection` existe y hoy no la usa
  ningún evento.
- El error del top contra GolfDB (ESPECIFICACION 2.5) sigue sin medirse: dos
  trials de un sujeto de mocap no son una tabla.
