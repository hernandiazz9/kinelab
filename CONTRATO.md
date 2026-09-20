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
              scale_px {value, frame, method}, camera_motion_px,
              verdict: confiable | con_reservas | no_usar, reasons[]
events[]      una por repetición — ver abajo
reps[]        una por repetición — scale_px, scale_source y las métricas con su sextuplo
summary       agregados + repetibilidad
series        t[], y algunas señales a ≤ 10 Hz para los gráficos
warnings[]    avisos legibles
deviations[]  desviaciones del contrato, fechadas
```

### `events[]`

```json
{
  "rep": 3,
  "address":    {"frame": 412, "t_s": 3.437, "tol_frames": 1, "method": "stable_window", "manual": false, "subframe": null},
  "top":        {"frame": 517, "t_s": 4.313, "tol_frames": 1, "method": "direction_change_farthest", "manual": false, "subframe": null},
  "impact":     {"frame": 548, "t_s": 4.571, "tol_frames": 1, "method": "peak_window", "manual": true, "subframe": {...}},
  "follow_end": {"frame": 604, "t_s": 5.038, "tol_frames": 2, "method": "still_after_impact", "manual": false, "subframe": null}
}
```

**`sequence_order` no está más** (ADR-018): salía de la misma función que la
ganancia y de los mismos picos, y el orden de la secuencia cinemática ya estaba
fuera de alcance por `CONTEXTO.md` y en el nivel 3 de §Niveles. Sacarlo es parte
del bump a 2.0.0.

`tol_frames` es la tolerancia del evento **en esta repetición**, y es de donde
sale la banda de toda métrica anclada a él: `evaluate` mueve cada evento ancla
±`tol_frames` (invariante 8), no un ±1 fijo. Un evento cuya regla decidió dentro
del ruido declara una banda más ancha y las métricas la heredan.

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
  "views": ["face_on"], "provenance": "estimacion", "null_reason": null,
  "mdc": {"value": 2.9269, "unit": "ms", "provenance": "medido_aqui", "source": "sports/golf/mdc.yaml §events.impact.subframe"}
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
- `provenance` es la del **valor**: `estimacion`, porque el cruce sale de una
  interpolación lineal entre dos cuadros. Es descriptivo, no juicio (ADR-007).
- **`mdc` es opcional** (`null` o ausente donde nadie lo midió) y lleva su
  propia unidad y su propia procedencia, que no tiene por qué ser la del valor:
  el MDC del cruce lo mide el arnés y es `medido_aqui`, con `source` diciendo de
  qué archivo y sección salió. Es el único lugar del contrato donde un campo de
  **evento** —y no una métrica del registro— lleva MDC: el registro es de
  métricas y un instante entre cuadros no es una. Tener el MDC no lo vuelve
  juicio: eso lo sigue decidiendo `judgment_allowed` de las métricas ancladas, y
  con un camino sin calibrar es `false` igual (ADR-016). Y el MDC de este cruce
  **es del arnés y no está validado en material real** (ADR-019): lo midió el
  nivel 0 —proyección más ruido, sin estimador de pose— con una cámara que no es
  la que filmó y que nadie verificó. La `provenance` sigue siendo `medido_aqui`,
  que es literalmente cierta y dice de dónde sale el número; lo que aclara de qué
  arnés viene y que no está validado es el `source`.
- Una corrección manual de `frame` **no** toca `subframe`: describe la señal,
  con sus dos cuadros escritos al lado.

### El sextuplo de toda métrica

```json
"backswing_duration_ms": {
  "value": 876.0,
  "unit": "ms",
  "metric_version": "1.0.0",
  "confidence": {"value": 0.92, "method": "event_tolerance_propagation"},
  "uncertainty": {"low": 859.3, "high": 892.7, "method": "±1 cuadro(s) en cada evento ancla a 119.88 fps (medido_aqui)"},
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

`metric_version` es la versión de **esta** métrica, la misma que declara el
registro. Va en el sextuplo y no sólo en el registro porque, si no, un bump de
métrica es invisible para quien lee un `analysis.json`: las ocho métricas en cm
cambiaron de valor con la convención de escala del encargo 14 y nada en el
archivo lo avisaba. `registry_version` sigue en el `header`, y son dos números
distintos a propósito.

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

`fps_min_met` es `fps_real >= fps_min · (1 − 0,005)`, con **tolerancia del
0,5 %**: la tabla del arnés barre en fps nominales enteros (240 · 120 · 60 · 30)
y las tasas de video reales son NTSC (239,76 · 119,88 · 59,94 · 29,97) más el
redondeo del propio teléfono —29,998 medido en el Galaxy S22 Ultra—, así que sin
tolerancia ningún clip real de 30 fps llegaría a un `fps_min` de 30. La
constante es `FPS_MIN_TOL` y está en un solo lugar
(`kinelab/metrics/registry.py`, función `fps_min_met`); `null_reason` sigue
diciendo los dos números sin redondear. Es otra regla que
`fps_min_for_gesture`, el chequeo del gate, que compara contra el umbral del
deporte **sin** tolerancia (`CAPTURA.md` §El gate de ingesta).

`judgment_allowed` se deriva en código, nunca se escribe a mano:

```
judgment_allowed = level == 1
                   and mdc is not None
                   and fps_min_met
                   and fps_provenance == "medido_aqui"
                   and view in metric.views
                   and mdc_validation == "material_real"
                   and reference is not None
                   and reference.kind == "range"
                   and reference.provenance not in ("estimacion", "sin_verificar")
                   and mdc <= reference.range_width
```

La condición de la procedencia del fps es ADR-016: con la tasa de cuadros sin
verificar el número se muestra —es descriptivo— pero no se compara contra nada,
porque el eje del tiempo es un supuesto y no una medición.

Las cuatro últimas son **ADR-019**, y son dos preguntas independientes: una
mira el instrumento y la otra, contra qué se compara.

- `mdc_validation` es un campo del registro con dos valores, `sin_validar` (el
  default) y `material_real`, y **no es una procedencia**: la procedencia dice
  de dónde sale un número —y el MDC del arnés es `medido_aqui`, lo medimos
  nosotros—, esto dice contra qué se lo validó. Vale `material_real` cuando el
  MDC se midió con el estimador real, sobre material real, por el camino de
  captura de la toma, con los eventos contra etiquetas humanas, la deriva de
  cámara medida, la escala trazable y los intrínsecos del teléfono calibrados
  con tablero. Un MDC del arnés, de cualquier nivel, **no** alcanza.
- **Esta fórmula corrige la línea que decía `reference is None or mdc <=
  reference.range_width`**, que dejaba pasar una referencia descriptiva sin
  rango. `CONTEXTO.md` §Vocabulario define juicio como *comparar contra un
  rango*: sin rango no hay contra qué juzgar, y la condición vieja habilitaba
  juicio justamente en el caso en que no hay nada contra qué comparar. De ahí
  salieron los 21 `judgment_allowed: true` del 15/9 que la auditoría del 16/9
  revisó uno por uno: aritmética exacta en los 21, ninguno defendible.
- Las procedencias `estimacion` y `sin_verificar` quedan afuera por la
  invariante 12: ante la duda, el hueco antes que el número inventado.

La razón por la que una métrica **no** es juicio no viaja en el sextuplo:
`$defs/metric` es `additionalProperties: false` y agregarle un campo sería un
bump de schema. Va a `warnings[]`, en frases para el entrenador.

### `summary`

```json
{
  "rep_count": 12,
  "reps_rejected": {"count": 2, "reasons": {"plausibility": 1, "manual_discard": 1}},
  "metrics": {
    "backswing_duration_ms": {"median": 871.0, "sd_abs": 34.2, "n": 10, "mdc": 21.0,
                              "repeatability": {"kind": "sd_abs", "value": null, "n": 10, "noise_floor": null,
                                                "null_reason": "sin piso de ruido medido del pipeline: …"}}
  }
}
```

**Mientras no haya piso de ruido medido, `repeatability.value` es `null` con su
`null_reason`** (ADR-019). El `n` se conserva —decir cuántas repeticiones
entraron no afirma nada sobre el valor— y vale igual para
`repeatability_scalar` y para `repeatability_curves`. `summary.metrics` es un
objeto libre en el schema, así que el campo entra sin tocar el contrato.

**`summary.gain` no está más** (ADR-018). El arnés midió que la velocidad
angular de una línea en el plano de imagen es el largo proyectado del segmento
disfrazado de °/s —11110 °/s contra 139,6 verdaderos en la línea de caderas
desde `down_the_line`, con la proyección colapsada a 3,6 px— y muere en las dos
vistas. La ganancia sigue siendo el **concepto** correcto (§Niveles, y
`CONTEXTO.md` §Vocabulario): lo que murió es medirla con una cámara sola por el
ángulo aparente de un segmento.

La repetibilidad **siempre** lleva `noise_floor`: el piso de ruido del propio
pipeline, medido corriendo el mismo clip con jitter o dos clips del mismo
gesto. Sin ese número, una parte de la "inconsistencia" es el instrumento, no
el atleta. Por eso, hoy que ese piso no existe, el motor no publica una SD con
`noise_floor: null` al lado: publica `value: null` con la razón. Medido en
`cortado3-lento.mp4`: la SD del backswing entre dos repeticiones dio 17,7 ms, y
la ambigüedad de los eventos que la producen es de 4 a 16 cuadros.

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
        definition="desplazamiento lateral del centro de pelvis Halpe26 respecto del address, en el plano de imagen, convertido a cm con la escala de la repetición (§La escala) y la estatura declarada del atleta",
        range=None,
    ),
    mdc=None,        # se llena desde truth/; None → judgment_allowed = False
    metric_version="1.0.0",
)
```

`fps_min` y `views` **se escriben desde la tabla del arnés**, no a mano. Una
métrica cuyo barrido muestra que muere por debajo de cierto fps recibe ese
número; una que colapsa desde una vista pierde esa vista.

### La escala: de píxeles a centímetros

Toda métrica en cm es un desplazamiento en píxeles dividido por **la estatura
declarada del atleta medida en píxeles**, y multiplicado por esa estatura en
metros. El divisor es lo que esta sección define, porque es un solo número que
multiplica a siete métricas: si está mal por un factor, las siete devuelven
números plausibles multiplicados por ese factor y nada los delata (cementerio 6
de `HERENCIA.md`).

**La escala es el máximo, dentro de la repetición, de la cadena de la estatura
proyectada** (`kinelab/metrics/core.py`: `stature_chain_px`,
`MetricContext.scale_px`):

- **la cadena** es la suma de los largos **proyectados** de
  tobillo → rodilla → cadera → hombro → cabeza, cada eslabón entre los puntos
  medios de los dos lados (la coronilla no tiene par). Son los mismos centros
  articulares de Halpe26 con los que el motor ya mide: ningún largo de segmento
  sale de una tabla antropométrica ni de un factor ajustado a un deporte.
- **el máximo** porque cada eslabón se acorta con la perspectiva y **nunca se
  alarga**: la cadena es una cota inferior de lo que mediría el sujeto de pie y
  paralelo al plano de imagen, y el cuadro en que más se acerca a esa cota es el
  más extendido de la repetición.
- antes del máximo, la cadena pasa por una **mediana móvil de 0,25 s**
  (`SCALE_SMOOTH_S`, en segundos y no en cuadros). Un máximo crudo lo rompe un
  solo cuadro con la cabeza en otro lado: medido sobre el mocap 64_01, una
  cabeza saltada 200 px durante 1 a 15 cuadros infla el máximo un 6,6 % y achica
  las siete métricas un 6,2 %; con la ventana, 0,0 %. Una racha mala tiene que
  durar más de media ventana (0,125 s) para pasar.
- **una escala por repetición**, no por cuadro: el tamaño del atleta no cambia
  durante el swing; lo que cambia es su extensión aparente.
- si la cadena no se puede medir en ningún cuadro de la repetición (faltan
  rodillas o tobillos en todos), se cae a la altura cabeza→tobillos del cuadro
  cero, que es la convención anterior: un número con su sesgo conocido antes que
  un `null`.

**Y queda escrito en el JSON, en dos lugares que no son el mismo número.**

El divisor de verdad es **por repetición**, y desde 2.1.0 viaja en `reps[]`:

```json
{"rep": 1, "frame_start": 1052, "frame_end": 1765,
 "scale_px": 783.9, "scale_source": "stature_chain_rep", "metrics": {…}}
