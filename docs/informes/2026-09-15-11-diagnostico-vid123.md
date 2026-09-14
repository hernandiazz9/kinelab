# diagnostico-vid123 — 2026-09-15

**Encargo:** decir qué son los tres clips que Hernán dejó en `~/Downloads`
(`vid1/vid2/vid3.mp4`), a qué tasa capturaron de verdad, si alguno permite
calibrar un camino de captura, qué dice el gate de cada uno, y cuánto cuesta
4K. Diagnóstico y medición, no código.

## Hecho

- Los tres copiados a `data/incoming/` (ignorado por git) sin tocar los
  originales: sha256 idéntico en origen y destino.
- **Ninguno de los tres es el cronómetro: los tres son swings.** Confirmado con
  Hernán: no se filmó. Por eso **no se escribió ningún camino calibrado** y
  sigue sin haber un `fps_real` medido de este teléfono en ningún modo.
- **Transferencia: WhatsApp en modo documento** (dicho por Hernán, y medido:
  no recomprimió, ver abajo). Camino declarado nuevo en
  `data/capture-paths.yaml`: `s22ultra-video-uhd60-whatsapp-doc`, `nominal_fps`
  60, `codec_expected` hevc, `calibrated: false`, los seis campos del cronómetro
  en `null`.
- Gate corrido sobre los tres con ese camino, exploración (`datos`) de los tres
  con altura 1,75 m, y el costo de UHD medido contra FHD con cinco corridas.
- Nada de código tocado: sólo `data/capture-paths.yaml`, `ESTADO.md` y este
  informe.

Commits: ver al cierre.

## Probado

### Ficha de los tres

Comandos: `shasum -a 256`, `ffprobe -v error -show_format -show_streams
-show_entries format_tags`, `.venv/bin/python -m kinelab.tools.fps_truth`.

| | **vid1** | **vid2** | **vid3** |
|---|---|---|---|
| sha256 (12 hex) | `f4d19a56db13` | `331d4c860689` | `22ffea6acb40` |
| tamaño | 97.860.899 B (93,3 MiB) | 27.852.217 B (26,6 MiB) | 18.999.719 B (18,1 MiB) |
| `creation_time` UTC | 2026-09-14T19:52:59 | 19:50:41 | 19:52:20 |
| hora local (`utc_offset` −0300) | 16:52:59 | 16:50:41 | 16:52:20 |
| duración del contenedor | 17,852 s | 4,9495 s | 3,204622 s |
| resolución + rotación | 3840×2160, rot −90 → **2160×3840** | ídem | ídem |
| codec / perfil / tag / pix | hevc Main, level 5.1, `hvc1`, yuv420p, bt709 | ídem | ídem |
| bitrate de video | 43,10 Mb/s | 43,01 Mb/s | 44,62 Mb/s |
| audio | aac LC 48 kHz estéreo 256 kb/s | ídem | ídem |
| `com.android.capture.fps` | 60.000000 | 60.000000 | 60.000000 |
| `com.android.version` | 16 | 16 | 16 |
| `com.samsung.android.utc_offset` | −0300 | −0300 | −0300 |
| `location` | −32,0431 −065,0295 | ídem | ídem |
| `major_brand` / `compatible` | mp42 / isommp42 | ídem | ídem |
| `udta` dentro de `moov` | 1.098.359 B | 1.078.071 B | 1.019.002 B |
| **cuadros decodificados** | **1066** | **292** | **189** |
| fps reproducción **bruto** | 59,713 | 58,992 | 58,972 |
| fps reproducción **efectivo** | **60,0256** | **60,0255** | **60,0255** |
| ratio VFR bruto | 6,579 | 6,098 | 4,360 |
| ratio VFR sin el 1er delta | 1,0007 | 1,0007 | 1,0007 |
| primer delta | 0,109567 s | 0,101567 s | 0,072622 s |
| veredicto `fps_truth` | `SIN_DURACION_REAL` | ídem | ídem |

**Lectura: los tres son el mismo teléfono, el mismo modo y la misma tanda de
dos minutos.** Galaxy S22 Ultra, **modo Video UHD (3840×2160) a 60 fps**, tal
como dice la captura de pantalla de la cámara. Tres cosas lo sostienen: la
resolución es 4K exacta (no hay modo de cámara lenta a 4K en la guía de este
teléfono); la reproducción efectiva es 60,03 fps en los tres, o sea que
reproducción y `com.android.capture.fps` **coinciden** — un Slow motion de
Samsung llega horneado y reproduciría a una fracción del nominal; y las tres
`creation_time` caen dentro de 2 min 18 s.

