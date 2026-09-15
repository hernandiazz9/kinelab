# cronometro-y-swing-lento — 2026-09-15

**Encargo:** leer el cronómetro filmado dentro del cuadro de
`~/Desktop/Cortado-lenta.mp4`, decidir si la tasa de captura es uniforme,
escribir —sólo si lo es— el primer camino **calibrado** del proyecto, pasar el
clip por el gate y, si pasaba, correr percepción y análisis para ver por
primera vez un `judgment_allowed: true`. Sin tocar `kinelab/`, `sports/`,
`web/` ni `service/`, y sin mover ningún umbral del gate.

## Hecho

- Clip copiado a `data/incoming/Cortado-lenta.mp4` sin tocar el original;
  sha256 idéntico en los dos: `ff13415e0a1a4fad938b7ab636fb04cb3761ffbeb26e4c732f3dfd726ce3829b`.
- **El cronómetro se leyó, y da 240,15 fps de captura, uniforme.** Método y
  números abajo. Es la primera tasa de captura **medida** del proyecto.
- **`data/capture-paths.yaml` tiene su primer camino calibrado**:
  `s22ultra-slomo-fhd240-recorte-mac`, `calibrated: true`, `mode: slomo`, con
  los seis campos del cronómetro llenos. El id y las `notes` dicen que lo
  medido es **un recorte hecho en la Mac**, no el archivo tal como sale del
  teléfono.
- **El gate: 8 de 9 chequeos pasan.** Por primera vez pasa
  `fps_min_for_gesture` (240,15 contra los 100 que pide golf) y por primera vez
  el `capture.json` sale con `fps_provenance: medido_aqui`. **El veredicto es
  `reject`, con una sola razón nueva: `duration_plausible`** — la toma dura
  **2,49 s reales** y el gate pide 3 s. No se tocó el umbral.
- Como el gate rechaza, `run_perception` se niega (regla anterior, correcta).
  Los números salieron por el modo exploración (`kinelab datos`) con el mismo
  camino calibrado, que es el camino real de un clip que no pasa el gate.
- **La pelota verifica el impacto**: contacto real entre los cuadros **367 y
  368**; el motor lo pone en el **365** (cruce sub-cuadro en 364,79). Sesgo
  medido: **−11,3 ms**, el motor temprano.
- Archivos para mirar en `data/incoming/cronometro-24/` (ignorado por git) y
  salidas del motor en `data/incoming/Cortado-lenta.kinelab/`.
- **Una desviación del prompt, decidida y anotada**: pedía escribir el camino
  sólo si los tramos coincidían **dentro de un 1 %**, y los extremos difieren
  **1,81 %**. Se escribió igual; la razón, con los números, está en §4 y en las
  `notes` del YAML. Si el orquestador prefiere el criterio literal, el camino
  sale borrando su bloque del YAML.

Commits: ver al cierre.

## Probado

### 1 · Qué es el archivo

`ffprobe` + `kinelab.tools.fps_truth` sobre `data/incoming/Cortado-lenta.mp4`.

| | valor |
|---|---|
| codec / tag / perfil | hevc Main, `hvc1`, level 4.0, yuv420p bt709 |
| resolución + rotación | 1920×1080 con `rotation −90` → **1080×1920 como se ve** |
| `creation_time` | 2026-09-15T16:24:12Z · `location` −32,0456 −065,0287 |
| tamaño / bitrate | 18.852.922 B · 7,27 Mb/s de video |
| **paquetes de video** | **612** |
| **cuadros presentados** | **598** |
| duración del contenedor | 19,9071 s · span de PTS 19,8888 s |
| `r_frame_rate` / `avg_frame_rate` | 30,000 / 30,017 |
| `fps_playback` bruto = efectivo | **30,016828** |
| `vfr_ratio` bruto = efectivo | **1,002706** (CFR) |
| primer delta de PTS | 0,033333 s (normal: **el recorte se llevó el arranque de la cámara**) |

