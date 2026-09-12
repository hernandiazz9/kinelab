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
  capture-paths.yaml                 caminos de captura calibrados (ver CAPTURA.md)
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

`data/` está en `.gitignore` salvo `schemas/` y `examples/`.

---

## `capture-paths.yaml`

Un camino = dispositivo + modo + transferencia. Es **configuración**, no
inferencia. Un clip cuyo `capture_path_id` no está acá se rechaza.

Cada camino registra **dos tasas**: `fps_real`, la de captura, que sale del
cronómetro filmado; y `fps_playback`, la que el archivo reproduce, que sale de
los PTS. Su cociente es `stretch_factor`: 1,0 en video normal, 8,0 en un
Slo-Mo de 240 estirado a 30. El motor convierte los PTS a tiempo real con ese
factor, y el gate compara la reproducción del clip contra la del camino.

```yaml
schema_version: "1.0.0"
paths:
  - id: iphone17pro-video-1080p120-airdrop
    device: "iPhone 17 Pro"
    mode: video            # video | slomo
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

---

## `capture.json`

Escrito por `kinelab.ingest`. Nunca a mano después de la Fase 0.

```json
{
  "schema_version": "1.0.0",
  "athlete": "hernan",
  "gesture": "driver",
  "view": "face_on",
  "capture_path_id": "iphone17pro-video-1080p120-airdrop",
  "fps_real": 119.88,
  "fps_source": "capture-paths.yaml:iphone17pro-video-1080p120-airdrop",
  "fps_playback": 119.85,
  "stretch_factor": 1.0,
  "codec": "hevc",
  "width": 1920,
  "height": 1080,
  "rotation_deg": 0,
  "frames_decoded": 2398,
  "duration_s": 20.008,
  "vfr_ratio": 1.004,
  "recorded_at": "2026-09-14T10:32:11+10:00",
  "sha256_original": "…",
  "gate": {
    "verdict": "ok",
    "checks": [
      {"id": "codec_matches_path", "pass": true, "value": "hevc", "expected": "hevc"},
      {"id": "vfr_ratio_le_1_10", "pass": true, "value": 1.004},
      {"id": "fps_matches_path", "pass": true, "value": 119.85, "expected": 119.88, "tolerance": 0.02},
      {"id": "duration_plausible", "pass": true}
    ],
    "reasons": []
  }
}
```

Cuando `verdict` es `reject`, `reasons` es una lista de frases que el
entrenador puede leer: *"El clip está en H.264: pasó por 'Más compatible' o
por un transcodificador. Volvé a exportarlo con 'Mantener originales'."*

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
              source {pose_sha256, master_sha256, capture_path_id, fps_real}
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
  "address":    {"frame": 412, "t_s": 3.437, "tol_frames": 1, "method": "stable_window", "manual": false},
  "top":        {"frame": 517, "t_s": 4.313, "tol_frames": 1, "method": "d2_inflection", "manual": false},
  "impact":     {"frame": 548, "t_s": 4.571, "tol_frames": 1, "method": "peak_window", "manual": true},
  "follow_end": {"frame": 604, "t_s": 5.038, "tol_frames": 2, "method": "d2_inflection", "manual": false},
  "sequence_order": "indeterminado"
}
```

`sequence_order` toma `indeterminado` cuando dos picos caen dentro de ±2
cuadros. Nunca se fuerza un orden.

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
  "judgment_allowed": true,
  "null_reason": null
}
```

Cuando la métrica no se puede calcular, `value` es `null` y `null_reason` dice
por qué en una frase: `"fps_real 59.94 por debajo de fps_min 100"`,
`"vista down_the_line no válida para esta métrica"`, `"MDC no medido"`.

`judgment_allowed` se deriva en código, nunca se escribe a mano:

```
judgment_allowed = level == 1
                   and mdc is not None
                   and fps_min_met
                   and view in metric.views
                   and (reference is None or mdc <= reference.range_width)
```

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
  nombre viejo. Métrica nueva y opcional es minor.
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

*(vacío)*