**No hubo recompresión: el `udta` de Samsung está intacto.** Los hijos del
`moov` son `mvhd, udta, meta, trak, trak`, en ese orden, idéntico al original
FHD del 7/9 (`20260907_170638.mp4`, cuyo `udta` medía 557.940 B). Acá miden
1,02–1,10 MB — más grande porque la miniatura embebida es de 4K. Sumado al
codec `hvc1`/HEVC a 43–47 Mb/s y a las etiquetas `com.android.*` /
`com.samsung.*` completas: **WhatsApp en modo documento no los tocó.** Un envío
como video habría dado H.264 de pocos Mb/s, sin `udta` y con la resolución
bajada — que es lo que advierte `docs/filmacion-s22.md`.

**El delta de arranque de este modo: 0,073–0,110 s** (4,4 a 6,6 cuadros a
60 fps), contra 0,2015 s (6,0 cuadros) medidos en FHD 30 en el informe del 03.
En cuadros es el mismo orden; en tiempo, la mitad. En los tres clips el primer
delta es el **único** fuera de lugar: el criterio "el primero y sólo el
primero" aguanta también en este modo. Cierra parcialmente la pregunta 3 del
informe del 03 — falta el mismo dato en Slow motion FHD 240.

### Qué hay adentro

Cuadros mirados a resolución nativa con `ffmpeg -vf select=…,crop=…,tile=…`.

- **vid2** (el primero que filmó, 16:50:41) — un swing **de práctica**
  completo, vista ~face-on, sobre el pasto. Address hasta el cuadro ~58, top
  ~115, el palo pasa por la zona de la pelota ~134, finish ~170; después baja el
  palo y camina hacia la cámara. **La pelota no se mueve en ningún cuadro**:
  verificada cuadro a cuadro del 128 al 139 con un recorte al pie. No hay
  contacto.
- **vid3** (16:52:20) — **arranca con el palo ya arriba.** En el cuadro 0 las
  manos ya están en lo alto del backswing: el archivo no tiene address ni
  backswing. La pelota tampoco se mueve (cuadros 24–35). Todo lo que sigue es
  acompañamiento y finish sostenido.
- **vid1** (16:52:59, el último y el más largo) — ~11 s de address y waggle, un
  swing con **contacto real**, y después camina hacia la cámara. **La pelota
  está en su lugar en el cuadro 741 y desapareció en el 742**, con estela de
  salida. Es el único de los tres que golpea.

**Cuerpo en el cuadro: 28,2–29,5 % del alto** en los tres (1083–1132 px de
cuerpo sobre 3840 px). `CAPTURA.md` pide 80–90 %. En el original FHD del 7/9 el
cuerpo medía 973 px = **41,9 %** de sus 2320 px de alto: **filmar en 4K sumó
13 % de píxeles de cuerpo y perdió 13 puntos de encuadre**, porque la cámara
quedó más lejos y el cuadro es más alto.

### El cronómetro: no hay

Ninguno de los tres es un cronómetro y Hernán confirmó que no se filmó. **No se
escribió ningún camino calibrado**, no se leyó ninguna hora y no hay
`fps_real`, `stretch_factor` ni uniformidad por tramos que reportar. El camino
nuevo entra como **declarado** (ADR-016), con la tasa de captura **asumida**
igual a la de reproducción y procedencia `sin_verificar`.

### El gate

```bash
.venv/bin/python -m kinelab.ingest data/incoming/vidN.mp4 --atleta hernan \
  --gesto driver --vista face_on --camino s22ultra-video-uhd60-whatsapp-doc --data <scratch>
```

**Los tres: `reject`, con una sola razón, `fps_min_for_gesture`.** Siete
chequeos pasan, uno queda sin evaluar, uno falla. Es lo correcto y es lo que
tiene que decir el gate para este teléfono en este modo.

