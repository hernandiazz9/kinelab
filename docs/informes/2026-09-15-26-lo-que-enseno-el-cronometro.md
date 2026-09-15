# lo-que-enseno-el-cronometro — 2026-09-15

**Encargo:** escribir en `docs/filmacion-s22.md` y `CAPTURA.md` las nueve
lecciones de filmación que midió el 24, medir el segundo clip lento
(`cartado2-lenta.mp4`) con el mismo método para verificar por primera vez de
forma independiente los 240,15 fps, y escribir el test que fija el camino
calibrado. Sin tocar `kinelab/`, `sports/`, `service/`, `web/` ni `truth/`, sin
mover umbrales del gate y sin escribir caminos nuevos.

## Hecho

- **Los tres documentos escritos.** `docs/filmacion-s22.md` reescrita entera;
  `CAPTURA.md` en cuatro secciones; `docs/checklist-captura.md` sincronizado en
  cinco casillas. Cinco líneas de qué dice ahora la guía, al pie.
- **El test que faltaba**: `tests/test_capture_paths.py::test_repo_has_the_calibrated_slomo_path_of_the_s22`.
  48 en verde en ese archivo (eran 47), y **4 de 4 mutaciones del YAML lo ponen
  rojo**.
- **El punto 3 no se pudo hacer, y la razón es una lección de filmación:
  el cronómetro del segundo clip está detenido en 00:00.00 en los 292
  cuadros.** No hay verificación independiente de los 240,15 fps. Medido y
  documentado abajo; entró a la guía y al checklist como casilla propia.
- **Apareció un tercer clip lento que el prompt no podía conocer**
  (`~/Desktop/cortado3-lento.mp4`, creado una hora después de los otros dos).
  Se midió, y con él **el gate pasó entero por primera vez en el proyecto: 9 de
  9, `verdict: ok`** — y detrás, **los primeros `judgment_allowed: true`**. No
  se escribió ningún camino nuevo: usa el que ya existe.
- **No se tocó `data/capture-paths.yaml`.** El camino calibrado quedó tal como
  lo dejó el 24.

Commits: ver al cierre.

## Probado

### 1 · El segundo clip: el cronómetro está detenido

`cartado2-lenta.mp4` (copiado a `data/incoming/`, sha256 `60713477…`, idéntico
al del escritorio). Mismo modo, mismo recorte de la Mac, mismo `location`,
`creation_time` 16:29:39 — **cinco minutos después** del clip del 24.

| | valor |
|---|---|
| codec / rotación | hevc `hvc1`, 1920×1080 con rotación −90 → **1080×1920** |
| paquetes / cuadros presentados | **318 / 292** (un `elst` esconde 26) |
| `fps_playback` bruto = efectivo | **30,016952** |
| `vfr_ratio` | **1,0027063599** (CFR) |
| duración real a 240,15 fps | **1,216 s** |

**Y el cronómetro no sirve: lee `00:00.00` en los 292 cuadros.** Está reseteado
y parado. El método fue el del 24 al revés — en vez de leer mesetas, verificar
que no hay ninguna:

1. Los 292 cuadros extraídos con `-fps_mode passthrough` (292 archivos: ffmpeg
   y el motor coinciden).
2. **Seguimiento del cronómetro con plantilla** (`matchTemplate`) anclada en los
   dos dígitos de los minutos del cuadro 0, porque el teléfono se corre **38,6 px
   en x y 26,8 px en y** a lo largo del clip. Correlación del ancla contra el
   cuadro 0: **mínimo 0,986, mediana 0,991** sobre los 292.
3. La caja de las **centésimas** —los únicos dígitos que cambiarían— comparada
   contra el cuadro 0: correlación mínima **0,818**, mediana 0,898. Esa caída
   **no es un cambio de dígito**: es deriva sub-píxel más desenfoque. Los cinco
   cuadros peor correlacionados (196, 209, 213, 218, 219) se miraron a ojo
   ampliados y **los cinco leen `00:00.00`**.
