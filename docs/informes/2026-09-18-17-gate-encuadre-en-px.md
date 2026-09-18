# gate-encuadre-en-px — 18 de septiembre de 2026

Encargo: fijar el chequeo de encuadre en **píxeles de cuerpo** (`body_height_px
≥ 717` en golf, procedencia `estimacion`) en vez de fracción del cuadro, con su
frase para el entrenador, los documentos al día y una corrida real que tiene
que salir rechazada.

## Hecho

Commit del código y los documentos: **`6bae365`**. Commit de cierre (este
informe y `ESTADO.md`): al final.

- **`kinelab/sport.py`**: `PerceptionGates.body_height_frac_min` →
  `body_height_px_min: float | None = None`. La validación pasó de exigir el
  rango `(0, 1]` a exigir `> 0` (y un `NaN` también rebota). El docstring dice
  por qué el píxel y no la fracción, y avisa de la colisión de nombres con
  `FramingReport.body_height_px_min`, que es otra cosa: el mínimo observado del
  clip, no el umbral que pide el deporte.
- **`sports/golf/config.py`**: `perception=PerceptionGates(body_height_px_min=717)`,
  con el comentario reescrito — de dónde sale el 717, qué métrica lo fija,
  quiénes le siguen, que la procedencia es `estimacion` porque es arnés de nivel
  0 sin estimador de pose, y que se revisa con σ por keypoint medido en material
  real.
- **`kinelab/perception/framing.py`**: el chequeo pasa a llamarse
  `body_height_px` (también en `CHECK_IDS`). `value` es la mediana **redondeada
  a entero**, `expected` es el umbral. La fracción del cuadro va **dentro de
  `reason`**, también cuando pasa. Se borró `_finite_or_none`, que quedó sin
  uso. `kinelab/ingest/gate.py` no se tocó: `Check` sigue sin campos extra y el
  veredicto lo recalcula `with_checks` como siempre.
- **Las cuatro frases** (`{N}` es la mediana en px, `{M}` el porcentaje):
  - pasa → «*N px de cuerpo, M % del alto.*»
  - falla → «*El jugador mide N px de alto en el cuadro y hacen falta 717:
    acercá el trípode. Son el M % del alto del cuadro.*»
  - sin umbral → «*Sin evaluar: umbral sin medir (…). N px de cuerpo, M % del
    alto.*»
  - sin sujeto → «*No se pudo medir cuánto mide el jugador en el cuadro: no se
    lo detectó en ningún cuadro.*», con `passed: false`.
- **`CAPTURA.md`**: la fila `body_height_px` en la tabla del gate; el párrafo de
  §Encuadre reescrito con el número, su procedencia, quién lo fija y las dos
  cuentas del S22 (**717 px = 37,3 % de 1920** en *Slow motion* FHD 240;
  **30,9 % de 2320** en *Video* FHD); las fracciones de `vid1` y `vid2`
  desinvertidas y la columna «¿pasa los 717 px?» agregada a la serie.
- **`CAPTURA.md` §Lo que queda por verificar**: la afirmación «*un clip de este
  teléfono puede pasar el gate entero — puede*» quedó **falsa** con este cambio
  y se corrigió con fecha. Hoy `cortado3-lento` pasa la ingesta (9 de 9) y lo
  rechaza la Fase 1: **11 de 12**.
- **`docs/filmacion-s22.md`**: sección nueva **«7. La sesión de validación»**
  con los nueve puntos del prompt, cada uno con su porqué en castellano llano; el
  §2 reconciliado (el cronómetro va en la primera toma de cada vista y en la de
  la escena vacía, porque calibra el **camino**, no el video, y hoy ese camino
  está medido n = 1 y sobre un recorte de la Mac); una línea explícita de que
  quien filme después con el mismo teléfono, modo y cable **no necesita
  cronómetro**; el 37,3 % en §4; la excepción del WhatsApp-como-video en §6;
  y el repaso final renumerado a §8.
- **`tests/test_perception.py`**: tres tests nuevos y dos adaptados (detalle
  abajo).

**No se tocó** `kinelab/ingest/gate.py`, `sports/golf/mdc.yaml`,
`kinelab/perception/run.py`, `kinelab/explore.py`, `service/`, `web/`, `truth/`
ni `data/sessions/`. **El 717 no se movió.** `CONTRATO.md` **no cambió**: el id
del chequeo no aparece ahí (la lista de §capture.json son los nueve chequeos de
ingesta; los de la Fase 1 se suman después y el contrato no los enumera).