| chequeo | vid1 | vid2 | vid3 |
|---|---|---|---|
| `capture_path_known` | ✓ `s22ultra-video-uhd60-whatsapp-doc` | ✓ | ✓ |
| `codec_matches_path` | ✓ hevc / hevc | ✓ | ✓ |
| `vfr_ratio_le_1_10` | ✓ **1,0007** (bruto 6,579) | ✓ 1,0007 (bruto 6,098) | ✓ 1,0007 (bruto 4,360) |
| `fps_matches_path` | — sin evaluar | — | — |
| **`fps_min_for_gesture`** | **✗ 60,0256 < 100** | **✗ 60,0255** | **✗ 60,0255** |
| `duration_plausible` | ✓ 17,759 s | ✓ 4,865 s | ✓ **3,149 s** |
| `rotation_normalized` | ✓ 90 | ✓ | ✓ |
| `view_declared` | ✓ face_on | ✓ | ✓ |
| `gesture_known` | ✓ driver | ✓ | ✓ |

`fps_matches_path` queda en `passed: null` con razón *"el camino no está
calibrado y no declara fps de reproducción; no hay contra qué comparar"*. Y
`capture_path_known` **pasa pero lo dice**: *"es un camino declarado sin
cronómetro: los tiempos asumen que el archivo reproduce a la velocidad de
captura"*. Declarar no ablandó ningún umbral.

**vid3 pasa `duration_plausible` por 0,149 s**: 3,149 s contra el mínimo de 3 s.

`capture.json` de vid1, recortado (los tres son iguales salvo cuadros y
duración; ninguno pasó el gate, así que van igual):

```json
"schema_version": "1.2.0",
"capture_path_id": "s22ultra-video-uhd60-whatsapp-doc",
"capture_path_calibrated": false,
"fps_provenance": "sin_verificar",
"fps_source": "declarado:s22ultra-video-uhd60-whatsapp-doc",
"fps_real": 60.0256, "fps_playback": 60.0256, "fps_playback_raw": 59.7129,
"stretch_factor": 1.0, "codec": "hevc", "width": 2160, "height": 3840,
"rotation_deg": 90, "frames_decoded": 1066,
"duration_s": 17.7591, "duration_playback_s": 17.8353,
"vfr_ratio": 1.0007, "vfr_ratio_raw": 6.5786, "first_delta_s": 0.109567,
"fps_note": "el primer delta es 0.1096 s (arranque de la cámara); sin él,
             ratio 1.00 y reproducción 60.026 fps (con él: ratio 6.58,
             59.713 fps). El resto de los deltas es uniforme: no es tasa variable.",
"gate": {"verdict": "reject", "reasons": ["A 60.0256 fps de captura no se pueden
   medir los tiempos del gesto (golf pide al menos 100). …"]}
```

### Exploración

```bash
.venv/bin/python -m kinelab datos data/incoming/vidN.mp4 --altura-m 1.75 \
  --camino s22ultra-video-uhd60-whatsapp-doc
```

Salidas en `data/incoming/vid1.kinelab/`, `…/vid2.kinelab/`,
`…/vid3.kinelab/` (ignorado por git). Última columna, el original FHD del 7/9
con `--camino s22ultra-video-fhd30-cable`, como referencia.

| | **vid1** | **vid2** | **vid3** | FHD 7/9 |
|---|---|---|---|---|
| cuadros · fps | 1066 · 60,026 | 292 · 60,026 | 189 · 60,025 | 265 · 29,998 |
| calidad | `confiable` | `confiable` | **`no_usar`** | `confiable` |
| detección | 1,0000 | 1,0000 | 1,0000 | 1,0000 |
| multi-sujeto | **0,0000** | 0,0000 | 0,0000 | **0,3132** |
| movimiento de cámara | 1,186 px | 0,975 px | 0,749 px | 0,266 px |
| cuerpo px (mediana) | 1104 | 1083 | 1132 | 973 |
| cuerpo / alto | 28,7 % | 28,2 % | 29,5 % | 41,9 % |
| plausibilidad rechazada | 11 / 1066 (1,0 %) | 5 / 292 (1,7 %) | **45 / 189 (23,8 %)** | 2 / 265 (0,8 %) |
| address · top · impacto · follow_end | **672 · 726 · 741 · 842** | 58 · 115 · 134 · — | — | 111 · 141 · 147 · 219 |
| en segundos | 11,195 · 12,095 · **12,345** · 14,027 | 0,966 · 1,916 · 2,232 | — | 3,7 · 4,7 · 4,9 · 7,3 |
| backswing / downswing | 899,6 / 249,9 ms | 949,6 / 316,5 ms | — | 1000,1 / 200,0 ms |
| tempo | 3,6 | 3,0 | — | 5,0 |
| sub-cuadro del impacto | **741→742, 0,2144, ±0,0991 cuadros** | 133→134, 0,9493, ±0,3557 | — | 147→148, 0,4181, ±0,1361 |
| repeticiones | 1 (1 descartada: `sin_top`) | 1 (0 descartadas) | **0** (`sin_address`, `sin_downswing`) | 1 (2 descartadas) |
| pico de manos | 4,46 bh/s · 780,9 cm/s | 4,27 · 747,3 | 3,75 · 656,0 | 4,81 · 841,6 |