```

`scale_source` tiene dos valores y sólo dos, porque son los dos caminos de
`px_to_cm`:

- **`stature_chain_rep`** — hay cadena: `scale_px` es el máximo de la cadena en
  la repetición y divide a todas sus métricas en cm.
- **`body_height_px_frame`** — la cadena no se pudo medir en ningún cuadro de la
  repetición, y cada métrica cayó a la altura de cuerpo **del cuadro de su
  propio evento cero**. Ahí `scale_px` es `null`, porque no hay un divisor
  único: dos métricas con eventos cero distintos se dividieron por números
  distintos. El fallback **sigue vivo** —un número con su sesgo conocido antes
  que un `null`—, lo que cambia es que ahora dice que lo es. La frase para el
  entrenador va a `warnings[]`: `$defs/metric` es `additionalProperties: false`
  y no admite un campo nuevo en el sextuplo.

Y el agregado sigue en `quality.scale_px`:

```json
"scale_px": {"value": 1089.6, "frame": 75, "method": "max_stature_chain_px"}
```

Es un solo número que multiplica a ocho métricas: si está mal por un factor,
las ocho devuelven valores plausibles multiplicados por ese factor y nada las
delata (cementerio 6 de `HERENCIA.md`). Por eso viaja con el **cuadro** en que
se midió —el del máximo de la cadena, que se puede ir a mirar— y con el método.
Hay una escala **por repetición**; con varias, el que se publica acá es la
**mediana entre repeticiones** y el cuadro es el de la repetición que la aporta,
nunca un promedio de cuadros (que no sería ningún cuadro). **Con dos o más
repeticiones, entonces, `quality.scale_px` no es el divisor de ninguna**, y el
`method` lo dice y manda a `reps[].scale_px`. Sin ninguna escala medible,
`value` y `frame` son `null` y `method` dice por qué.

**Una sola escala por pantalla.** La tabla por cuadro (`datos-por-cuadro.csv`)
divide cada fila por la escala de **la repetición que la contiene**, que es la
misma que usaron las métricas, y la publica fila por fila en la columna
`escala_px`. Un cuadro fuera de toda repetición **no tiene cm**: no hay ninguna
escala que sea la suya. Hasta el 20/9 esa tabla convertía con el
`body_height_px` de **cada cuadro** mientras las métricas usaban la de la
repetición, así que la misma pantalla mostraba dos números en cm para el mismo
evento sin que nada lo dijera: medido sobre los `pose.npz` guardados, de **1,7
a 4,4 cm** de diferencia —`pelvis_sway_impact_cm` de `cortado3-lento` daba 22,6
cm en las métricas y 26,99 en la tabla, contra un MDC de 2,42—. Es la misma
familia del cementerio 6 y 8 de `HERENCIA.md`: una constante de normalización
que nadie escribe devuelve números plausibles multiplicados por un factor.

**Por qué no la altura cabeza→tobillos del address, que es lo que había.** Un
golfista en address está agachado hacia la pelota, o sea **hacia la cámara** en
`face_on`: el tronco se inclina sobre el eje óptico y en la imagen no se ve
girar, se ve más corto. Medido sobre los **diez swings de mocap del sujeto 64 de
CMU** (`data/examples/cmu-mocap/`, un solo sujeto — no es una tabla de
referencia), la altura cabeza→tobillos del address mide **0,891 ± 0,006** de la
estatura, así que la escala vieja sobre-leía **×1,123** toda métrica en cm.
Sumar los largos de segmento **en el address** no arregla nada (mide 1533 px
contra 1532: agacharse hacia la cámara engaña por igual a las dos); lo que lo
arregla es mirar el cuadro extendido.

| candidata a divisor | px (media de 10) | \|sesgo\| medio contra la verdad 3-D |
|---|---|---|
| cabeza→tobillos en el address (la anterior) | 1532,5 | 1,035 cm |
| cadena en el address | 1533,1 | 1,032 cm |
| máxima extensión vertical de la repetición | 1584,1 | 0,777 cm |
| **máximo de la cadena en la repetición** | **1648,4** | **0,493 cm** |
| la escala exacta (sólo existe con verdad 3-D) | 1720,6 | 0,399 cm |

La última fila es el piso: con la escala exacta lo que queda es error de
**proyección**, que ninguna convención de escala puede tocar. Queda un
**+4,4 % residual**, y es geométrico: la cadena arranca en el tobillo y la
estatura declarada arranca en el piso. Se reproduce con
`cd truth && .venv/bin/python -m kinelab_truth.mocap 64 --escala`.

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
  nombre viejo. Métrica nueva y opcional es minor. Va en **2.1.0**.

  **2.1.0 es minor, sin discusión**: entran **dos campos nuevos y opcionales**,
  `reps[].scale_px` y `reps[].scale_source` (§La escala). Un `analysis.json`
  2.0.0 sigue validando contra el schema nuevo —no le falta nada obligatorio— y
  ningún lector se rompe. **Ningún valor publicado cambia**: los dos campos
  dicen cuál era el divisor que ya se estaba usando, así que tampoco se mueve
  ningún `metric_version` ni el `registry_version`. Van opcionales y no
  requeridos a propósito: hacerlos obligatorios habría invalidado los
  `analysis.json` 2.0.0 ya escritos, que es lo que §Versionado llama major, y
  para eso habría hecho falta la excusa que se usó en el bump de
  `fps_provenance` (§Desviaciones). El motor los escribe **siempre**, en `null`
  cuando no hay escala: un `null` nunca se omite.

  Lo que se arregla con ellos: `quality.scale_px` es la **mediana entre
  repeticiones**, así que con dos o más **no es el divisor de ninguna**, y la
  tabla por cuadro no tenía de dónde sacar la escala correcta. Convertía con el
  `body_height_px` de cada cuadro y las métricas con la de la repetición: dos
  números en cm para el mismo evento en la misma pantalla, de 1,7 a 4,4 cm de
  diferencia en los clips reales, y ninguno decía cuál usaba.

  **Por qué 2.0.0 es major, sin discusión**: se **sacan dos campos requeridos**,
  `summary.gain` y `events[].sequence_order` (ADR-018). Un `analysis.json` 1.2.0
  no valida contra el schema nuevo —le sobran dos claves— y un lector que
  espere `summary.gain` se rompe. Es exactamente el caso que §Versionado llama
  major, y acá no hay ninguna de las tres razones que hicieron minor a los bumps
  anteriores: no es un campo nuevo, el valor no se corrigió, **el campo no
  existe más**.

  Con el schema abierto entran, en el mismo bump, tres cosas que estaban
  decididas y sin escribir (informes del 13 y del 14):

  1. **`metric_version` en cada sextuplo**, obligatorio. El contrato lo declaraba
     por métrica y el JSON no lo llevaba: el bump que avisa que las ocho métricas
     en cm cambiaron de valor con la escala del 14 **no se podía leer desde un
     análisis**.
  2. **`quality.scale_px`** con `{value, frame, method}`: el divisor de esas ocho
     métricas, que hasta hoy no quedaba escrito en ningún lado (§La escala).
  3. **`events[].<evento>.subframe.mdc`**, opcional, con su unidad, su
     procedencia y su fuente. Acá se define el lugar y el validador; el número lo
     escribe quien lea la tabla del arnés.

  Los tres serían minor por sí solos —dos campos nuevos y uno opcional—; van
  juntos en el major porque el major ya estaba, y abrir el schema dos veces para
  lo mismo es peor.
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
  número, mejorar una métrica invalida el historial del atleta. Los dos viajan
  en el JSON: `registry_version` en el `header`, `metric_version` en cada
  sextuplo. Hoy: registro de golf **0.3.0**; las ocho métricas en cm en
  **1.1.0** y las seis restantes (cuatro duraciones, tempo y dos rodillas) en
  1.0.0.
- **`registry_version` del registro de golf `0.2.0 → 0.3.0` por ADR-019**, en un
  bump **minor**. La regla de `judgment_allowed` sumó dos condiciones y las
  catorce métricas pasaron de "podrían ser juicio" a "no lo son": 21 de 21 se
  apagaron en `cortado3-lento.mp4`. Es minor y no major porque **ningún valor
  cambia** —por eso tampoco se mueve ningún `metric_version`, y el
  `schema_version` de `analysis.json` sigue en 2.0.0: no entra ni sale ningún
  campo—; lo único que se apaga es la bandera que decía que ese valor se podía
  comparar contra algo. El registro genérico del motor
  (`kinelab/metrics/registry.py`) queda en 0.1.0: sigue vacío.
- **Cambiar la convención de escala (§La escala) es `metric_version` minor en
  las siete métricas en cm** — `1.0.0 → 1.1.0` — y `registry_version` minor
  (`0.1.0 → 0.2.0`). `schema_version` de `analysis.json` **no** se toca: no se
  renombró ningún campo ni cambió ninguna unidad (siguen en cm); lo que cambió
  es el valor. Por qué minor y no major, con los tres números:
  1. **Qué se mide no cambió.** Los mismos dos keypoints, los mismos dos
     eventos, el mismo eje, la misma unidad. Lo que cambió es el divisor, que
     es del motor y no de la métrica: la misma corrección les entra a las siete
     a la vez.
  2. **El movimiento queda por debajo del MDC de cada métrica** (los MDC de
     `sports/golf/mdc.yaml`, la tabla del arnés). Medido: sobre los diez trials
     de mocap el cambio más grande es 1,45 cm (`pelvis_sway_top_cm`) contra un
     MDC de 2,87; sobre los dos clips reales del S22, 1,7 cm
     (`pelvis_sway_impact_cm`) contra 2,42. Ningún valor
     histórico cruza un umbral por esto — y hoy, además, ningún
     `judgment_allowed` es verdadero (todo `sin_verificar`, ADR-016). El cambio
     es proporcional (−7 % en el mocap, −20 % en los clips del S22), así que a
     partir de desplazamientos de ~12 cm **sí** pasa el MDC: ahí el
     `metric_version` es lo único que avisa, y por eso se bumpea igual.
  3. **No hay historial que invalidar.** No existe ninguna sesión en
     `data/sessions/`; los únicos `analysis.json` son de `data/exploracion/` y
     de las carpetas `.kinelab`, que se rehacen con un comando. Y re-analizar
     conserva el anterior con su `engine_version` (invariante 18).

  Sería **major** si alguna de esas tres dejara de valer: un atleta con
  historial y juicio habilitado, o un cambio que supere el MDC en el rango de
  uso, o un cambio en qué se mide y no en cómo se escala.
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
