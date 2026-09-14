# kinelab — Contrato de datos

Es el artefacto central del proyecto. **Se escribe y se discute antes del
motor**, no se destila después de lo que el código terminó devolviendo. En la
Fase 2 se vuelve JSON Schema real (`kinelab/contract/schema.json`) con un test
que lo ejercita.

Tres reglas por encima de todo:

1. **Nada derivado se guarda sin poder recalcularse.** El video y `pose.npz`
   son la fuente; todo lo demás se regenera.
2. **Nunca un float solo.** Toda métrica es `{value, unit, confidence, view,
   mdc, level}`.
3. **La incertidumbre se muestra, no se esconde.** Si un clip tuvo detección
   pobre, el JSON lo dice antes de mostrar un solo número.

---

## Layout en disco

```
data/
  capture-paths.yaml                 caminos de captura, calibrados o declarados (ver CAPTURA.md)
  athletes/<slug>.yaml               altura_m, lateralidad, fecha de alta
  sessions/<atleta>/<fecha>/<gesto>/<vista>/take-NN/
    original.<ext>                   intocable, tal como llegó
    capture.json                     escrito por la ingesta; el gate vive acá
    master.mp4                       H.264 CFR, GOP 12, sin audio — Fase 4
    pose.npz                         percepción cruda + provenance
    analysis.json                    todo lo derivado, por capas
    analysis.<engine_version>.json   versiones anteriores, nunca se borran
    events-manual.json               correcciones humanas (opcional)
```

`data/` está en `.gitignore` salvo `capture-paths.yaml`, `schemas/` y
`examples/`: los caminos de captura son configuración y viajan con el repo;
las sesiones y los atletas son del entrenador y no.

---

## `capture-paths.yaml`

Un camino = dispositivo + modo + transferencia. Es **configuración**, no
inferencia. Un clip cuyo `capture_path_id` no está acá se rechaza.

Un camino **calibrado** registra **dos tasas**: `fps_real`, la de captura, que
sale del cronómetro filmado; y `fps_playback`, la que el archivo reproduce, que
sale de los PTS. Su cociente es `stretch_factor`: 1,0 en video normal, 8,0 en un
Slo-Mo de 240 estirado a 30. El motor convierte los PTS a tiempo real con ese
factor, y el gate compara la reproducción del clip contra la del camino.

```yaml
schema_version: "1.1.0"
paths:
  - id: iphone17pro-video-1080p120-airdrop
    device: "iPhone 17 Pro"
    mode: video            # video | slomo
    calibrated: true       # default; false = declarado sin cronómetro (ADR-016)
    nominal_fps: 120
    codec_expected: hevc
    transfer: airdrop-keep-originals
    fps_real: 119.88       # tasa de CAPTURA, medida con cronómetro filmado
    fps_playback: 119.88   # tasa a la que el archivo REPRODUCE, medida de los PTS
    stretch_factor: 1.0    # fps_real / fps_playback; 8.0 en un Slo-Mo 240 estirado a 30
    fps_method: "cronómetro 10 s, 1199 cuadros entre 00:00.000 y 00:10.000"
    calibrated_on: 2026-09-14
    calibrated_by: hernan
    notes: "delta_max/delta_min = 1.004"
```

Un camino **declarado** (`calibrated: false`, ADR-016) no tiene ninguno de esos
números: dispositivo y modo los dice el usuario, y la tasa de captura se asume
igual a la de reproducción del archivo. Los seis campos del cronómetro tienen
que estar en `null` — declarar no es medir — y `nominal_fps` y `codec_expected`
son opcionales: `null` es "no se sabe". Sólo `mode: video`; un `slomo` sin
calibrar lo rechaza el gate. La tabla completa está en `CAPTURA.md`
§Caminos declarados sin calibrar.

```yaml
  - id: desconocido-video     # el genérico: "no sé con qué se filmó"
    device: "desconocido"
    mode: video
    transfer: "desconocido"
    calibrated: false
    nominal_fps: null
    codec_expected: null      # el chequeo de codec queda sin evaluar
    fps_real: null
    fps_playback: null
    stretch_factor: null
    fps_method: null
    calibrated_on: null
    calibrated_by: null
    notes: "los tiempos asumen que el archivo reproduce a la velocidad de captura"
```