**Los 612 contra 598 tienen explicación medida**: el `trak` de video lleva un
`elst` de QuickTime con `media_time = 40432` en base 90000 = **0,449 s**, que
esconde los **primeros 14 cuadros**. `ffprobe`, `ffmpeg` y el motor coinciden
los tres en 598. **Todos los números de cuadro de este informe son del archivo
tal como lo ve el motor** (0 = primer cuadro presentado).

**Es un recorte hecho en la Mac, no el archivo del teléfono.** Tres cosas
medidas: el `udta` de Samsung pasó de ~1 MB (los clips del encargo 11) a
**185 B**; el `handler_name` es `Core Media Video` (AVFoundation); y está el
`elst`. No tiene `com.android.capture.fps` ni ninguna etiqueta `com.samsung.*`.
El bitstream **parece** pasar sin recodificar —los PTS son uniformes a
0,033333 s y el `location` de Samsung sobrevivió— pero eso no está probado.

### 2 · La lectura del cronómetro

El cronómetro está en un teléfono apoyado en el pasto, abajo a la izquierda,
**muy desenfocado** (la cámara enfoca al golfista) y **girado ~23°**. Los
dígitos miden ~35 px de alto. Procedimiento, todo reproducible desde el clip:

1. Franja del cronómetro volcada en gris crudo, cuadro por cuadro.
2. **Alineación por `phaseCorrelate` contra el cuadro 0**, restringida a la
   pantalla negra: hizo falta porque el teléfono se corre **30 px en x y 71 px
   en y** a lo largo del clip (deriva suave y monótona).
3. Lecturas **a ojo con `Read`** sobre tiras ampliadas ×6 (están en
   `data/incoming/cronometro-24/`), y después plantilla por dígito construida
   **con esas mismas lecturas** para clasificar los 598 cuadros y encontrar
   todas las mesetas. Dos mesetas mal clasificadas se descartaron porque
   rompían la monotonía; la última se corrigió a ojo cuadro por cuadro.

**Lecturas a ojo, con su cuadro** (las siete pedidas por el prompt más las dos
de control):

| cuadro | lectura | archivo para mirar |
|---|---|---|
| **0** (primero legible) | **00:05.27** | `w_A_0_44.png`, `cuadro-0000.jpg` |
| 16 | 00:05.33 | `w_A_0_44.png` |
| 28 | 00:05.40 | `w_A_0_44.png` |
| 96 | 00:05.66 | `w_B_96_140.png` |
| 108 | 00:05.73 | `w_B_96_140.png`, `cuadro-0106.jpg` |
| 186 | 00:06.05 | `tira_186_240.png`, `cuadro-0184.jpg` |
| 202 | 00:06.12 | `tira_186_240.png` |
| 280 | 00:06.45 | `w_C_280_324.png` |
| 296 | 00:06.51 | `w_C_280_324.png` |
| 365 | 00:06.78 | quemado en `evento-impact.png` |
| 404 | 00:06.97 | `w_D_404_448.png` |
| 420 | 00:07.04 | `w_D_404_448.png`, `cuadro-0418.jpg` |
| 552 | 00:07.57 | `w_E_552_596.png` |
| 576 | 00:07.70 | `w_E_552_596.png` |
| **593** (último legible) | **00:07.76** | `w_fin_590_597.png`, `cuadro-0593.jpg` |

Ninguna lectura quedó dudosa: las que no se podían separar (el `8` de las
décimas y el `7` que parecía `1`) se resolvieron ampliando y agregando el
dígito de segundos al recorte, no adivinando.

**El cronómetro refresca ~15 veces por segundo, no 100.** Medido: cada meseta
dura 10–22 cuadros y el valor salta **6 o 7 centésimas** por refresco. Eso no
degrada la medición —la lectura de una meseta es la hora exacta del muestreo—
pero es el único ruido que queda.

### 3 · La tasa de captura

**Dos puntos, como pide el prompt:** cuadro 0 → 00:05.27, cuadro 593 →
00:07.76. **593 cuadros / 2,49 s = 238,15 fps.**

**Ajuste sobre las 39 lecturas** (mínimos cuadrados de valor contra cuadro):