**El sub-cuadro del impacto de vid1 está verificado contra la pelota.** El
motor pone el impacto en el cuadro 741 y el cruce en 741→742 a 0,2144; la
pelota está quieta en el 741 y ya salió en el 742. Es la primera vez que el
detector se compara contra un contacto real a 60 fps, y acierta.

En **vid2** el "impacto" (cuadro 134) es el punto bajo del palo, no un
contacto: la pelota nunca se movió. Su sub-cuadro (`fraction` 0,9493,
±0,3557 cuadros, 3,6× la incertidumbre de vid1) lo refleja.

**Métricas del registro, con el clip a 60,026 fps y vista `face_on`** (las 12
del registro; iguales en vid1 y vid2, ninguna en vid3, que no tiene
repeticiones). Ninguna con `judgment_allowed` verdadero: procedencia
`sin_verificar` (ADR-016).

| métrica | con valor | vid1 | vid2 | por qué `null` |
|---|---|---|---|---|
| `backswing_duration_ms` | no | — | — | `fps_real 60.026 por debajo de fps_min 120` |
| `downswing_duration_ms` | no | — | — | ídem |
| `follow_duration_ms` | no | — | — | ídem |
| **`tempo_ratio`** | **sí** | **3,6** (banda 3,312–3,929) | **3,0** (2,8–3,222) | `fps_min` 60 · MDC 0,065 |
| `pelvis_sway_top_cm` | sí | −1,7 | −6,5 | MDC 2,87 |
| `pelvis_sway_impact_cm` | sí | 14,3 | 19,0 | MDC 2,481 |
| `pelvis_lift_top_cm` | sí | −12,5 | −1,3 | MDC 2,822 |
| `thorax_sway_top_cm` | sí | −1,8 | −2,6 | MDC 3,462 |
| `thorax_lift_top_cm` | sí | −8,3 | 5,2 | MDC 2,889 |
| `head_sway_top_cm` | sí | −8,1 | −3,1 | MDC 3,824 |
| `head_lift_top_cm` | sí | −9,0 | −4,4 | MDC 4,501 |
| `pelvis_thrust_top_cm` | no | — | — | `vista face_on no válida (válidas: down_the_line)` |

**Los 60 fps compran exactamente una métrica respecto de los 30 del clip del
7/9: `tempo_ratio`** (su `fps_min` es 60; el del 7/9 la tiene en `null`). Las
tres duraciones siguen en `null` porque piden 120.

**Ningún clip tiene más de un swing**: `find_peaks` sobre `hands_speed_bh_s` da
un solo grupo de picos por clip (vid1: 744 y 796, que son impacto y
acompañamiento del mismo swing; vid2: 131; vid3: 29). Así que `analyze` sobre
el take ingestado daría exactamente el `analysis.json` que ya está en el
`.kinelab` — mismos valores, misma `fps_provenance sin_verificar`, mismo
`judgment_allowed: false` en las 12 — si el gate lo dejara pasar. No lo deja.

### Lo que cuesta UHD

Cinco corridas de `datos` medidas con `/usr/bin/time -p`, misma máquina, misma
sesión, `load average` 3,4–6,5 (la máquina no estaba ociosa; el informe del 04
reportó 11,5 s para el mismo clip FHD de 265 cuadros, acá dio 13,63 s).

| clip | resolución | cuadros | tiempo real | ms/cuadro |
|---|---|---|---|---|
| `cortado.mp4` | 2320×1080 | 76 | 7,80 s | 102,6 |
| `20260907_170638.mp4` | 2320×1080 | 265 | 13,63 s | 51,4 |
| **vid3** | 3840×2160 | 189 | 18,06 s | 95,6 |
| **vid2** | 3840×2160 | 292 | 25,48 s | 87,3 |
| **vid1** | 3840×2160 | 1066 | **76,38 s** | 71,7 |

Ajustando `t = fijo + marginal · cuadros` (los dos puntos FHD, los tres UHD):