---

## `capture.json`

Escrito por `kinelab.ingest`. Nunca a mano después de la Fase 0.

```json
{
  "schema_version": "1.2.0",
  "athlete": "hernan",
  "gesture": "driver",
  "view": "face_on",
  "capture_path_id": "iphone17pro-video-1080p120-airdrop",
  "capture_path_calibrated": true,
  "fps_provenance": "medido_aqui",
  "fps_real": 119.88,
  "fps_source": "capture-paths.yaml:iphone17pro-video-1080p120-airdrop",
  "fps_playback": 119.85,
  "fps_playback_raw": 119.85,
  "stretch_factor": 1.0,
  "codec": "hevc",
  "width": 1920,
  "height": 1080,
  "rotation_deg": 0,
  "frames_decoded": 2398,
  "duration_s": 20.003,
  "duration_playback_s": 20.0,
  "vfr_ratio": 1.004,
  "vfr_ratio_raw": 1.004,
  "first_delta_s": 0.008342,
  "fps_note": null,
  "recorded_at": "2026-09-14T10:32:11.000000Z",
  "sha256_original": "…",
  "original_name": "IMG_0412.MOV",
  "gate": {
    "verdict": "ok",
    "checks": [
      {"id": "capture_path_known", "passed": true, "value": "iphone17pro-video-1080p120-airdrop"},
      {"id": "codec_matches_path", "passed": true, "value": "hevc", "expected": "hevc"},
      {"id": "vfr_ratio_le_1_10", "passed": true, "value": 1.004, "expected": "<= 1.1"},
      {"id": "fps_matches_path", "passed": true, "value": 119.85, "expected": 119.88, "tolerance": 0.02},
      {"id": "fps_min_for_gesture", "passed": true, "value": 119.88, "expected": ">= 100"},
      {"id": "duration_plausible", "passed": true, "value": 20.003, "expected": "3–180 s"},
      {"id": "rotation_normalized", "passed": true, "value": 0},
      {"id": "view_declared", "passed": true, "value": "face_on", "expected": ["face_on", "down_the_line"]},
      {"id": "gesture_known", "passed": true, "value": "driver", "expected": ["driver", "iron", "wedge"]}
    ],
    "reasons": []
  }
}
```

### La procedencia del fps

`fps_provenance` dice de dónde sale `fps_real`: `medido_aqui` cuando el camino
está calibrado con cronómetro, `sin_verificar` cuando es un camino declarado
(ADR-016) o no hay camino usable. `capture_path_calibrated` lo acompaña
(`true` / `false` / `null` si el camino es desconocido) y `fps_source` empieza
con `capture-paths.yaml:<id>` o con `declarado:<id>` según el caso.

Los dos son opcionales para que un `capture.json` 1.1.0 siga validando, y sus
defaults son los conservadores: `null` y `sin_verificar`. Sin el campo, nada
puede ser juicio.

En un camino declarado `fps_real` es el `fps_playback` efectivo y
`stretch_factor` es 1,0 **por supuesto, no por medición**. En un `slomo`
declarado no hay ninguno de los dos: `fps_real` y `stretch_factor` quedan en
`null` y la toma se rechaza.

### El fps efectivo y el bruto

`fps_playback` y `vfr_ratio` son los números **efectivos**: los de todos los
deltas de PTS menos el primero, cuando el arranque de la cámara es la única
anomalía (`vfr_ratio` bruto > 1,10 y sin el primer delta ≤ 1,10). Son los que
evalúa el gate y los que usa el motor. Los brutos viajan al lado en
`fps_playback_raw` y `vfr_ratio_raw`, el delta de arranque en `first_delta_s`,
y `fps_note` explica en una frase por qué difieren — `null` cuando coinciden,
que es el caso normal.

Por qué: medido en el original del Galaxy S22 Ultra (265 cuadros), 263 deltas
de 0,0333 s y **uno** de 0,2015 s, el primero. Contado entero, el clip se
declaraba de tasa variable con ratio 6,04 y reproducía a 29,436 fps en vez de
29,998: todos los tiempos 1,9 % largos. Un solo delta de arranque no es tasa
variable. Ver el informe `docs/informes/2026-09-14-03-fps-truth-primer-delta.md`
y `CAPTURA.md` §El gate de ingesta.