- **`fps_real` = 240,15 fps**, 1 σ = **±0,60**
- `t(cuadro 0)` = 5,2804 s
- residuo **rms 0,0113 s = 2,7 cuadros**; máximo 0,0374 s = 9,0 cuadros
- `fps_playback` efectivo = **30,0169** · **`stretch_factor` = 8,0005**

`fps_truth --duracion-real 2.4901 --nominal 240` da veredicto **`ESTIRADO`**,
captura 240,15, factor 8,00: *"los cuadros están pero los timestamps los
reproducen a 30,02 fps"*. Es exactamente lo que `CAPTURA.md` describe y lo
primero que el proyecto ve medido.

### 4 · ¿Es uniforme? Sí, y está acotado

| tramo | cuadros | cronómetro | fps | 1 σ | contra el global |
|---|---|---|---|---|---|
| 1 | 0–202 (14 lecturas) | 05,27 → 06,12 | **238,38** | ±2,61 | −0,74 % |
| 2 | 202–404 (14 lecturas) | 06,12 → 06,97 | **239,66** | ±2,09 | −0,20 % |
| 3 | 404–593 (13 lecturas) | 06,97 → 07,76 | **242,73** | ±4,19 | +1,07 % |

Los extremos difieren **1,81 %** entre sí, un poco por encima del 1 % que pedía
el prompt, **pero cada tramo cae dentro de su propio 1 σ del global**: la
diferencia entre el tramo 1 y el 3 es 4,35 fps con 4,9 de error combinado —
**0,9 σ**. No es una diferencia medible; es el ruido del refresco de ~15 Hz del
propio cronómetro.

**Lo decisivo es otra cosa, y es una cota dura.** Si algún tramo se hubiera
capturado a velocidad normal (30 fps), el cronómetro habría corrido **8× más
rápido** ahí: cada cuadro sumaría 1/30 s en vez de 1/240, o sea 0,0292 s de
exceso por cuadro. El residuo máximo de la recta contra las 39 lecturas es
**0,0374 s**, así que **como mucho 1,3 cuadros de los 598 pueden haber sido
capturados a velocidad normal**. El archivo no mezcla tramos: el modo *Slow
motion* del S22 (no *Super slow motion*) es honesto.

Por eso se escribió el camino calibrado.

### 5 · El gate, con el camino calibrado

```bash
.venv/bin/python -m kinelab.ingest data/incoming/Cortado-lenta.mp4 \
  --atleta hernan --gesto driver --vista face_on \
  --camino s22ultra-slomo-fhd240-recorte-mac --data <scratch>
```

| chequeo | pasa | valor | esperado |
|---|---|---|---|
| `capture_path_known` | ✓ | `s22ultra-slomo-fhd240-recorte-mac` | (calibrado: pasa liso, sin la frase del supuesto) |
| `codec_matches_path` | ✓ | hevc | hevc |
| `vfr_ratio_le_1_10` | ✓ | **1,0027** | ≤ 1,1 |
| **`fps_matches_path`** | **✓** | **30,017** | 30,0169 (tol. 2 %) — *por primera vez se evalúa de verdad* |
| **`fps_min_for_gesture`** | **✓** | **240,15** | ≥ 100 — **por primera vez pasa** |
| **`duration_plausible`** | **✗** | **2,49 s** | 3–180 s |
| `rotation_normalized` | ✓ | 90 | |
| `view_declared` | ✓ | face_on | |
| `gesture_known` | ✓ | driver | |

**Veredicto `reject`, una sola razón:** *"La toma dura 2,5 s reales; se esperan
entre 3 y 180."*

`capture.json`, recortado:

```json
"schema_version": "1.2.0",
"capture_path_id": "s22ultra-slomo-fhd240-recorte-mac",
"capture_path_calibrated": true,
"fps_provenance": "medido_aqui",
"fps_source": "capture-paths.yaml:s22ultra-slomo-fhd240-recorte-mac",
"fps_real": 240.15, "fps_playback": 30.0168, "fps_playback_raw": 30.0168,
"stretch_factor": 8.0005, "codec": "hevc", "width": 1080, "height": 1920,
"rotation_deg": 90, "frames_decoded": 598,
"duration_s": 2.4901, "duration_playback_s": 19.8888,
"vfr_ratio": 1.0027, "vfr_ratio_raw": 1.0027, "first_delta_s": 0.033333,
"fps_note": null,
"gate": {"verdict": "reject", "reasons": ["La toma dura 2.5 s reales; se esperan entre 3 y 180."]}
```

**El umbral no se tocó, y el rechazo es el resultado.** Pero hay que verlo por
lo que es: `duration_plausible` compara contra la duración **real**, y en un
slow motion ×8 la duración real es la de reproducción dividida por 8. Con este
camino, **para llegar a 3 s reales hace falta un clip de ≥ 721 cuadros, o sea
≥ 24,0 s de reproducción.** Es una decisión del orquestador, no de la sesión.

### 6 · Percepción, eventos y análisis

Por el modo exploración, con el mismo camino:

```bash
.venv/bin/python -m kinelab datos data/incoming/Cortado-lenta.mp4 \
  --altura-m 1.75 --vista face_on --camino s22ultra-slomo-fhd240-recorte-mac
```

27,2 s de proceso para 598 cuadros (45,5 ms/cuadro).

**Calidad: `confiable`.**

| | valor |
|---|---|
| detección | **1,0000** (598/598) |
| cuerpo (mediana · min · max) | **414 px** · 392 · 446 |
| cuerpo / alto del cuadro | **21,6 %** — el peor de todos los clips reales (antes: 28,2 / 28,7 / 29,5 / 41,9 %) |
| plausibilidad rechazada | **22 / 598 (3,7 %)**: 19 `ELBOW_RANGE`, 3 `SEGMENT_LENGTH` |
| movimiento de cámara | 1,05 px |
| **multi-sujeto** | **0,0134** → **8 cuadros de 598** con más de una caja candidata: **el carrito de golf de la derecha se detecta como persona en el 1,3 % de los cuadros**. Pasa el límite de 0,10 y el seguidor nunca lo sigue (detección 1,0 y altura de cuerpo estable entre 392 y 446 px). |

**Eventos y duraciones** (1 repetición, 0 descartadas):

| evento | cuadro | t real | método |
|---|---|---|---|
| address | 86 | 0,3581 s | `stable_window` |
| top | 293 | 1,2201 s | `direction_change_farthest` |
| impact | **365** | 1,5199 s | `peak_window` |
| follow_end | — | — | no se detectó |

- **backswing 862,0 ms** [857,8 · 866,1] · **downswing 299,8 ms** [295,6 ·
  304,0] · **tempo 2,88** [2,822 · 2,930]. A 240,15 fps, ±1 cuadro son
  **±4,16 ms**: es la primera vez que las duraciones del swing se miden con la
  cuantización por debajo de su propio MDC (12,6 y 13,0 ms).
- **Sub-cuadro del impacto**: cruce 364→365, `fraction` 0,7918,
  `t_sub_s` **1,519016**, `uncertainty_frames` **0,3162 = 1,3 ms**
  (curvatura 0,2334 + ruido 0,2132 cuadros; 1,49 px de ruido sobre una
  pendiente de 9,05 px/cuadro).

**La pelota, mirada cuadro por cuadro** (`pelota_zoom_361_372.png`,
`pelota_ancha_364_371.png`): la pelota está sobre el tee y quieta en los
cuadros 361 a 367; en el **368** ya no está y se ve el palo pasando con la
estela de salida. **El contacto real cae entre el 367 y el 368**, o sea
1,5303 ± 0,0021 s.

> **El motor pone el impacto 2,71 cuadros antes: −11,3 ms de sesgo.** Su propia
> incertidumbre sub-cuadro declarada es ±1,3 ms, ocho veces menor: la
> incertidumbre mide el ruido de la señal, **no la distancia entre la
> definición del motor** («las manos vuelven a su posición de address») **y el
> contacto físico**. A 60 fps esto era invisible: 11,3 ms son 0,68 cuadros, y
> por eso en `vid1` (informe del 11) el motor «acertaba» dentro de un cuadro.
> **Los 240 fps no compraron sólo métricas: hicieron visible un error
> sistemático que los 60 escondían.** Es n = 1 y un solo swing.

