# arnes-ganancia-subcuadro-encuadre — 15 de septiembre de 2026

Encargo: `docs/prompts/13-arnes-ganancia-subcuadro-encuadre.md` — el arnés
contesta tres cosas que sólo él puede contestar: si la ganancia vive o muere,
cuánto vale el MDC del instante sub-cuadro del impacto, y a qué altura de cuerpo
en píxeles el MDC de cada métrica cruza su tolerancia.

Hecho:

- **`truth/kinelab_truth/swing.py`**: la amplitud del arco de las manos deja de
  estar quemada (`arm_arc_top_deg` / `arm_arc_end_deg`, con los valores de
  siempre como default); `segment_rate_3d` (velocidad angular 3-D de una línea,
  `|dû/dt|` en °/s), `truth_gain` (picos 3-D y cocientes en la misma ventana que
  usa el motor) y `gain_params`, que arma un swing con cocientes 3-D **pedidos**
  y devuelve los **conseguidos**, que son los que se reportan como verdad.
- **`truth/kinelab_truth/harness.py`**: `Condition.noise_px` (ruido absoluto en
  px, además del relativo de ESPECIFICACION 3.1); `realize_seeds` (proyecta una
  vez por condición, sortea por semilla — el resultado por semilla es idéntico
  al de antes, verificado contra el `mdc.yaml` de HEAD); y los tres bloques
  nuevos: `gain_table`, `subframe_table` y `framing_table`.
- **`truth/kinelab_truth/__main__.py`**: inyecta lo del deporte (segmentos de la
  ganancia, estimador del sub-cuadro, parámetros de evento). El arnés no importa
  ningún deporte.
- **`sports/golf/mdc.yaml`** gana tres secciones — `gain`, `events` y `framing` —
  además de `metrics`, y **vuelve a tener las 14 filas**: ver Bug encontrado.
- **`sports/golf/metrics.py`**: `DEAD_METRICS` guarda también la unidad.
- 13 tests nuevos en `truth/tests/test_gain_subframe.py`.
- Commits: ver al pie.

## Probado

`cd truth && .venv/bin/pytest -q`: **29 en verde** (13 nuevos), 9,1 s.
`.venv/bin/pytest -q` del motor: **272 en verde**, 40,4 s.
El arnés corre entero — `python -m kinelab_truth --seeds 16` — en **59 s** y
regenera `sports/golf/mdc.yaml` y `truth/reports/mdc-2026-09-15.json`.

**Mutación manual** sobre el código nuevo: de seis mutaciones, **cinco hacen
fallar al menos un test** (grados→radianes, fps+1, nivel del cruce tomado en el
impacto y no en el address, σ relativo/absoluto invertidos, y el orden del
sorteo por semilla). La sexta —quitar el giro del eje de viaje— es un no-op
real: el cruce por cero de una señal negada cae en el mismo lugar.

### 1 · Ganancia: **muere en las dos vistas**

Verdad 3-D en la ventana address→follow_end, con tres bancos de cocientes
conocidos (el tórax sale exacto por amplitud; el brazo se resuelve iterando):

| banco | pelvis °/s | tórax °/s | brazo °/s | pelvis→tórax | tórax→brazo |
|---|---|---|---|---|---|
| 1,5 / 1,5 | 139,6 | 209,5 | 314,2 | **1,500** | **1,500** |
| 1,0 / 1,0 | 139,6 | 139,6 | 139,6 | **1,000** | **1,000** |
| 2,0 / 2,0 | 139,6 | 279,3 | 558,6 | **2,000** | **2,000** |

Lo que el motor calcula, condición nominal, 16 semillas (tolerancia 0,3, que es
el ancho de rango declarado, procedencia `estimacion`):

| vista | banco | picos en imagen (pelvis/tórax/brazo °/s) | pelvis→tórax | sesgo | tórax→brazo | sesgo |
|---|---|---|---|---|---|---|
| `face_on` | 1,5 | 86,3 / 120,1 / 593,0 | 1,429 | −0,071 | 5,058 | **+3,558** |
| `face_on` | 1,0 | 86,3 / 74,0 / 297,3 | 0,885 | −0,115 | 4,032 | **+3,032** |
| `face_on` | 2,0 | 86,3 / 572,3 / 987,8 | 6,796 | **+4,796** | 1,731 | −0,269 |
| `down_the_line` | 1,5 | **11110,2** / 1630,7 / 341,0 | 0,152 | **−1,348** | 0,214 | **−1,286** |
| `down_the_line` | 1,0 | **11110,2** / 1202,8 / 58,7 | 0,111 | **−0,889** | 0,050 | **−0,950** |
| `down_the_line` | 2,0 | **11110,2** / 1995,7 / 1517,4 | 0,185 | **−1,815** | 0,774 | **−1,226** |