En un clip realmente de tasa variable el efectivo **es** el bruto: excluir el
primer delta no perdona nada.

`duration_s` es la duración **real** (`frames_decoded / fps_real`);
`duration_playback_s`, el span de PTS medido, con el hueco del arranque adentro
si lo hubo — por eso no tiene que coincidir con `frames_decoded / fps_playback`.
En un Slo-Mo estirado ×8 difieren ×8.
`passed` puede ser `null`: el chequeo no se pudo evaluar (por ejemplo, sin
camino calibrado no hay contra qué comparar el codec); no cuenta como fallo,
pero queda visible. `rotation_deg` es en sentido horario: un iPhone filmando en
vertical da 90.

Cuando `verdict` es `reject`, `reasons` es una lista de frases que el
entrenador puede leer: *"El clip está en H.264: pasó por 'Más compatible' o
por un transcodificador. Volvé a exportarlo con 'Mantener originales'."*

Un chequeo que **pasa** también puede llevar `reason`: es su propio registro, y
no entra en `reasons` (que sólo lleva lo que falló). Es donde
`vfr_ratio_le_1_10` y `fps_matches_path` dicen que el número que evaluaron no
es el bruto del archivo: *"ratio 1.000 sin el primer delta de 0.201 s (arranque
de la cámara); bruto 6.044."* Nunca una corrección en silencio.

---

## `pose.npz`

Percepción cruda. Se escribe una vez por corrida del modelo y no se toca.

| clave | tipo | forma | contenido |
|---|---|---|---|
| `keypoints` | float32 | `(T, J, 2)` | píxeles en el marco `image_px` del `master.mp4` |
| `scores` | float32 | `(T, J)` | confianza por keypoint, tal como la da el modelo (no calibrada) |
| `bbox` | float32 | `(T, 4)` | caja usada para el recorte, `x0 y0 x1 y1` |
| `timestamps_s` | float64 | `(T,)` | tiempo real de cada cuadro, desde `fps_real` |
| `plausibility` | uint8 | `(T,)` | máscara de bits de rechazos anatómicos por cuadro (0 = limpio) |
| `provenance` | str (JSON) | — | ver abajo |

`provenance`:

```json
{
  "model": "rtmpose-m",
  "checkpoint_sha256": "…",
  "keypoint_set": "halpe26",
  "input_size": [192, 256],
  "detector": "yolox-m-coco",
  "detector_sha256": "…",
  "provider": "CoreMLExecutionProvider",
  "onnxruntime_version": "1.23.2",
  "intra_op_num_threads": 5,
  "engine_version": "0.1.0",
  "code_sha": "…",
  "master_sha256": "…",
  "run_at": "…"
}
```

El determinismo se afirma **sólo** para `(model, checkpoint_sha256, provider,
onnxruntime_version)` iguales.

---

## `analysis.json` — por capas

Todo lo que no está en `pose.npz`. Legible, sin arrays largos (las series van
submuestreadas a ≤ 10 Hz para gráficos; el detalle se recalcula desde `pose.npz`).

```
header        schema_version, engine_version, registry_version, generated_at,
              source {pose_sha256, master_sha256, capture_path_id, fps_real,
                      fps_provenance}
quality       detection_rate, body_height_px {median, min, max, frac_of_frame},
              blur_estimate, plausibility {rejected_frames, by_reason},
              verdict: confiable | con_reservas | no_usar, reasons[]
events[]      una por repetición — ver abajo
reps[]        una por repetición — métricas con su sextuplo
summary       agregados + repetibilidad + ganancia
series        t[], y algunas señales a ≤ 10 Hz para los gráficos
warnings[]    avisos legibles
deviations[]  desviaciones del contrato, fechadas
```

### `events[]`