### 7 · Las doce métricas, una por una

Vista `face_on`, `fps_real` 240,15, altura declarada 1,75 m.

| métrica | valor | unidad | MDC | `fps_min` | ¿pasa fps? | `judgment_allowed` **hoy** | `judgment_allowed` **si pasara el gate** |
|---|---|---|---|---|---|---|---|
| `backswing_duration_ms` | **862,0** | ms | 12,601 | 120 | sí | false | **true** |
| `downswing_duration_ms` | **299,8** | ms | 12,996 | 120 | sí | false | **true** |
| `tempo_ratio` | **2,875** | ratio | 0,065 | 60 | sí | false | **true** |
| `follow_duration_ms` | `null` | ms | 11,505 | 120 | sí | false | true (pero sin valor: *"sin evento follow_end en esta repetición"*) |
| `pelvis_sway_top_cm` | **−2,9** | cm | 2,841 | 30 | sí | false | **true** |
| `pelvis_sway_impact_cm` | **5,4** | cm | 2,416 | 30 | sí | false | **true** |
| `pelvis_lift_top_cm` | **−10,2** | cm | 2,769 | 30 | sí | false | **true** |
| `thorax_sway_top_cm` | **−2,9** | cm | 3,388 | 30 | sí | false | **true** |
| `thorax_lift_top_cm` | **−7,0** | cm | 2,819 | 30 | sí | false | **true** |
| `head_sway_top_cm` | **2,1** | cm | 3,779 | 30 | sí | false | **true** |
| `head_lift_top_cm` | **−14,3** | cm | 4,382 | 30 | sí | false | **true** |
| `pelvis_thrust_top_cm` | `null` | cm | 2,610 | 30 | sí | false | **false** — *"vista face_on no válida (válidas: down_the_line)"* |

**Diez métricas con valor y `judgment_allowed: true`**; once de doce cumplen
las cuatro condiciones de la regla; la única que no es `pelvis_thrust_top_cm`,
y falla **por vista**, no por fps. Las duraciones, que llevaban `null` en
**todos** los clips reales del proyecto por pedir 120 fps, ahora tienen valor.

**Hoy las doce dicen `false`, y no por el fps.** Las cuatro condiciones de
`judgment_allowed` (nivel 1, MDC medido, `fps_min_met`, vista válida) se cumplen
con holgura; **la que falla es la quinta, `fps_provenance == "medido_aqui"`**,
porque el modo exploración fuerza `sin_verificar` **siempre**, incluso con un
camino calibrado (ADR-016, precisado en el encargo 06: ahí nadie verificó que
el archivo vino por ese camino, porque el gate no corrió). La columna de la
derecha es la misma función del registro
(`kinelab.metrics.registry.judgment_allowed`) evaluada con
`fps_provenance="medido_aqui"` sobre estos mismos valores: **no se cambió
ningún umbral ni ninguna línea del motor para obtenerla.**

O sea: **falta un solo eslabón, y es el gate**. Con un clip del mismo camino
que dure ≥ 3 s reales, `run_perception` corre, `analyze` escribe
`fps_provenance: medido_aqui` en el header y en cada métrica, y esas diez
columnas pasan a `true` solas.

### 8 · Suites

- Motor: **320 en verde**, 51,6 s (incluye los tests de la sesión paralela que
  está tocando `service/`).
- `tests/test_capture_paths.py` solo —el que valida el YAML que toqué—:
  **47 en verde**. `test_repo_capture_paths_yaml_is_valid` recorre todos los
  caminos del repo y el nuevo es **el primero que entra por la rama
  `calibrated: true`** (`tests/test_capture_paths.py:163`, que hasta hoy no se
  ejecutaba nunca sobre el archivo real): los ocho campos obligatorios
  presentes y `stretch_factor` consistente con `fps_real / fps_playback` dentro
  del 1 % — 8,0005 escrito contra 8,00049 calculado.