4. Tira cada 20 cuadros (16 lecturas, del 0 al 291) leída a ojo: **las 16 dicen
   `00:00.00`**, centésimas incluidas.

Archivos para mirar, en `data/incoming/cronometro-26/`:
`crono2_cada20cuadros.png` (la tira de 16), `crono2_peores_cuadros.png` (los
cinco peores más tres de control), y `cuadro-0000.jpg` / `cuadro-0145.jpg` /
`cuadro-0291.jpg` enteros.

> **La primera verificación independiente de una tasa calibrada del proyecto no
> ocurrió.** Los 240,15 fps siguen siendo **n = 1**: la mejor medición que tiene
> el proyecto y, a la vez, la que menos veces se repitió. No hay ninguna
> evidencia en contra — simplemente no hay segunda medición.

### 2 · Lo que el segundo clip SÍ verifica: la reproducción

| | `Cortado-lenta` (24) | `cartado2-lenta` (26) | `cortado3-lento` (26) | camino |
|---|---|---|---|---|
| cuadros | 598 | 292 | 2977 | — |
| `fps_playback` | 30,016828 | **30,016952** | 30,016854 | **30,0169** |
| `vfr_ratio` | 1,0027063599 | **1,0027063599** | 1,0027063599 | — |
| deltas de PTS distintos | 10 | **los mismos 10** | los mismos 10 | — |

Los tres archivos comparten el patrón de deltas **hasta el décimo decimal**:
salen del mismo proceso de retiming, y `fps_matches_path` (tolerancia 2 %) pasa
con 0,00017 % de diferencia. Es una confirmación real, pero **de la tasa de
reproducción, que es la que el archivo sí puede decir**. La de captura —la que
el cronómetro mide y la única que habilita juicio— no queda verificada por esto.

### 3 · El tercer clip, y el primer `verdict: ok` del proyecto

`~/Desktop/cortado3-lento.mp4` no existía cuando se escribió el prompt
(`creation_time` 17:26:40, una hora después de los otros dos; 91,3 MB). Mismo
modo, mismo camino: handler `Core Media Video`, `udta` recortado, `elst` que
esconde 4 cuadros de 2981, audio a 12.000 Hz, mismo patrón de PTS. Otro lugar
(`location` −32,0436 −065,0268) y **sin cronómetro en el cuadro**.

**2977 cuadros / 240,15 fps = 12,3964 s reales.** Eso es lo que cambia todo:

```bash
.venv/bin/python -m kinelab.ingest data/incoming/cortado3-lento.mp4 \
  --atleta hernan --gesto driver --vista face_on \
  --camino s22ultra-slomo-fhd240-recorte-mac --data <scratch>
```

| chequeo | pasa | valor | esperado |
|---|---|---|---|
| `capture_path_known` | ✓ | `s22ultra-slomo-fhd240-recorte-mac` | calibrado |
| `codec_matches_path` | ✓ | hevc | hevc |
| `vfr_ratio_le_1_10` | ✓ | 1,0027 | ≤ 1,1 |
| `fps_matches_path` | ✓ | 30,017 | 30,0169 (tol. 2 %) |
| `fps_min_for_gesture` | ✓ | 240,15 | ≥ 100 |
| **`duration_plausible`** | **✓** | **12,396 s** | 3–180 s — *lo que rechazaba al anterior* |
| `rotation_normalized` | ✓ | 90 | |
| `view_declared` · `gesture_known` | ✓ | face_on · driver | |

**`verdict: ok`. 9 de 9. `fps_provenance: medido_aqui`.** Es el primer
`capture.json` del proyecto que pasa el gate entero, y **no se movió ningún
umbral**: el clip anterior duraba 2,49 s reales y éste 12,40. La lección 4 del
informe del 24 —filmar más largo— era la correcta, y costó diez segundos de
grabación.

### 4 · Percepción y análisis: los primeros `judgment_allowed: true`