**Por qué**, medido y con test: las tres líneas giran alrededor del eje
vertical, y en el plano de imagen eso es degenerado.

- Desde `down_the_line` la línea de caderas apunta a la cámara y su proyección
  **baja a 3,6 px de largo**; ahí el ángulo aparente se dispara a 11110 °/s
  contra 139,6 verdaderos: **80×**. El mismo número en los tres bancos.
- Desde `face_on` pasa lo contrario: la línea de caderas se mantiene horizontal
  en la imagen y casi no gira (86,3 contra 139,6). La de hombros sí gira, pero
  el pico medido va **74,0 → 120,1 → 572,3** para verdades 139,6 → 209,5 →
  279,3: un salto de 7,7× para un cambio verdadero de 2,0×, porque con 90° de
  giro la línea de hombros pasa por su propio colapso.

El número que hoy viaja en `summary.gain` **no es la ganancia de velocidad
angular**: es un artefacto del largo proyectado del segmento. No lo borré (el
prompt lo prohíbe). Los archivos que la tocan, para el encargo que la borre:

| archivo | qué |
|---|---|
| `kinelab/metrics/generic.py:54-81` | `line_angle_rate` y `gain` |
| `kinelab/analysis.py:161,169,179-190,215` | arma `gain_out` y `summary.gain` |
| `kinelab/sport.py:65` | campo `gain_segments` de `SportMetrics` |
| `sports/golf/metrics.py:24` · `sports/golf/config.py:9,30` | `GAIN_SEGMENTS` |
| `kinelab/contract/schema.json:67,72` | `summary.gain` es **requerido** |
| `kinelab/explore.py:185-186,375` | columnas `hip_line_rate_deg_s`, `shoulder_line_rate_deg_s`, `arm_left_rate_deg_s` del CSV y sus picos |
| `web/src/lib/etiquetas.ts:64-65` · `web/src/components/TablaEventos.tsx:36,45-46` | las muestra al entrenador como «rotación aparente de caderas» |
| `tests/test_fase2.py:388` · `data/examples/analysis.example.json:210` | esperan la clave |

**Atención al borrarla:** `gain()` es también quien calcula `sequence_order`, y
ése sí está en el contrato (`events[].sequence_order`, requerido por el schema).
Borrar la ganancia se lo lleva puesto si no se separa antes.

### 2 · Instante sub-cuadro del impacto: **vive**, con MDC medido

Verdad: el mismo cruce geométrico calculado a **2400 fps** (tiempo continuo),
`t* = 2,359769 s` en `face_on`. Ancla: el `address` verdadero y el `impact` que
da `peak_window`, la regla del propio detector. 16 semillas por fila.

| fps | ruido | sesgo ms | SD ms | LoA ms | **MDC ms** | MDC cuadros | nulls |
|---|---|---|---|---|---|---|---|
| 240 | 0 | +0,008 | 0,000 | — | 0,000 | 0,0000 | 0 |
| 240 | 0,003 | −0,007 | 0,535 | [−1,06 · +1,04] | 1,482 | 0,3558 | 0 |
| 240 | 0,006 | −0,032 | 1,021 | [−2,03 · +1,97] | **2,829** | 0,6791 | 0 |
| 240 | 0,012 | −0,210 | 1,814 | [−3,77 · +3,34] | 5,027 | 1,2065 | **2** |
| 120 | 0 | +0,008 | 0,000 | — | 0,000 | 0,0000 | 0 |
| 120 | 0,003 | −0,098 | 0,532 | [−1,14 · +0,95] | 1,475 | 0,1770 | 0 |
| 120 | 0,006 | −0,217 | 1,056 | [−2,29 · +1,85] | **2,927** | 0,3512 | 0 |
| 120 | 0,012 | −0,422 | 2,049 | [−4,44 · +3,59] | 5,678 | 0,6814 | 0 |
| 60 | 0,006 | −0,006 | 1,049 | [−2,06 · +2,05] | **2,909** | 0,1745 | 0 |
| 30 | 0 | −0,099 | 0,000 | — | 0,000 | 0,0000 | 0 |
| 30 | 0,006 | −0,251 | 0,712 | [−1,65 · +1,15] | **1,974** | 0,0592 | 0 |
| 30 | 0,012 | −0,384 | 1,454 | [−3,23 · +2,47] | 4,029 | 0,1209 | 0 |
| `down_the_line` 240 | 0,006 | — | — | — | — | — | **16 · null por vista** |

- **El sesgo va de −0,42 a +0,01 ms** (≤ 0,05 cuadros) en todas las
  condiciones. Sin ruido, ≤ 0,10 ms: el residuo es la interpolación lineal
  entre dos cuadros, nada más.