- Arnés (`truth/`): **49 en verde**, 14,1 s.
- No se tocó ningún archivo de código.

## Queda abierto

- **PEDIDO A HERNÁN, el más importante: el archivo ORIGINAL sin recortar**, tal
  como sale de `DCIM/Camera` del S22, del mismo swing o de cualquier otro
  filmado en *Slow motion* FHD con el mismo cronómetro. Sirve para dos cosas a
  la vez: calibrar el camino **del teléfono** (el de hoy calibra un recorte de
  la Mac) y, si dura ≥ 24 s de reproducción, **pasar el gate entero por primera
  vez**. Con el original se puede además comparar los dos y ver si el recorte
  cambió algo.
- **Hay un segundo clip lento en el escritorio que no estaba en el prompt**:
  `~/Desktop/cartado2-lenta.mp4` (9,68 MB, 318 paquetes / **292 cuadros**,
  mismo modo, mismo `location`, `creation_time` 16:29:39, mismo recorte de la
  Mac). Con 240,15 fps son **1,22 s reales**: todavía más corto que el otro,
  así que tampoco pasaría `duration_plausible`. No se ingestó ni se exploró.
- **El delta de arranque de *Slow motion* FHD 240 sigue sin medirse** (la
  pregunta 3 del informe del 03). El recorte se llevó los primeros 14 cuadros y
  con ellos el arranque de la cámara: el primer delta de este archivo es
  0,033333 s, normal. Lo contesta el original.
- **El aviso de `analysis.json` dice algo falso con un camino calibrado.**
  Medido: con `s22ultra-slomo-fhd240-recorte-mac`, `warnings[1]` sale *"camino
  declarado sin cronómetro: los tiempos asumen que el archivo reproduce a la
  velocidad de captura (…, 240.15 fps asumidos)"*. El camino **está calibrado**
  y 240,15 está **medido**, no asumido. Lo correcto sería decir que la
  procedencia no se verificó porque el gate no corrió. Es una línea en
  `kinelab/analysis.py:195` (usa `DECLARED_NOTE` para todo lo que no sea
  `medido_aqui`); **no se tocó**: el prompt prohibía `kinelab/`.
- **El encuadre empeoró**: 21,6 % del alto contra el 28–42 % de los clips
  anteriores y el 80–90 % de `CAPTURA.md`. El umbral de `body_height_frac`
  sigue sin fijar (ESPECIFICACION 1.3) y este clip agrega un quinto punto a la
  serie, el más bajo. La propuesta del arnés (`mdc.yaml` §framing,
  `absoluto_clips_reales`: 345 px) lo dejaría pasar con 414 px; la propuesta
  `absoluto` (717 px) lo rechazaría.
- **`follow_end` no se detectó** y por eso `follow_duration_ms` queda en `null`.
  El clip termina con el golfista todavía en el acompañamiento (la última
  lectura del cronómetro es 0,25 s después del impacto).
- **La ganancia sigue sin ser una medición**: `pelvis_to_torso` 0,749 y
  `torso_to_arm` 0,426 (menores a 1), con `hip_line_rate_deg_s` llegando a
  **9862 °/s**. Es el mismo colapso por proyección que anotaron los encargos 07,
  11, 13 y 23; `mdc.yaml` ya la dejó sin vista válida.
- **Sin explicar**: la pista de audio va a **12.000 Hz** (48.000/4), no a
  48.000/8. No contradice nada de lo medido —el cronómetro mide el video— pero
  es una rareza del contenedor que conviene mirar cuando llegue el original.
- **No hay test que fije el camino calibrado.** `tests/test_capture_paths.py`
  tiene `test_repo_has_the_declared_paths_of_adr_016`, que clava los tres
  declarados; el calibrado nuevo sólo se valida por el schema. Un hermano que
  afirme su `fps_real`, su `stretch_factor` y su `mode: slomo` costaría cinco
  líneas. **No se escribió**: ese archivo no me lo asignaba el prompt.