## Probado

### 1 · La corrida real: rechazo por 691 px contra 717

Sobre un `--data` de scratch, con `cortado3-lento.mp4` (2977 cuadros, 12,40 s
reales, camino `s22ultra-slomo-fhd240-recorte-mac`):

| paso | resultado |
|---|---|
| `python -m kinelab.ingest …` | **exit 0**, `gate: OK`, 9 de 9 |
| `python -m kinelab.perception …` | **exit 2**, `gate: RECHAZADO`, **11 de 12** |

El único chequeo que falla es el nuevo:

```
body_height_px  FALLA  El jugador mide 691 px de alto en el cuadro y hacen
                       falta 717: acercá el trípode. Son el 36 % del alto
                       del cuadro.
```

`value: 691` · `expected: 717` · `detection_rate` 1,0 ok · `single_subject`
0,0 ok. **Ese rechazo es el resultado**, y son 26 px: medio paso de trípode.

### 2 · La tabla de los otros clips, de los reportes que ya existen

Sin correr nada, leyendo `quality.body_height_px.median` de cada `analysis.json`
(los siete valores reprodujeron exacto los del prompt):

| clip | cuerpo px | % del alto | ¿pasa 717? |
|---|---|---|---|
| `vid3` | 1132 | 29,5 % | **sí** |
| `vid1` | 1104 | 28,7 % | **sí** |
| `vid2` | 1083 | 28,2 % | **sí** |
| `20260907_170638` | 973 | 41,9 % | **sí** |
| `cortado` (recorte del anterior) | 869 | 37,5 % | **sí** |
| `cortado3-lento` | **691** | 36,0 % | **no**, por 26 px |
| `Cortado-lenta` | 414 | 21,6 % | **no** |

**Pasarían cinco de siete**, y los cinco son de *Video* — los dos de *Slow
motion*, que es el único modo que llega a los 100 fps de golf, son justamente los
dos que no pasan. Hoy eso no cambia nada operativo: los cinco que pasan el
encuadre se rechazan igual por `fps_min_for_gesture` (30 y 60 fps contra 100), y
el que llega al fps es el que no pasa el encuadre. **Ningún clip del repo pasa
el gate completo, y desde hoy tampoco `cortado3-lento`.**

**Y confirma que la fracción engañaba**: `vid3` pasa con 29,5 % del alto y
`cortado3-lento` no pasa con 36,0 %. Ordenar los siete por fracción da un orden
distinto que ordenarlos por píxeles en **9 de los 21 pares** — los tres de UHD
contra los tres de FHD, en todas las combinaciones.

**Una corrección a la serie de `CAPTURA.md`**: las fracciones de `vid1` y `vid2`
estaban invertidas. Lo medido (informe 11:188, y reproducido acá desde los
`analysis.json`) es **vid1 28,7 % (1104 px)** y **vid2 28,2 % (1083 px)**.
Corregido.

### 3 · El modo exploración, como el prompt anticipó

`python -m kinelab datos data/incoming/Cortado-lenta.mp4 --altura-m 1.75`:
**no bloquea**, corre entero y suma la frase a los avisos —

```
el gate diría: El jugador mide 413 px de alto en el cuadro y hacen falta 717:
               acercá el trípode. Son el 22 % del alto del cuadro.
```

**Nota que no estaba en el prompt: el valor del chequeo depende del `fps_real`
declarado.** Ahí dice 413 px y el `analysis.json` guardado de ese mismo clip
dice 414. No es ruido: `body_height_px()` suaviza con una mediana móvil de **1
segundo**, o sea `window = 1,0 × fps`. Con el camino calibrado (240,15 fps) la
ventana son 240 cuadros y da **414,1 px**; con `desconocido-video` (30,017 fps)
son 30 cuadros y da **412,8 px**. Son 1,2 px sobre 717 y acá no cambia ningún
veredicto, pero **un clip a 2 px del umbral puede pasar o no según con qué
camino se lo declare**. Queda anotado; no lo toqué.

### 4 · Suites