- **El MDC casi no depende del fps** (2,0–2,9 ms al ruido nominal) y eso es
  esperable: el error en tiempo es σ_px / velocidad, y la velocidad en px/s no
  cambia con la tasa de cuadros. En cuadros sí: 0,059 a 30 fps, 0,679 a 240.
- **Contra ±1 cuadro entero**: a 30 fps son 33,3 ms contra 2,0 → **17×**; a
  120 fps, 8,3 contra 2,9 → **2,8×**. El sub-cuadro compra tiempo real.
- **Invariante al tamaño**: 811, 406, 203 y 89 px dan el mismo número, exacto.
- **`down_the_line` sale `null` por vista, 16 de 16** (invariante 6).
- **La banda declarada por el motor nunca es optimista**: `uncertainty_frames`
  contra la SD medida da **1,18× a 9,23×** según fps y ruido (la más ajustada,
  1,18× a 60 fps; la más conservadora, 9,23× a 30 fps con poco ruido).

Escrito en `mdc.yaml` §`events.impact.subframe`. **No llega a `analysis.json`**:
el registro es de métricas, no tiene lugar para eventos, y quien tendría que
leer la tabla es `sports/golf/events.py`, que este encargo tenía prohibido tocar
(lo toca el 15). Es un cambio de pocas líneas para el encargo siguiente.

### 3 · Umbral de encuadre: el modelo de ruido de la spec no puede fijarlo

**Con el ruido que pide ESPECIFICACION 3.1** (σ proporcional a la altura del
cuerpo en px), **el MDC es exactamente invariante al tamaño del sujeto**: 100,
200, 400 y 800 px dan valores idénticos hasta el último decimal, en las doce
métricas. No es una casualidad de las semillas, es álgebra: si σ = f · altura,
el error en cm es (σ/altura) · estatura · 100 = f · estatura · 100, y la altura
se cancela. **Ninguna métrica cruza su tolerancia, así que de este barrido no
sale ningún umbral.** Hay un test que lo fija.

Por eso agregué el modelo **absoluto** (σ fijo en px), que es el único que puede
dar un número. Dos σ:

| métrica | tol | cruce con σ = 4,866 px | cruce con σ = 2,3 px |
|---|---|---|---|
| `pelvis_sway_impact_cm` | 5 cm | 394 px | 188 px |
| `pelvis_thrust_top_cm` | 5 cm | 413 px | 195 px |
| `pelvis_lift_top_cm` | 5 cm | 450 px | 215 px |
| `pelvis_sway_top_cm` | 5 cm | 462 px | 221 px |
| `thorax_lift_top_cm` | 5 cm | 465 px | 224 px |
| `thorax_sway_top_cm` | 5 cm | 552 px | 270 px |
| `head_sway_top_cm` | 5 cm | 608 px | 291 px |
| `head_lift_top_cm` | 5 cm | **717 px** | **345 px** |
| las cuatro duraciones y `tempo_ratio` | 30 ms / 0,3 | nunca | nunca |
| `impact_subframe` | 30 ms | nunca | nunca |

- **σ = 4,866 px** es el mismo ruido absoluto que el nominal relativo en el
  tamaño nominal (0,6 % de 811 px). Propuesta: **`body_height_px_min` = 717 px**.
- **σ = 2,3 px** es la mediana de lo **medido** en los clips reales
  (`subframe.components.noise_px`: 1,204 en `cortado.mp4`, 2,274 en vid1, 2,969
  en vid2). Propuesta: **345 px**.
- La métrica que manda es `head_lift_top_cm` en los dos casos: la cabeza es el
  punto más ruidoso y su desplazamiento verdadero es el más chico (3 cm).
- Las duraciones **no dependen del tamaño**: su MDC es cuantización de cuadros.

**Los cuatro clips reales pasan los dos umbrales con margen**: 973 px (FHD 30
del 7/9), 1083 (vid2), 1104 (vid1), 1132 (vid3).

**Y eso desarma la lectura por fracción de cuadro**: esos mismos clips ocupan
28,2–29,5 % del alto (UHD) y 41,9 % (FHD), muy lejos del 80–90 % que pide
`CAPTURA.md` — y aun así el encuadre no es lo que los limita. En 4K, 28 % del
cuadro son 1104 px, **más** que el 80 % de un 1080p (864 px). Lo que decide es
`body_height_px`, no la fracción; el gate hoy tiene `body_height_frac_min`.

**No fijé nada en el gate** (el prompt lo prohíbe): `sports/golf/config.py` sigue
con `body_height_frac_min = None` y el bloque `framing` de `mdc.yaml` lleva
escrito que es una propuesta y que nadie lo lee.