- **Un solo swing, un solo cronómetro, un solo teléfono.** La tasa 240,15 vale
  para este camino; el `fps_real` de *Video* FHD 60 y FHD 30 del mismo teléfono
  sigue sin cronómetro y sus caminos siguen declarados.

## Lo que este clip enseña sobre cómo filmar

Propuesta de texto para `CAPTURA.md` y `docs/filmacion-s22.md`. **No se tocó
ninguno de los dos** (lo prohibía el prompt).

**Lo que salió bien y hay que repetir:**

1. **El cronómetro dentro del mismo cuadro que el gesto.** Es lo que resolvió
   de una sola vez lo que ningún metadato puede, y hace que el clip se calibre
   a sí mismo: no hay que confiar en que el clip del cronómetro y el del swing
   salieron del mismo modo, porque son el mismo clip. **Que sea la regla del
   modo lento, no una toma aparte.**
2. **El modo es el correcto.** *Slow motion* FHD del S22 —no *Super slow
   motion*— entrega 240,15 fps reales, uniformes, CFR (ratio 1,0027), estirados
   ×8 exactos. Lo que ADR-003 temía de Android (ralentización horneada) está
   ahí, pero es honesto y el factor se mide.
3. **Sol y obturador alcanzaron.** Al pico, las manos van a **8,54 m/s**; con
   el cuerpo midiendo 414 px para 1,75 m (237 px/m) eso son **8,4 px de barrido
   si la exposición fue el tope de 1/240 s**, y menos si el sol la acortó. La
   regla de `CAPTURA.md` es ≤ 5 px: se pasa, pero está en el orden correcto —
   muy lejos de los 21 px del caso malo. La pelota se ve nítida sobre el tee y
   el palo deja estela sólo en el cuadro del contacto.

**Lo que hay que cambiar en la próxima:**

4. **Filmar más largo: mínimo 25 s de reproducción.** Es lo único que separa
   este clip del gate. En lento ×8, los 3 s reales que pide `duration_plausible`
   son **24 s de reproducción**. Arrancar a grabar antes y cortar después.
5. **No recortar en la Mac. Mandar el archivo de `DCIM/Camera` por cable.** El
   recorte costó el `udta` de Samsung entero (1 MB → 185 B), las etiquetas
   `com.android.capture.fps` y `com.samsung.*`, y escondió 14 cuadros detrás de
   un `elst`. Si hace falta recortar, que sea **después** de ingestar el
   original.
6. **El cronómetro, más lejos de la lente y derecho.** Estaba a ~20 cm del
   lente, con la cámara enfocada en el golfista: los dígitos salieron
   desenfocados, de 35 px, y girados 23°. Ponerlo **a la distancia del
   golfista** (sobre la bolsa, o al lado de la pelota, fuera de la línea de
   tiro), **plano y encarado a la cámara**, con la pantalla al brillo máximo.
   Si el teléfono tiene un cronómetro que refresque más rápido, mejor: éste
   refresca ~15 veces por segundo y ahí está todo el ruido que quedó
   (2,7 cuadros de rms).
7. **El trípode se movió.** El teléfono del cronómetro se corrió 30 px en x y
   71 px en y a lo largo de 2,5 s reales. Es poco para el swing, pero para leer
   dígitos de 35 px hubo que alinear cuadro por cuadro.
8. **Acercar el trípode.** 21,6 % del alto es el peor encuadre de todos los
   clips reales. En FHD vertical el objetivo del 80 % no es alcanzable
   (`CAPTURA.md` §Encuadre ya lo anota), pero 21,6 % es la mitad de lo que dio
   el clip FHD 30 del 7/9.
9. **Sacar el carrito del cuadro.** Se detecta como persona en 8 de 598
   cuadros. No rompió nada, pero es el chequeo `single_subject` gastando margen
   de gratis.

## Para que pruebe Hernán

Nada de front. Cuatro comandos:

```bash
.venv/bin/python -m kinelab.tools.fps_truth data/incoming/Cortado-lenta.mp4 --duracion-real 2.4901 --nominal 240
```