```bash
.venv/bin/python -m kinelab.perception <take>          # 2977 cuadros
.venv/bin/python -m kinelab analyze <take> --altura-m 1.75
```

**Percepción:** detección **1,0000** (2977/2977) · cuerpo **690,9 px mediana =
36,0 % del alto** (636–832) · movimiento de cámara 1,35 px · `detection_rate` ok
· `single_subject` ok · `body_height_frac` sin evaluar (umbral sin fijar,
ESPECIFICACION 1.3).

**Análisis:** calidad **`confiable`**, **`warnings: []`** (el aviso falso que
anotó el 24 no aparece porque acá el camino está calibrado *y* el gate corrió),
**2 repeticiones**, 1 descartada por `sin_address`, y **`follow_end` detectado
por primera vez en un clip real**.

| métrica (rep 1) | valor | `fps_provenance` | `judgment_allowed` |
|---|---|---|---|
| `backswing_duration_ms` | 966,1 ms | `medido_aqui` | **true** |
| `downswing_duration_ms` | 333,1 ms | `medido_aqui` | **true** |
| `tempo_ratio` | 2,9 | `medido_aqui` | **true** |
| `follow_duration_ms` | 2560,9 ms | `medido_aqui` | **true** |
| `pelvis_sway_top_cm` | 3,7 cm | `medido_aqui` | **true** |
| `pelvis_sway_impact_cm` | 22,6 cm | `medido_aqui` | **true** |
| `pelvis_lift_top_cm` | −4,3 cm | `medido_aqui` | **true** |
| `thorax_sway_top_cm` · `thorax_lift_top_cm` | 3,5 · 5,0 cm | `medido_aqui` | **true** |
| `head_sway_top_cm` · `head_lift_top_cm` | 4,9 · −2,0 cm | `medido_aqui` | **true** |
| `pelvis_thrust_top_cm` | `null` | `medido_aqui` | false — *vista* |

**Once de doce.** El eslabón que el 24 dijo que faltaba —el gate— está cerrado,
y `judgment_allowed` pasó a `true` **solo**, sin tocar una línea del motor.

**Dos advertencias que van con estos números, y son importantes:**

1. **No son reproducibles desde HEAD.** `analyze` corrió contra un árbol con
   trabajo sin commitear de las sesiones 16 y 18: la primera corrida se cayó con
   `NameError: interpolate_gaps` en `kinelab/events/signal.py` (a medio editar),
   y la segunda, minutos más tarde, ya funcionó. **El gate de §3 sí es
   reproducible** — la ingesta no toca ninguno de esos archivos. Los valores y
   los cuadros de los eventos hay que rehacerlos cuando el 16 y el 18 cierren.
2. **Son los primeros números con juicio habilitado y nadie los revisó.**
   `pelvis_sway_impact_cm` 22,6 cm y `follow_duration_ms` con SD de 1292 ms
   entre dos repeticiones no se parecen a mediciones cerradas. Que el motor
   *permita* juzgarlos no dice que estén bien; dice que ya no hay un supuesto
   escondido en el eje del tiempo.

### 5 · El encuadre, sexto punto de la serie

| clip | modo | cuerpo | % del alto |
|---|---|---|---|
| `vid1` · `vid2` · `vid3` | Video UHD 60 | — | 28,2 / 28,7 / 29,5 % |
| `20260907_170638` | Video FHD 30 | — | 41,9 % |
| `Cortado-lenta` | Slow motion FHD 240 | 414 px | **21,6 %** — el peor |
| **`cortado3-lento`** | Slow motion FHD 240 | **691 px** | **36,0 %** |

**+14,4 puntos con la misma lente, el mismo modo y el mismo teléfono.** Es sólo
el trípode. Está en los tres documentos.

### 6 · El test