- **Motor: 360 pasados, 0 fallados, exit 0** (eran 357; +3 tests). 52,9 s.
- **Arnés: 43 pasados, 0 fallados**, y **exit 134** — el aborto intermitente al
  cerrar el intérprete que ya anotó el 27 y que es el encargo 30. No se tocó
  `truth/`; el arnés importa `framing_report` y `body_height_px`, que no
  cambiaron.
- Tests nuevos: `test_body_height_px_check_measures_pixels_not_fraction`
  (600 px rechaza con la frase, 900 px pasa, 1104 px en 4K pasa con 28,75 % del
  alto, un tramo corto no tira abajo la mediana, sin sujeto falla legible, y el
  id es el mismo en las cuatro ramas), `test_body_height_px_min_has_to_be_positive`
  y `test_run_perception_rejects_a_take_with_the_subject_too_small` (la corrida
  completa con el estimador falso: el gate queda en `reject` y `pose.npz` se
  escribe igual).
- Adaptados: `test_framing_report_and_checks` (el renombre) y
  `test_run_perception_ok_and_timestamps`, que como avisaba el prompt se ponía en
  rojo (el estimador falso pone una persona de ~78 px) — **se arregló en el test,
  no en el umbral**: corre con `dataclasses.replace(GOLF, perception=PerceptionGates())`
  y de paso afirma que sin umbral el chequeo sale `passed: None`.

### 5 · Mutación manual: 9 de 9 en rojo

| # | mutación | resultado |
|---|---|---|
| 1 | golf vuelve a `PerceptionGates()` sin umbral | rojo |
| 2 | la comparación al revés (`<=` por `>=`) | rojo |
| 3 | el chequeo vuelve a mirar la fracción del cuadro | rojo |
| 4 | la fracción desaparece de la razón cuando pasa | rojo |
| 5 | la frase al fallar pierde «acercá el trípode» | rojo |
| 6 | sin la validación de `> 0` (un umbral de 0 pasa a ser legal) | rojo |
| 7 | el valor sale del **mínimo** del clip y no de la mediana | rojo |
| 8 | sin sujeto pasa a `passed: None` en vez de `False` | rojo |
| 9 | el id vuelve a `body_height_frac` en la rama que pasa | rojo |

**Las mutaciones 7 y 9 pasaron en verde en la primera vuelta**, y las dos
señalaban huecos reales de los tests, no del código:

- La **7** porque mi clip sintético tenía altura constante y ahí mediana, mínimo
  y máximo son el mismo número. Se agregó un clip de 300 cuadros con un tramo
  sostenido de 60 a 600 px: mediana 900, mínimo 600, y el chequeo tiene que
  **pasar**. Importa: si decidiera el peor cuadro, una pérdida de tobillo de dos
  segundos tiraría abajo una toma buena.
- La **9** porque sólo verificaba el id en las ramas «sin umbral» y «falla». Se
  agregó la aserción de que las cuatro ramas llevan el mismo id.

Después de las dos, las nueve mutaciones ponen la suite en rojo y los archivos
quedaron restaurados byte a byte.

### 6 · El nombre viejo

`rg body_height_frac` en `kinelab/`, `sports/`, `tests/`, `truth/`, `service/`,
`web/src/` y los seis documentos base: **cero resultados**. Lo que queda es
histórico y no se edita — los informes del 11, 13, 24 y 26, la auditoría del 16,
los prompts 13 y 17, y las dos secciones fechadas de `ESTADO.md` (1485 y 3199),
que registran lo que era cierto ese día. Un `capture.json` de
`web/public/demo/` todavía lleva el id viejo: es un dato publicado, se rehace
cuando se regenere la demo.

## Queda abierto

1. **Una toma rechazada por encuadre no se puede volver a correr.**
   `run.py:74` se niega a correr pose sobre una toma cuyo gate dice `reject`, y
   la Fase 1 escribe su propio rechazo **en ese mismo `capture.json`**. O sea:
   `python -m kinelab.perception TAKE --overwrite` sobre `cortado3-lento` ahora
   sale con `exit 1` y «*el gate rechazó esta toma*», citando la razón que la
   corrida anterior escribió. Antes no pasaba porque el chequeo salía
   `passed: null` y nunca rechazaba. Medido acá. No lo toqué: `run.py` no es
   archivo de este encargo, y la decisión de si un rechazo de Fase 1 debe ser
   re-corrible es del orquestador.