```json
{
  "rep": 3,
  "address":    {"frame": 412, "t_s": 3.437, "tol_frames": 1, "method": "stable_window", "manual": false, "subframe": null},
  "top":        {"frame": 517, "t_s": 4.313, "tol_frames": 1, "method": "d2_inflection", "manual": false, "subframe": null},
  "impact":     {"frame": 548, "t_s": 4.571, "tol_frames": 1, "method": "peak_window", "manual": true, "subframe": {...}},
  "follow_end": {"frame": 604, "t_s": 5.038, "tol_frames": 2, "method": "d2_inflection", "manual": false, "subframe": null},
  "sequence_order": "indeterminado"
}
```

`sequence_order` toma `indeterminado` cuando dos picos caen dentro de ±2
cuadros. Nunca se fuerza un orden.

### `subframe`: el instante entre dos cuadros

`frame` es el ancla de todo y no cambia nunca por esto. `subframe` es un campo
**opcional** (`null` donde el deporte no lo define) con el instante estimado
entre `frame_before` y `frame_after`, para los eventos cuya definición
geométrica es un cruce y no un cuadro. Hoy lo tiene sólo el impacto de golf.

```json
"subframe": {
  "frame_before": 44, "frame_after": 45, "fraction": 0.4404,
  "t_sub_s": 1.481396,
  "uncertainty_frames": 0.1112, "uncertainty_s": 0.003707,
  "components": {"curvature_frames": 0.1104, "noise_frames": 0.0128, "noise_px": 1.204, "slope_px_per_frame": 115.363},
  "method": "hands_cross_address_linear_interp",
  "signal": "centro de las dos muñecas (crudo, huecos rellenados) proyectado sobre su dirección de viaje en el impacto",
  "views": ["face_on"], "provenance": "estimacion", "null_reason": null
}
```

- `fraction` va de 0 a 1 entre los dos cuadros, y `t_sub_s` es el mismo
  instante en segundos, con la convención de `t_s` (cuadro `n` = `n / fps`).
- **Si el cruce no es claro, `fraction` es `null` y `null_reason` lo dice** en
  una frase: la señal no cruza en la ventana, cruza más de una vez, el cruce no
  es contiguo al cuadro del evento, o la vista no es válida. Nunca un número
  forzado.
- `uncertainty_frames` es la invariante 8 aplicada acá: en vez de ±1 cuadro
  entero, el cruce se recalcula extrapolando cada segmento vecino con la
  velocidad local (`curvature_frames`), y se le suma en cuadratura el ruido de
  la señal propagado por la pendiente (`noise_frames`). Los sumandos quedan a
  la vista en `components`.
- `provenance` es `estimacion` mientras el arnés no le mida MDC: es
  descriptivo, no juicio (ADR-007).
- Una corrección manual de `frame` **no** toca `subframe`: describe la señal,
  con sus dos cuadros escritos al lado.

### El sextuplo de toda métrica

```json
"backswing_duration_ms": {
  "value": 876.0,
  "unit": "ms",
  "confidence": {"value": 0.92, "method": "event_tolerance_propagation"},
  "uncertainty": {"low": 859.3, "high": 892.7, "method": "±1 frame at 119.88 fps"},
  "view": "face_on",
  "mdc": 21.0,
  "level": 1,
  "fps_min": 100,
  "fps_min_met": true,
  "fps_provenance": "medido_aqui",
  "judgment_allowed": true,
  "null_reason": null
}
```

`fps_provenance` es de dónde sale el `fps_real` con el que se calculó el tiempo:
`medido_aqui` (cronómetro filmado, camino calibrado) o `sin_verificar` (camino
declarado, ADR-016). Va en **cada** métrica, no sólo en las ancladas a tiempo:
la incertidumbre de todas se propaga desde ±1 cuadro, y un cuadro dura lo que
diga ese número. Está en el campo y no sólo en `uncertainty.method` porque una
métrica en `null` tiene `uncertainty: null` y la procedencia no se puede perder;
la frase de `uncertainty.method` la repite para quien lee el JSON a ojo
(*"±1 cuadro en cada evento ancla a 29.998 fps (sin_verificar)"*).

Cuando la métrica no se puede calcular, `value` es `null` y `null_reason` dice
por qué en una frase: `"fps_real 59.94 por debajo de fps_min 100"`,
`"vista down_the_line no válida para esta métrica"`, `"MDC no medido"`.