`tests/test_capture_paths.py::test_repo_has_the_calibrated_slomo_path_of_the_s22`,
hermano de `test_repo_has_the_declared_paths_of_adr_016`: existe, `calibrated`,
`mode: slomo`, `nominal_fps` 240, `codec_expected` hevc, `fps_real` 240,15,
`fps_playback` 30,0169, `stretch_factor` consistente con el cociente **a 4
decimales**, los seis campos del cronómetro no nulos, fecha y autor, la palabra
`cronómetro` en `fps_method`, y `fps_real ≥ 100`.

**Mutación manual sobre el YAML, 4 de 4 en rojo:** `fps_real` → 239,76;
`mode: slomo` → `video`; `stretch_factor` 8,0005 → 8,0 (la primera versión del
test, con `rel=0.001`, **dejaba pasar ésta**: se apretó a `abs=0.0001`);
`calibrated_by: hernan` → `nadie`. El YAML se restauró intacto después de cada
una (`diff` limpio).

### 7 · Suites

- **`tests/test_capture_paths.py`: 48 en verde** (eran 47). Es el archivo que
  toqué.
- **La suite entera del motor no está en verde, y no es por esto.** Tres
  corridas dieron 25, 3 y 3 rojos según el minuto, todos en `test_fase2.py`,
  `test_perception.py` y `test_service.py`, y todos por trabajo a medio escribir
  de las sesiones paralelas (`kinelab/events/signal.py`, `kinelab/analysis.py`,
  `kinelab/metrics/generic.py`, `sports/golf/events.py`, visibles en
  `git status`). El único archivo de código de esta sesión es
  `tests/test_capture_paths.py`.
- `truth/` no se tocó ni se corrió: ninguno de sus archivos es de este encargo.

### Qué dice ahora la guía, en cinco líneas

1. **Una sola regla arriba de todo**: *Slow motion* FHD 240, **cronómetro
   andando dentro del mismo cuadro que el swing**, y **25 segundos por toma**.
   El resto de la hoja son los porqués.
2. **Los 25 segundos tienen su cuenta escrita**: la cámara lenta estira ×8, así
   que los 3 s reales que exige el programa son 24 s de grabación — y es lo
   único que separó al clip del 15/9 del gate.
3. **El cronómetro dejó de ser un clip aparte**: va en todas las tomas, andando
   (con la falla del segundo clip escrita como casilla), a la distancia del
   golfista, plano, encarado, al brillo máximo y fuera de la línea de tiro.
4. **No recortar en la Mac**, con las tres cosas que costó el recorte (1 MB de
   `udta` → 185 B, las etiquetas del fabricante, 14 cuadros escondidos); el
   archivo entero de `DCIM/Camera` por cable.
5. **Acercar el trípode y vaciar el cuadro**: la serie de seis clips con el
   21,6 % y el 36,0 % al lado, y el carrito de golf que se detectó como persona
   en 8 de 598 cuadros.

## Queda abierto

- **PEDIDO A HERNÁN, el que reemplaza al del 24 como más importante: un clip de
  *Slow motion* FHD 240 con el cronómetro ANDANDO en el cuadro y 25 segundos de
  grabación.** Contesta las tres cosas de una vez: verifica los 240,15 fps por
  segunda vez (hoy n = 1), pasa el gate entero con calibración **propia** en vez
  de prestada, y —si sale de `DCIM/Camera` sin recortar— calibra el camino del
  teléfono en vez del recorte.
- **El ORIGINAL sin recortar sigue faltando** (pedido del 24). Los tres clips
  lentos son recortes de la Mac, con `elst` que esconden 14, 26 y 4 cuadros.
- **El delta de arranque de Slow motion FHD 240 sigue sin medirse**, por la
  misma razón.
- **Rehacer los números de §4 cuando el 16 y el 18 cierren.** Hoy dependen de
  código sin commitear.
- **`cortado3-lento.mp4` no se ingestó a `data/sessions/`**, sólo a un
  directorio de scratch. Sigue abierta la pregunta 3 del informe del 24 (dónde
  viven las tomas, rechazadas y aceptadas).