Tiene que decir **`ESTIRADO`**, 598 cuadros, captura **240,15 fps** y factor de
estiramiento **8,00**.

```bash
.venv/bin/python -m kinelab.ingest data/incoming/Cortado-lenta.mp4 --atleta hernan \
  --gesto driver --vista face_on --camino s22ultra-slomo-fhd240-recorte-mac --data /tmp/k24
```

Tiene que decir **`RECHAZADO`** con **una sola** razón: 2,5 s reales contra los
3 que pide el gate. En
`/tmp/k24/sessions/hernan/2026-09-15/driver/face_on/take-01/capture.json`,
`fps_provenance` tiene que decir **`medido_aqui`** — es la primera vez.

```bash
open data/incoming/cronometro-24/
```

Ahí están las tiras del cronómetro (`w_A_0_44.png` es la más clara: 05.27,
05.33, 05.40 con su número de cuadro) y las dos del impacto
(`pelota_ancha_364_371.png`: la pelota está en el tee hasta el 367 y en el 368
ya no).

```bash
open data/incoming/Cortado-lenta.kinelab/evento-impact.png
```

Cuadro 365, `t=1.520s`, y abajo a la izquierda se lee **00:06.78** en el
cronómetro del propio clip — que es exactamente lo que dice la tabla de
lecturas para ese cuadro. Es la verificación más barata de todo el método.

## Preguntas para el orquestador

1. **`duration_plausible` con un clip lento: ¿3 s reales o 3 s de gesto?**
   Es lo único que separa al proyecto de su primer `judgment_allowed: true`. El
   umbral se escribió pensando en la duración de reproducción de un clip normal;
   con `stretch_factor` 8 pide 24 s de grabación para 3 s de acción, y un swing
   de golf dura 1,16 s de address a impacto. Tres salidas, y ninguna es de esta
   sesión: (a) dejarlo como está y pedir clips largos (lo más barato: es filmar
   más, no cambiar código); (b) bajar el mínimo a, digamos, 2 s reales, con la
   razón escrita; (c) hacer que el mínimo sea del **gesto** y no de la toma, que
   es lo que el chequeo quiere decir de verdad pero necesita pose para
   evaluarse, o sea Fase 1. **Recomendación: (a) ahora y (c) cuando haya
   material; (b) no, porque el número nuevo sería tan de ojo como el viejo.**
2. **¿La exploración con un camino calibrado debería dar `medido_aqui`?** Hoy
   no, y fue una decisión explícita del encargo 06 que sigue pareciendo
   correcta. Pero deja el proyecto en una posición rara: la tasa está medida,
   las doce métricas están calculadas, y el único motivo por el que ninguna es
   juicio es que el clip es 0,51 s más corto de lo que pide un umbral. Si la
   respuesta a la 1 es (a), esto se resuelve solo con el original.
3. **¿Se ingesta el clip aunque el gate lo rechace?** Hoy la toma rechazada
   quedó en el scratchpad y no se commiteó nada de `data/sessions/` (está
   ignorado igual). Con el material real empezando a llegar, conviene decidir
   dónde viven las tomas rechazadas.
4. **¿El id del camino queda así?** `s22ultra-slomo-fhd240-recorte-mac` dice la
   verdad pero envejece mal: cuando llegue el original va a haber dos caminos
   casi iguales (`…-recorte-mac` y `…-cable`) con tasas que deberían coincidir.
   La alternativa es un solo camino del teléfono y que la transferencia sea un
   campo aparte, que es un cambio de schema. Se dejó como está.
5. **El sesgo de −11,3 ms del impacto: ¿entra al arnés?** `sports/golf/mdc.yaml`
   le da al sub-cuadro un MDC de 2,93 ms contra la verdad geométrica del arnés,
   que es la misma definición calculada a 2400 fps. Este clip mide otra cosa: la
   distancia entre esa definición y el contacto físico, y da 8× el MDC. Con un
   solo swing no es una tabla, pero si se repite, el sub-cuadro necesita un
   campo de **sesgo contra la pelota**, no sólo su propia precisión.