`judgment_allowed` se deriva en código, nunca se escribe a mano:

```
judgment_allowed = level == 1
                   and mdc is not None
                   and fps_min_met
                   and fps_provenance == "medido_aqui"
                   and view in metric.views
                   and (reference is None or mdc <= reference.range_width)
```

La condición de la procedencia es ADR-016: con la tasa de cuadros sin verificar
el número se muestra —es descriptivo— pero no se compara contra nada, porque el
eje del tiempo es un supuesto y no una medición.

### `summary`

```json
{
  "rep_count": 12,
  "reps_rejected": {"count": 2, "reasons": {"plausibility": 1, "manual_discard": 1}},
  "metrics": {
    "backswing_duration_ms": {"median": 871.0, "sd_abs": 34.2, "n": 10, "mdc": 21.0,
                              "repeatability": {"kind": "sd_abs", "value": 34.2, "noise_floor": 9.1}}
  },
  "gain": {
    "pelvis_to_torso": {"value": 1.49, "unit": "ratio", "n": 10, "confidence": {...}},
    "torso_to_arm":    {"value": 1.51, "unit": "ratio", "n": 10, "confidence": {...}}
  }
}
```

La repetibilidad **siempre** lleva `noise_floor`: el piso de ruido del propio
pipeline, medido corriendo el mismo clip con jitter o dos clips del mismo
gesto. Sin ese número, una parte de la "inconsistencia" es el instrumento, no
el atleta.

---

## El registro de métricas

Declarativo. Una entrada por métrica. Las 16 métricas del prototipo anterior
estaban en una función de 40 líneas; acá cada una es un objeto que el motor
puede inspeccionar antes de calcular.

```python
Metric(
    id="pelvis_sway_cm",
    unit="cm",
    level=1,
    views=("face_on",),
    fps_min=60,
    anchored_to=("address", "top"),
    reference_frame="image_px",
    compute=metrics.golf.pelvis_sway,
    confidence=confidence.from_keypoint_scores(("hip_center",)),
    reference=Reference(
        kind="descriptive",               # descriptive | range
        provenance="fabricante",          # medido_aqui | pares | fabricante | estimacion
        source="Onform model card v2.0, abr 2026",
        definition="desplazamiento lateral del centro de pelvis Halpe26 respecto del address, en el plano de imagen, normalizado por altura de cuerpo y convertido con altura declarada",
        range=None,
    ),
    mdc=None,        # se llena desde truth/; None → judgment_allowed = False
    metric_version="1.0.0",
)
```

`fps_min` y `views` **se escriben desde la tabla del arnés**, no a mano. Una
métrica cuyo barrido muestra que muere por debajo de cierto fps recibe ese
número; una que colapsa desde una vista pierde esa vista.

### Niveles

**Nivel 1 — defendibles.** El error lo domina la cuantización temporal o es
del orden de centímetros. Pueden ser juicio si tienen MDC.
Golf: duraciones de fase y tempo · repetibilidad de cualquier métrica ·
sway, lift, thrust de pelvis y tórax · movimiento de cabeza · geometría del
shaft por evento · deltas respecto del address · ganancia de velocidad angular.

**Nivel 2 — condicionales.** Sólo con `fps_real ≥ 120`, vista controlada,
banda de ±5° explícita, y nunca juicio binario.
Golf: giro de pelvis y tórax en Top e Impact · forward bend y side bend.

**Nivel 3 — no se construyen.** No hay entrada en el registro, a propósito.
X-factor stretch (señal 2,9° bajo un piso de 4–7°) · orden de la secuencia
cinemática · X-factor en el top como objetivo · ángulos absolutos de codo,
rodilla y muñeca · plano de swing 3D · rotación interna de hombro · pronación
· cualquier veredicto de riesgo de lesión · velocidad absoluta en m/s desde
homografía.

---

## Versionado

- `schema_version` semver. **Renombrar un campo o cambiar una unidad es
  major**, aunque parezca inocente: la IA que lee el JSON ya aprendió el
  nombre viejo. Métrica nueva y opcional es minor. Va en **1.2.0**: 1.1.0 por el
  `subframe` de los eventos (campo nuevo y opcional) y 1.2.0 por
  `fps_provenance` en `header.source` y en cada métrica (ADR-016). El de 1.2.0
  es un campo **obligatorio** en un bump minor: está anotado en §Desviaciones.