- **FHD**: 5,46 s fijos + **30,8 ms/cuadro**
- **UHD**: 5,82 s fijos + **66,2 ms/cuadro** → **2,15× por cuadro**
- Por segundo de movimiento real: FHD30 **0,93 s/s** · UHD60 **3,97 s/s** →
  **4,29×**. vid1 son 17,76 s de video en 76,38 s: 4,30× tiempo real.

**Y los píxeles de más se tiran.** El recorte que entra a `rtmpose-m` se
reescala a **192×256** (`input_size` en el `pose.npz`). Alto de bbox medido:

| | bbox alto mediana | factor de reducción hasta 256 px |
|---|---|---|
| FHD 7/9 | 1340 px | **5,24×** |
| vid1 | 1468 px | 5,74× |
| vid2 | 1466 px | 5,73× |
| vid3 | 1550 px | 6,05× |

**En FHD el recorte ya entraba 5,2× sobredimensionado.** UHD lo lleva a 5,7–6,0×:
no agrega un solo píxel útil al modelo, sólo 2,15× de tiempo por cuadro y 3,4×
de disco (93,3 MiB por 17,8 s). Respuesta al punto 7 del prompt: **sí, el
recorte supera los 256 px de alto ya en FHD — UHD no agrega precisión, sólo
peso.**

### Suites

- Motor: **260 en verde**, ~28 s, con
  `--deselect tests/test_service.py::test_datos_lista_un_ejemplo_de_otro_proceso`.
- `tests/test_capture_paths.py` solo: **47 en verde** (es el que valida el YAML
  que toqué; `test_load_fixture` recorre todos los caminos del repo y
  `test_repo_has_the_declared_paths_of_adr_016` verifica que los declarados
  tengan los seis campos en `null` y `mode: video`).
- Arnés (`truth/`): **13 en verde**.

## Queda abierto

- **Un test rojo que no es mío y que se rompió solo al pasar la medianoche.**
  `tests/test_service.py::test_datos_lista_un_ejemplo_de_otro_proceso` escribe
  un `trabajo.json` con `"creado": "2026-09-14T12:00:00+00:00"` fijo y después
  afirma `assert [...] == ["ejemplo", "subida"], "el ejemplo es más nuevo"`. Hoy
  es 15/9, así que la subida recién creada es más nueva que la fecha quemada y
  el orden se da vuelta. **Es de la sesión del encargo 09 (`service/`), no lo
  toqué.** Falla igual con el YAML de HEAD, o sea que no lo causó mi cambio —
  verificado. Se reproduce con:
  ```bash
  .venv/bin/pytest -q tests/test_service.py::test_datos_lista_un_ejemplo_de_otro_proceso
  ```
  El arreglo es una línea: que la fecha del ejemplo sea relativa a `now`, no
  literal.
- **`hip_line_rate_deg_s` llega a 3662–3979 °/s** en los tres clips (la de
  hombros, 1247–3159). Es la misma geometría que `ESTADO.md` ya anotó en el
  encargo 07: la línea de caderas se acorta en proyección hasta casi cero al
  girar. Es columna descriptiva del CSV, pero alimenta `summary.gain`, que en
  vid1 da `pelvis_to_torso` 0,608 y `torso_to_arm` 0,461 — ganancias menores a 1
  y `sequence_order` `arm>pelvis>torso`. **No es una medición todavía.**
- **vid3 tiene 23,8 % de cuadros rechazados por `ELBOW_RANGE`** (45 de 189),
  contra 1,0–1,7 % en vid1 y vid2. El clip es casi todo acompañamiento y finish
  con los brazos cruzados detrás de la cabeza: es el caso donde el codo se
  ocluye. No se investigó más allá del conteo.
- **No se filmó el cronómetro**, así que sigue sin haber ningún camino calibrado
  en el repo y la pregunta 3 del informe del 03 (cuánto mide el primer delta en
  **cada** modo) queda contestada sólo para UHD 60 (0,073–0,110 s) y FHD 30
  (0,2015 s). Falta Slow motion FHD 240.
- El `--data` de la ingesta fue un directorio del scratchpad: **las tres tomas
  rechazadas no se commitearon** (y `data/sessions/` está ignorado igual).

## Para que pruebe Hernán

Nada de front. Tres comandos, si querés verlo con tus ojos:

```bash
.venv/bin/python -m kinelab.tools.fps_truth data/incoming/vid1.mp4
```
Tiene que decir `SIN_DURACION_REAL`, 1066 cuadros, y la línea
`sin el 1er delta (0.10957 s): reproducción 60.026 fps · ratio 1.001`.

```bash
.venv/bin/python -m kinelab.ingest data/incoming/vid1.mp4 --atleta hernan \
  --gesto driver --vista face_on --camino s22ultra-video-uhd60-whatsapp-doc --data /tmp/k11
```
Tiene que decir `RECHAZADO` con **una sola** razón: 60,0256 fps contra los 100
que pide golf.

```bash
open data/incoming/vid1.kinelab/evento-impact.png
```
Cuadro 741, `t=12.345s`, el rótulo amarillo con
`camino s22ultra-video-uhd60-whatsapp-doc | fps 60.026 | sin_verificar`. La
pelota todavía está en el pasto; en el 742 ya salió.

## Las tres líneas del cierre

1. **Qué son.** Tres swings del mismo golfista, el mismo teléfono, el mismo modo
   —Video UHD 3840×2160 a 60 fps, HEVC, sin recomprimir— y la misma tanda de dos
   minutos del 14/9 a las 16:50. **Ninguno es el cronómetro.** vid2 y vid3 son
   swings de práctica sin contacto; vid1 es el único que golpea la pelota.
2. **Cuál es el mejor: vid1**, por tres razones medidas: es el único con
   contacto real y el motor lo clava (impacto 741, sub-cuadro 741→742 a 0,2144;
   la pelota sale entre esos dos cuadros); es el único con los cuatro eventos
   (address, top, impacto, follow_end); y es el único con detección 1,0 y
   **cero** cuadros con más de una persona, sobre 1066 cuadros. vid2 sirve de
   segundo —swing completo con address, pero sin contacto y sin follow_end—; y
   **vid3 no sirve para nada anclado al address**, porque arranca con el palo ya
   arriba: 0 repeticiones, calidad `no_usar`.
3. **Qué le falta.** El **fps**: 60 contra los 100 que pide golf. Es el único
   chequeo que falla y no lo arregla ni el encuadre ni el cronómetro. Detrás
   viene el **encuadre**: 28–29 % del alto contra el 80–90 % de `CAPTURA.md`.
   Y 4K **no compra nada** —el recorte ya se achicaba 5,2× hasta 256 px en
   FHD—, cuesta 2,15× por cuadro y 3,4× de disco.

## Preguntas para el orquestador

1. **Con este teléfono, ¿el fps_min de golf es alcanzable?** Según
   `docs/filmacion-s22.md`, los dos modos en juego son Video FHD 60 y Slow
   motion FHD 240. **Ningún modo Video del S22 Ultra llega a 100 fps**, así que
   el gate va a rechazar todo lo que se filme en Video, se calibre o no. El
   único camino a ≥100 es Slow motion FHD 240, que llega horneado y que por
   ADR-016 **se rechaza sin cronómetro**. O sea: el cronómetro de Slow motion
   240 no es un trámite pendiente, es la única llave que existe para que este
   teléfono produzca un clip que pase el gate. ¿Se pide ya, o se baja el
   `fps_min` de golf con una decisión escrita?
2. **¿4K se desaconseja por escrito?** Está medido: no agrega precisión (el
   recorte ya entraba 5,2× sobredimensionado en FHD), cuesta 2,15× por cuadro y
   3,4× de disco. La consecuencia práctica es que conviene **FHD y acercar el
   trípode**, que además es lo que arregla el 28 % de encuadre. Si se acepta, va
   a `CAPTURA.md` §Presupuesto de datos y a `docs/filmacion-s22.md`, que hoy
   dice FHD 60 pero no explica por qué no 4K.
3. **WhatsApp en modo documento resultó ser un camino limpio**, contra lo que
   dice `docs/filmacion-s22.md` ("no mandes los videos por WhatsApp"). La
   advertencia sigue siendo correcta para el envío como video, pero la guía no
   distingue los dos modos y Hernán usó el bueno por su cuenta. ¿Se agrega la
   distinción a la guía?
4. **El umbral de `body_height_frac` sigue sin fijarse** (ESPECIFICACION 1.3) y
   ahora hay cuatro clips reales para medirlo: 28,2 / 28,7 / 29,5 % en UHD y
   41,9 % en el FHD del 7/9. Todos estarían por debajo de cualquier umbral
   derivado del 80–90 % de `CAPTURA.md`.