2. **El valor del chequeo depende del `fps_real` del camino declarado** (§3
   arriba): 414,1 px a 240,15 fps contra 412,8 px a 30,017, por la ventana de
   1 segundo del suavizado. 1,2 px. No lo toqué.
3. **`ARRANQUE.md:64`** dice que «el umbral exacto de `body_height_frac` está sin
   fijar a propósito». Es el único documento vivo que quedó con el nombre viejo y
   con una afirmación que hoy es falsa, y **no es archivo de este encargo**. Lo
   que pondría: «*el umbral de encuadre se fijó midiendo (717 px de cuerpo,
   `body_height_px_min`), el nombre del proyecto es provisorio, y los bitrates de
   `CAPTURA.md` vienen de un sitio comercial*».
4. **El 717 sigue siendo `estimacion`** y de nivel 0. Se revisa con σ por
   keypoint medido en material real, que es lo que la sesión de validación
   (`docs/filmacion-s22.md` §7) va a hacer posible. Mientras tanto ninguna
   métrica es juicio igual, por ADR-019.
5. **El umbral vuelve inalcanzable el material existente en el único modo que
   sirve.** Los dos clips de *Slow motion* FHD 240 —el único modo del S22 que
   llega a los 100 fps— están a 691 y 414 px. Hasta que se filme más cerca, el
   pipeline completo no tiene ni un clip que pase. Es lo que el umbral tiene que
   hacer, y es el motivo de que la sesión de validación pida un paso más de
   trípode.

## Para que pruebe Hernán

No hay front en este encargo (no se levantó `next dev` ni se abrió el navegador).
Lo que se puede correr a mano, desde la raíz del repo:

```bash
S=$(mktemp -d) && cp data/capture-paths.yaml $S/ && .venv/bin/python -m kinelab.ingest data/incoming/cortado3-lento.mp4 --atleta hernan --gesto driver --vista face_on --camino s22ultra-slomo-fhd240-recorte-mac --data $S && .venv/bin/python -m kinelab.perception $S/sessions/hernan/2026-09-15/driver/face_on/take-01
```

Qué tenés que ver: la ingesta dice `gate: OK`; la percepción tarda ~50 s, imprime
`cuerpo 691 px (36% del alto)` y termina en `gate: RECHAZADO` con la línea
`body_height_px FALLA · El jugador mide 691 px de alto en el cuadro y hacen falta
717: acercá el trípode`. **Ese rechazo es lo correcto.**

```bash
.venv/bin/pytest -q
```

Qué tenés que ver: `360 passed`, exit 0.

**Y lo importante que no es un comando: `docs/filmacion-s22.md` cambió.** Leé
la **§7, «La sesión de validación»** entera antes de filmar de nuevo, y fijate
en tres cosas que son nuevas: el cronómetro ya **no va en todas las tomas**
(sólo en la primera de cada vista y en la de la escena vacía), hay que grabar
**25 s de escena vacía** por vista con un **objeto fijo en el suelo**, y el
trípode tiene que quedar **más cerca que la última vez**: el cuerpo por encima
del **37,3 % del alto**, contra el 36,0 % que dio `cortado3`.

## Preguntas para el orquestador

1. **¿Un rechazo de Fase 1 tiene que poder re-correrse?** Hoy no (punto 1 de
   «Queda abierto»): la percepción escribe su rechazo en `capture.json` y la
   próxima corrida se niega a arrancar por ese mismo rechazo. Las salidas son
   tres: que `run.py` ignore los chequeos de Fase 1 al decidir si arranca (son
   suyos), que `--overwrite` fuerce también el gate, o dejarlo así y que
   re-ingestar sea el camino. No es decisión de esta sesión.
2. **¿La mediana o el peor cuadro?** Lo dejé en la mediana, que es lo que pedía
   el prompt y lo que informa `quality.body_height_px.median`, y le puse un test
   (mutación 7). Pero un clip con la mitad de los cuadros a 600 px pasa con
   mediana 900, y esos 600 px son cuadros donde las métricas valen menos. Si en
   algún momento hay que mirar los dos, el reporte ya trae `min` y `max`.
3. **¿`ARRANQUE.md` lo arregla alguien?** Ver punto 3 de «Queda abierto»: tengo
   el texto de reemplazo escrito, no es mi archivo.