- `capture.json` lleva su propio `schema_version`, hoy **1.2.0**: 1.1.0 agregó
  `fps_playback_raw`, `vfr_ratio_raw`, `first_delta_s` y `fps_note`; 1.2.0
  agrega `capture_path_calibrated` y `fps_provenance` (ADR-016). Los seis son
  opcionales: un `capture.json` de 1.0.0 sigue validando, con los cuatro
  primeros en `null`, `capture_path_calibrated` en `null` y `fps_provenance` en
  `sin_verificar`. El bump a 1.1.0 cambió de qué número hablan `fps_playback` y
  `vfr_ratio` (bruto → efectivo): también está en §Desviaciones.
- `capture-paths.yaml` lleva el suyo, hoy **1.1.0**: agregó `calibrated` (con
  default `true`) y volvió opcionales `nominal_fps`, `codec_expected` y los
  seis campos del cronómetro, que ahora sólo son obligatorios cuando
  `calibrated: true`. Un archivo 1.0.0 sigue cargando sin cambios.
- `registry_version` aparte, y `metric_version` por métrica. Con un solo
  número, mejorar una métrica invalida el historial del atleta.
- `engine_version` en `provenance` y en `header`.
- Re-analizar conserva el `analysis.json` anterior renombrado con su
  `engine_version`. Comparar dos versiones del motor sobre la misma sesión
  tiene que ser posible sin copiar carpetas a mano.

---

## Frontera Python ↔ JSON

- `NaN` e `inf` se convierten a `null` en **una sola función** de la capa de
  escritura. Ningún otro lugar los toca.
- Los `null` nunca se omiten: un campo esperado siempre está, aunque sea `null`
  con su `null_reason`.
- float32 en `.npz`; en JSON, redondeo a 3 decimales para ángulos y a 1 para
  milisegundos y centímetros.

---

## Desviaciones

Toda desviación respecto de este contrato se anota acá con fecha, qué se
cambió y por qué. Es la sección que hizo posible auditar el prototipo anterior
sin haberlo escrito.

- **2026-09-14 · `analysis.json` 1.1.0 → 1.2.0 con `fps_provenance`
  OBLIGATORIO**, en un bump **minor**. §Versionado dice que lo nuevo y opcional
  es minor, y un campo requerido nuevo es, en rigor, major: un `analysis.json`
  1.1.0 ya escrito no valida contra el schema nuevo. Se hizo minor igual, por
  tres razones: la procedencia del fps es justamente lo que ADR-016 no quiere
  que se pueda omitir — opcional, un análisis sin ella pasaría como si el eje
  del tiempo estuviera medido —; el validador sólo corre al **escribir**
  (`contract/write.py`), así que ningún archivo viejo se rompe al leerlo; y no
  hay `analysis.json` fuera de `data/exploracion/` y de los ejemplos, que se
  regeneran. El ejemplo del repo (`data/examples/analysis.example.json`) se
  actualizó a mano con `fps_provenance: medido_aqui`.
- **2026-09-14 · `capture.json` 1.0.0 → 1.1.0 con `fps_playback` y `vfr_ratio`
  cambiando de significado** (bruto → efectivo), en un bump **minor**.
  §Versionado dice que renombrar un campo o cambiar una unidad es major, y
  cambiar de qué número habla un campo está en ese mismo espíritu. Se hizo
  minor igual, por decisión del orquestador (informe
  `docs/informes/2026-09-14-03-fps-truth-primer-delta.md`, backlog
  `docs/PLAN.md`), con tres razones: el nombre y la unidad no cambian; los dos
  números coinciden salvo cuando el arranque de la cámara es la única anomalía,
  y ahí el viejo estaba **mal** (29,436 fps en vez de 29,998); y el valor viejo
  no se pierde, queda en `fps_playback_raw` / `vfr_ratio_raw` con `fps_note`
  explicando la diferencia. No había ningún `capture.json` fuera de
  `data/exploracion/`, que se regenera en cada corrida.
