# kinelab — Especificación por fases

Seis fases, en orden fijo. Cada una se cierra con su criterio de aceptación
antes de empezar la siguiente. No se adelanta trabajo. El criterio siempre es
verificable: un comando que corre, un archivo que existe, un número que se
reporta.

La Fase 0 es casi toda del humano. El trabajo del agente en esa fase es darle
las herramientas para hacerla bien, y después **parar**.

---

## Fase 0 — El cronómetro y el material

Nada de pose, métricas ni interfaz. Sin clips reales que pasen el gate, todo lo
demás es código a ciegas — que es exactamente lo que hundió los dos prototipos
anteriores.

**Agente**

- 0.1 Portar `banco/fps_truth.sh` a `kinelab/tools/fps_truth.py`. Entrada: un
  clip y la duración real medida. Salida: cuadros decodificados, tasa efectiva,
  `delta_max / delta_min`, codec, y veredicto. Tests sobre **tres clips
  sintéticos generados con ffmpeg en el propio test**: 240 fps real, 240
  estirado a 30 con `setpts`, y 30 remuestreado con `-r`. El test tiene que
  demostrar que `r_frame_rate` y `avg_frame_rate` no distinguen los dos
  últimos y que el conteo sí.
- 0.2 `data/capture-paths.yaml`: schema, archivo vacío, y un ejemplo comentado
  (dispositivo, modo, transferencia, fps real, codec esperado, fecha de
  calibración, cómo se midió).
- 0.3 `docs/checklist-captura.md`: el checklist imprimible de configuración del
  teléfono y de filmación, derivado de `CAPTURA.md`.
- 0.4 Gate mínimo de ingesta en `kinelab/ingest/gate.py`: codec HEVC, VFR
  `≤ 1,10`, tasa efectiva contra el camino calibrado, duración plausible.
  Escribe `capture.json` o rechaza con razón legible. Con tests.
- 0.5 Commit. Parar. Decirle al humano exactamente qué filmar y cómo verificarlo.

**Humano**

- 0.6 Configurar el teléfono según `CAPTURA.md` §Configuración.
- 0.7 Filmar 10 s de un cronómetro con milisegundos con **cada** combinación
  modo + camino de transferencia que se vaya a usar. Pasar cada clip por
  `fps_truth`. Escribir el resultado en `capture-paths.yaml`.
- 0.8 Filmar la primera sesión real: un golfista, `face_on` y `down_the_line`,
  10–20 swings por vista, según protocolo. Encuadre ≥ 80% del alto. AirDrop
  con "Mantener originales".

**Aceptación**

- Existe una carpeta de clips reales. Cada uno tiene `capture.json` con
  `fps_real` tomado de un camino calibrado, `codec: hevc`, y `vfr_ratio ≤ 1,10`.
- El gate rechaza, con razón legible, un clip deliberadamente malo: el mismo
  swing exportado desde Fotos con File → Export.
- Cero líneas de código de pose, métricas o interfaz.

---

## Fase 1 — Percepción

- 1.1 Portar de `padel-coach` (ver `HERENCIA.md`): wrapper de pose, guardia
  anti cajas fantasma, selección y seguimiento de un sujeto, relleno de huecos
  acotado, `posestore`. Con atribución, y con tests propios.
- 1.2 Cambiar a `rtmpose-m` + Halpe26 vía `rtmlib`, `CoreMLExecutionProvider`
  con caída a CPU, `intra_op_num_threads=5`, pesos fijados por hash en
  `models/`, detector entrenado en COCO. Aserción de preprocesado y chequeo de
  `NaN` a la salida. Provenance completa en `pose.npz`.
- 1.3 Gate de encuadre y detección: `body_height_px` mínimo (el umbral se fija
  **midiendo** sobre los clips de Fase 0, no a mano), tasa de detección, bbox
  estable por repetición (padding fijo, relación de aspecto fija, sin
  re-detectar por cuadro).
- 1.4 Filtro de plausibilidad anatómica por cuadro: codo fuera de 20–180°,
  longitudes de segmento inconsistentes entre cuadros, confianza por keypoint
  bajo umbral. **Marca**, no borra: los cuadros marcados se cuentan y quedan
  visibles.
- 1.5 Paso cero de validación: correr `SynthPose ViTPose-B` sobre los mismos
  clips y producir un reporte de discrepancia por keypoint contra RTMPose. Sin
  ground truth: sólo la discrepancia, en píxeles y en grados de codo/rodilla.
- 1.6 Portar `banco/` (bench, threads, coreml_opts, scale_sweep, degrade) con
  rutas parametrizadas, como banco permanente de rendimiento.

**Aceptación**

- `pose.npz` para cada clip real, con provenance completa (modelo, sha256,
  proveedor, versión de onnxruntime, tamaño de entrada, conjunto de keypoints).
- Dos corridas del mismo clip con el mismo proveedor dan `pose.npz` idénticos.
- El gate rechaza un clip con el sujeto al 15% del alto del cuadro.
- El reporte SynthPose vs RTMPose existe, con número por keypoint.
- Un clip sintético con la imagen sin normalizar produce una aserción, no un
  `pose.npz` lleno de `NaN`.

---

## Fase 2 — Contrato y eventos

- 2.1 `CONTRATO.md` como JSON Schema real en `kinelab/contract/schema.json`,
  con validador y un test que valida un `analysis.json` de ejemplo y rechaza
  uno con un campo renombrado.
- 2.2 Registro declarativo de métricas (`kinelab/metrics/registry.py`): cada
  entrada con `id, unit, level, views, fps_min, anchored_to, compute,
  reference, mdc, confidence`. Vacío de métricas todavía: sólo la estructura y
  sus tests.