- **La pista de audio a 12.000 Hz** de los tres clips sigue sin explicar
  (anotado por el 24, confirmado acá en los tres).
- **No se tocó `sports/golf/`** ni ningún umbral. El `body_height_frac` sigue
  sin umbral fijado: ahora hay seis puntos de encuadre para cuando el arnés
  decida.

## Para que pruebe Hernán

Nada de front. Cuatro comandos.

```bash
.venv/bin/pytest -q tests/test_capture_paths.py
```

**48 en verde.** El que se agregó es
`test_repo_has_the_calibrated_slomo_path_of_the_s22`: si alguien le cambia el
`fps_real` al camino calibrado, ese test se pone rojo.

```bash
open data/incoming/cronometro-26/crono2_cada20cuadros.png
```

Dieciséis lecturas del cronómetro del segundo clip, del cuadro 0 al 291. **Las
dieciséis dicen `00:00.00`**: eso es lo que hay que ver, y es por lo que ese
clip no pudo medir nada.

```bash
.venv/bin/python -m kinelab.ingest data/incoming/cortado3-lento.mp4 --atleta hernan \
  --gesto driver --vista face_on --camino s22ultra-slomo-fhd240-recorte-mac --data /tmp/k26
```

Tiene que decir **`gate: OK`** — 2977 cuadros, 12,3964 s reales. **Es la primera
vez que el gate acepta un clip en todo el proyecto.** En
`/tmp/k26/sessions/hernan/2026-09-15/driver/face_on/take-01/capture.json`,
`verdict` dice `ok` y `reasons` está vacío.

Y lo otro es leer **`docs/filmacion-s22.md`** con ojos de quien va a filmar. Lo
que hay que mirar, en orden: (1) que las tres cosas del párrafo de arriba se
entiendan sin leer el resto; (2) que la sección 2 deje claro que el cronómetro
va **andando** y **en cada toma**, no una vez; (3) que «contá hasta 25» sea
ejecutable con un trípode y un palo en la mano; y (4) si el elogio al
`cortado3-lento` —que salió bien— está dicho de forma que no suene a que ya
está todo resuelto, porque a ese clip le faltó el cronómetro.

## Preguntas para el orquestador

1. **La pregunta 1 del informe del 24 se contesta sola, y a favor de (a).**
   `duration_plausible` no hay que tocarlo: el clip siguiente, filmado más
   largo, pasó 9 de 9 sin mover nada. Lo dejé escrito así en `CAPTURA.md` §El
   gate de ingesta. Si preferís reabrirlo, el lugar es un ADR, no el umbral.
2. **Los primeros `judgment_allowed: true` existen y nadie los revisó.**
   ¿Encargo para mirarlos uno por uno contra el video (22,6 cm de sway en el
   impacto, `follow_duration_ms` con SD de 1292 ms entre dos repeticiones), o se
   espera a que el 16 y el 18 cierren y se rehace todo de una?
3. **`cortado3-lento.mp4` pasó con calibración prestada.** El gate verifica la
   reproducción por clip, pero la captura la hereda del camino que declara el
   usuario. ¿Alcanza —y queda escrito como supuesto, que es lo que hice— o el
   gate debería distinguir «camino calibrado y verificado en este clip» de
   «camino calibrado y heredado»? Es un campo nuevo en `capture.json`, o sea
   contrato, o sea no era de esta sesión.
4. **El id del camino sigue envejeciendo mal** (pregunta 4 del 24): ahora hay
   tres clips distintos bajo `…-recorte-mac`, y el del teléfono crudo sigue sin
   existir. No lo toqué.
5. **`docs/checklist-captura.md` sigue siendo la hoja del iPhone** (pregunta 2
   del informe del 12, todavía sin contestar). Le sincronicé cinco casillas y le
   reforcé la cabecera que manda a la guía del S22, pero son dos documentos para
   el mismo trabajo con dos teléfonos distintos, y uno de los dos no existe.