**Qué no cubre esto:** es nivel 0 — proyección y ruido gaussiano, sin estimador.
Cómo depende de verdad el error de RTMPose del tamaño del sujeto no está medido
acá; el script que lo mide sobre un cuadro real es `banco/scale_sweep.py` y
necesita los ONNX, que no se corrieron en esta sesión.

## Bug encontrado y arreglado (no estaba en el prompt)

`write_outputs` escribía `mdc.yaml` iterando el **registro**, y una métrica que
el arnés ya mató no está en el registro: al regenerar la tabla desaparecían las
dos filas de rodilla. Y una fila ausente **revive la métrica**, porque
`sports/golf/metrics.py::_m` sólo la mata si la fila existe y tiene `views: []`
— sin fila, la registra con sus vistas declaradas y `mdc: None`. La tabla
oscilaba entre dos estados en corridas alternas. Ahora `DEAD_METRICS` lleva
unidad y razón, `__main__` se las pasa al arnés y las filas sobreviven.

## Queda abierto

- **La ganancia no está borrada.** El prompt lo pedía así; la lista de archivos
  está arriba.
- **El MDC del sub-cuadro no llega a `analysis.json`.** Falta que
  `sports/golf/events.py` lea `mdc.yaml`.
- **La tabla se regeneró con los encargos 12, 14 y 15 ya adentro**, que
  commitearon mientras esta sesión corría. El 14 cambia la escala en cm
  (`kinelab/metrics/core.py`) y eso **mueve los ocho MDC en cm entre 1 y 9 %**:
  `pelvis_sway_top_cm` 2,870 → **2,841**, `pelvis_sway_impact_cm` 2,481 →
  **2,416**, `pelvis_lift_top_cm` 2,822 → **2,769**, `thorax_sway_top_cm` 3,462
  → **3,388**, `thorax_lift_top_cm` 2,889 → **2,819**, `pelvis_thrust_top_cm`
  2,867 → **2,610**, `head_sway_top_cm` 3,824 → **3,779**, `head_lift_top_cm`
  4,501 → **4,382**. Las cuatro duraciones, el veredicto de la ganancia y el del
  sub-cuadro no se movieron. Antes de mezclar los dos árboles la tabla se generó
  contra el HEAD viejo y reproducía sus doce filas exactas, así que la diferencia
  es toda del cambio de escala y de nada más.
- **El barrido de tamaño no toca el estimador.** Si alguien corre
  `banco/scale_sweep.py` con los ONNX, ahí está el σ(tamaño) real.

## Para que pruebe Hernán

No hay front en este encargo. Si querés ver los números vos mismo:

```bash
cd truth && .venv/bin/python -m kinelab_truth --seeds 16
```

Tarda ~60 s y te imprime, al final, los tres veredictos: la ganancia muerta en
las dos vistas, el sub-cuadro con su MDC en ms, y las dos propuestas de
`body_height_px_min`. Reescribe `sports/golf/mdc.yaml` y
`truth/reports/mdc-<fecha>.json` con lo mismo que está commiteado.

## Preguntas para el orquestador

1. **La ganancia muere. ¿Quién la borra, y qué pasa con `sequence_order`?** El
   schema exige `summary.gain` y `events[].sequence_order`, y los dos salen de
   la misma función. Sacarlos es un bump de `schema_version`.
2. **¿Se van también las columnas `hip_line_rate_deg_s` y
   `shoulder_line_rate_deg_s` del CSV y del front?** Hoy el front las rotula
   «rotación aparente de caderas», y acá quedó medido que el pico es un
   artefacto del colapso de la línea (11110 °/s contra 139,6). Es lo que ya
   venía marcando `ESTADO.md` con los 3244–3979 °/s del mocap y de los clips.
3. **El umbral de encuadre: ¿727 px (σ conservador) o 350 px (σ medido en los
   clips)?** Y, sobre todo: **¿el gate pasa a `body_height_px_min` en vez de
   `body_height_frac_min`?** Lo que el arnés mide son píxeles, y en 4K la
   fracción engaña en el sentido cómodo.
4. **¿Se agrega al contrato un lugar para el MDC de un campo de evento?** Hoy
   el registro es sólo de métricas, y el sub-cuadro es un campo del evento con
   `provenance: estimacion`. Con el MDC medido podría pasar a `medido_aqui` —
   sigue sin poder ser juicio mientras el camino esté sin calibrar.
5. **Cada cambio de la escala en cm invalida la tabla.** El 14 movió los ocho
   MDC en cm 1–9 % sin que nada avisara: `mdc.yaml` es salida del arnés y no hay
   nada que lo marque como viejo. ¿Se guarda en la tabla el `code_sha` de
   `kinelab/metrics/` y el motor avisa cuando no coincide?

Commits: `4342073` (arnés, tabla y tests) y el de cierre con `ESTADO.md` y este informe.