- 2.3 Eventos de golf en `sports/golf/events.py`: Address determinista (último
  cuadro de una ventana pre-movimiento estable, umbral parametrizado), Top por
  inflexión de la segunda derivada de la velocidad filtrada (Butterworth de
  4º orden con `filtfilt`, corte parametrizado por fps — nunca fijo), Impact
  por pico con ventana de búsqueda, fin de follow-through. Tolerancia ±1
  cuadro en cada evento. Regla de exclusión: picos a < 2 cuadros →
  `indeterminado`.
- 2.4 Segmentación de repeticiones, con **test negativo**: una persona quieta
  y una caminando producen cero repeticiones.
- 2.5 Medir el error de detección de eventos contra GolfDB (uso de medición,
  no de entrenamiento). Reporte por evento en cuadros, con sesgo y límites de
  acuerdo. Se acepta que Address y Finish salgan mal: es lo esperado.
- 2.6 Corrección manual de eventos que vuelve al JSON y recalcula desde
  `pose.npz` (portar `adjust.py`). Dos repeticiones no pueden compartir cuadro.

**Aceptación**

- `analysis.json` valida contra el schema.
- Error de eventos contra GolfDB reportado por evento en cuadros.
- Clip sin gesto → 0 repeticiones, sin excepción.
- Ajuste manual de un evento hace round-trip y conserva el valor detectado.
- Intentar mover dos repeticiones al mismo cuadro falla con razón.

---

## Fase 3 — Arnés de verdad y métricas de nivel 1

Las dos cosas van juntas a propósito: cada métrica se agrega con su barrido.

- 3.1 `truth/` con su propio entorno. Cadena cinemática de segmentos rígidos
  con longitudes de de Leva 1996; generador de poses por ángulos conocidos y
  de swing paramétrico; cámara pinhole con intrínsecos **medidos del teléfono
  real** (`cv2.calibrateCamera` con tablero, distorsión incluida);
  extrínsecos en `face_on` y `down_the_line`; barridos de azimut (0–90° en
  pasos de 15), elevación (0–45°), distancia (2–8 m), ruido gaussiano con σ
  escalado por altura del cuerpo en px, tamaño del sujeto (100–900 px), fps
  (240 → 30), oclusión y desenfoque por promediado de sub-cuadros.
- 3.2 Métricas de nivel 1 de golf, una por una, cada una con su barrido en el
  arnés: duraciones de fase y tempo; sway, lift y thrust de pelvis y tórax;
  movimiento de cabeza relativo al address; geometría del shaft por evento;
  deltas de flexión de rodilla y postura respecto del address; repetibilidad
  (SD absoluta para escalares, DTW normalizado para la curva de velocidad de
  muñeca); ganancia de velocidad angular pelvis→tórax→brazo.
- 3.3 La tabla de sesgo / límites de acuerdo / MDC por métrica y condición es
  el entregable. **De ahí se escriben `fps_min` y `views` en el registro, no a
  mano.** Si el barrido muestra que una métrica muere, se borra.
- 3.4 Tests de las cuatro capas de ADR-011, incluida la mutation manual.

**Aceptación**

- Cada métrica de nivel 1 tiene MDC medido y está en el registro con sus seis
  cosas.
- La regla del MDC está en código: una métrica sin MDC o con MDC > rango no
  puede marcarse como juicio.
- Cada uno de los cuatro bugs inyectados hace fallar al menos un test.
- Un sujeto quieto produce cero métricas, no métricas en `null`.
- El nivel 0 del arnés **no** se acepta con sólo el caso nominal: la tabla
  tiene que tener los barridos.

---

## Fase 4 — Servicio local, ingesta y visor

- 4.1 Portar el patrón de `service.py` (jobs, cancelación, validación de rutas
  con sus 14 tests), el servido con Range/206, y la transcodificación con
  sondeo (prefiere `avg_frame_rate` pero **no lo usa como verdad**).
- 4.2 `master.mp4`: H.264 CFR, `-g 12`, `-fps_mode cfr`, sin audio,
  `+faststart`, rotación aplicada. Todo índice de cuadro se refiere a este
  archivo; su hash va en `analysis.json`.
- 4.3 Ingesta: importar carpeta, preview de cada clip, asignar atleta, gesto
  y vista, ver el veredicto del gate **antes** de analizar.
- 4.4 Un solo visor (ADR-014): frame a frame en las dos direcciones con
  verificación del cuadro presentado, cámara lenta (0,25–1× nativo; por debajo,
  stepper propio), zoom con paneo sobre wrapper común, capas conmutables,
  y por cada métrica: valor, unidad, confianza y MDC. Corrección de eventos
  desde el visor.

**Aceptación**

- Importar → gate → analizar → visor, de punta a punta, sobre los clips
  reales.
- El cuadro dibujado es el cuadro presentado, verificado por `mediaTime`;
  retroceder un cuadro cambia número e imagen juntos.
- Un clip rechazado muestra la razón antes de cualquier número.
- El zoom a 4× no pixela el trazo.

---

## Fase 5 — Lectura para el entrenador

- Repetibilidad primero; descriptivos con confianza después; ganancia; nunca
  puntaje, nunca texto autogenerado.
- Comparación lado a lado de dos repeticiones sincronizadas por evento (portar
  `compare.py`).
- Cada número lleva su banda, y una métrica descriptiva se ve distinta de un
  juicio.

**Aceptación**

- El entrenador mira diez swings y puede decir en voz alta qué va a corregir,
  señalando el cuadro, con el número y su banda.

---

## Después de las seis fases

`sports/padel/` (sólo cuando golf tenga MDC medidos). Devolución escrita por IA
sobre `analysis.json`. Acceso del alumno. Dos personas en cuadro. Nivel 2 de
validación (OpenCapBench, y pedir el dataset GolfSwing de GolfPose por mail).
