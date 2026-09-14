# fps-min-tolerancia — 2026-09-14

**Encargo:** que la comparación `fps_real >= fps_min` del registro lleve una
tolerancia del 0,5 % en un solo lugar, con constante nombrada y el porqué
escrito (tasas NTSC contra la tabla nominal entera del arnés), para que un clip
real de 30 fps deje de perder por dos milésimas las métricas de `fps_min: 30`.
Sin tocar el gate, `mdc.yaml`, `truth/`, `explore.py`, `service/` ni `web/`.

## Hecho

- **`kinelab/metrics/registry.py`**: `FPS_MIN_TOL = 0.005` y una función
  `fps_min_met(metric, fps_real)` que devuelve
  `fps_real >= fps_min · (1 − FPS_MIN_TOL)`. Es el **único** lugar donde se
  compara la tasa de la toma contra el mínimo de la métrica: la llaman
  `judgment_allowed`, `null_metric` y `metrics.core.evaluate`, que antes tenían
  cada uno su propio `>=`. El porqué está en el comentario de la constante, con
  los números (NTSC 239,76 · 119,88 · 59,94 · 29,97; S22 Ultra 29,998).
- **`kinelab/metrics/core.py`**: `evaluate` usa esa función. El `null_reason`
  no cambió una letra: sigue siendo `"fps_real 29.998 por debajo de fps_min
  120"`, con los dos números sin redondear.
- **`CONTRATO.md` §El sextuplo de toda métrica**: párrafo nuevo con la regla,
  el porqué en una frase y la aclaración de que `fps_min_for_gesture` —el
  chequeo del gate— es otra regla y no lleva tolerancia.
- **Lo que NO se tocó**, verificado con `git status` antes del commit: el gate
  (`kinelab/ingest/gate.py`), `CAPTURA.md`, `sports/golf/mdc.yaml`, `truth/`,
  `kinelab/explore.py`, `service/`, `web/`. El arnés sigue barriendo en fps
  enteros y escribiendo la tabla igual (y de paso no lo afecta: en
  `harness.py:84` evalúa con `fps_min=1.0`).

Commit: `e2204ee` (registro, `core.py`, `CONTRATO.md`, tests) y el de cierre
con `ESTADO.md` y este informe.

## Probado

Suites: **252 en verde** en el motor, 26 s (eran 240 al cerrar el 06: son
exactamente los 12 casos nuevos de este encargo). **4 en verde** en el arnés.

Tests nuevos (12), todos en `tests/test_fase2.py`:

| caso | esperado |
|---|---|
| 29,998 contra 30 (el S22 medido) | pasa |
| 29,97 · 59,94 · 119,88 · 239,76 contra 30 · 60 · 120 · 240 | pasan |
| 30,0 contra 30 y 120 contra 30 | pasan |
| **29,8 contra 30** (0,67 % abajo) | **no pasa** |
| 29,0 contra 30 · 60 contra 120 | no pasan |
| el borde exacto 29,85 y 29,85 − 1e−6 | pasa / no pasa |
| swing sintético a **29,97 fps** | las de `fps_min` 30 dan número; las de 60 y 120 en `null` con la razón exacta |

Cada caso se verifica dos veces: en `fps_min_met` y en `judgment_allowed`, y el
del borde también en el `fps_min_met` del sextuplo que devuelve `evaluate`.

**No son decorativos** (invariante 15). Con `FPS_MIN_TOL = 0.0` fallan 7 de los
12; con `FPS_MIN_TOL = 0.05` fallan los 3 que exigen que 29,8 y 29,0 **no**
pasen. La tolerancia está acotada por los dos lados.

### Corrida real 1 — original del S22 con `s22ultra-video-fhd30-cable`

```bash
.venv/bin/python -m kinelab datos ~/Desktop/20260907_170638.mp4 --altura-m 1.75 \
    --camino s22ultra-video-fhd30-cable
```

265 cuadros a **29,998 fps**, `fps_provenance: sin_verificar`. De las 12
métricas, **7 pasan de `null` a tener valor** (antes eran 12 en `null`):

| métrica | fps_min | valor | unidad |
|---|---|---|---|
| `pelvis_sway_top_cm` | 30 | −0,8 | cm |
| `pelvis_sway_impact_cm` | 30 | 7,7 | cm |
| `pelvis_lift_top_cm` | 30 | −2,6 | cm |
| `thorax_sway_top_cm` | 30 | 0,7 | cm |
| `thorax_lift_top_cm` | 30 | −3,0 | cm |
| `head_sway_top_cm` | 30 | 5,2 | cm |
| `head_lift_top_cm` | 30 | −5,7 | cm |

Las 5 que siguen en `null`, con su razón textual:

| métrica | fps_min | razón |
|---|---|---|
| `backswing_duration_ms` | 120 | `fps_real 29.998 por debajo de fps_min 120` |
| `downswing_duration_ms` | 120 | ídem |
| `follow_duration_ms` | 120 | ídem |
| `tempo_ratio` | 60 | `fps_real 29.998 por debajo de fps_min 60` |
| `pelvis_thrust_top_cm` | 30 | `vista face_on no válida para esta métrica (válidas: down_the_line)` — muere por vista, no por fps; su `fps_min_met` ya es `true` |

**`judgment_allowed` sigue en `false` en las 12**, incluidas las 7 que ahora
tienen número: el camino es declarado y `fps_provenance` es `sin_verificar`
(ADR-016). La tolerancia habilita **medición**, no **juicio**. Los 7 números
salen como descriptivos, cada uno con su `mdc` de la tabla del arnés al lado
(2,481 a 5,7 cm) y su `uncertainty` de ±1 cuadro propagado.

Eventos y tiempos **sin cambio** respecto de los encargos 04 y 06: address 3,7 s
· top 4,7 s · impacto 4,9 s · fin 7,3 s; `address_to_top_ms` 1000,1 ·
`top_to_impact_ms` 200,0. Ninguna medición se movió: lo único que cambió es
cuáles se muestran.

### Corrida real 2 — `cortado.mp4` con `desconocido-video`

```bash
.venv/bin/python -m kinelab datos ~/Desktop/cortado.mp4 --altura-m 1.75
```

76 cuadros a **29,999 fps**. Lo mismo: **7 de 12 con valor**, las mismas 7, y
las mismas 5 en `null` con las mismas razones. Ningún `judgment_allowed` en
`true`. Valores, con su banda de ±1 cuadro:

| métrica | valor | banda |
|---|---|---|
| `pelvis_sway_top_cm` | 0,8 | [−0,8 · 2,3] |
| `pelvis_sway_impact_cm` | 7,6 | [7,6 · 8,6] |
| `pelvis_lift_top_cm` | −4,2 | [−4,5 · −2,1] |
| `thorax_sway_top_cm` | 1,7 | [1,0 · 4,3] |
| `thorax_lift_top_cm` | −5,3 | [−6,2 · −4,1] |
| `head_sway_top_cm` | 4,7 | [4,4 · 5,6] |
| `head_lift_top_cm` | −5,1 | [−6,2 · −5,1] |

Eventos de siempre: address 0,233 s (cuadro 7), top 1,3 s (39), impacto 1,467 s
(44); `address_to_top_ms` 1066,7 · `top_to_impact_ms` 166,7.

## Queda abierto

- **Estos 7 números son los primeros que el motor muestra sobre video real, y
  no están validados contra nada.** Su MDC sale del nivel 0 del arnés
  (proyección + ruido, sin estimador) y su `fps_provenance` es `sin_verificar`.
  `pelvis_sway_impact_cm` da 7,7 cm con un MDC de 2,481: la señal está sobre el
  piso, pero el piso es sintético. Que se vean no los vuelve defendibles.
- **`follow_duration_ms` en `cortado.mp4` está doblemente en `null`**: por
  `fps_min` 120 y porque el clip de 3 s no tiene `follow_end`. El orden de
  chequeos de `evaluate` hace ganar al fps; si algún día se quiere ver la otra
  razón, hay que decidir cuál manda.
- **La tolerancia no acerca nada al gate.** `fps_min_for_gesture` sigue pidiendo
  100 fps para golf sin tolerancia, y 29,998 no se le acerca. Este encargo sólo
  cambia qué muestra el modo exploración de un clip que el gate rechaza.
- **El 0,5 % es una decisión, no una medición.** Cubre NTSC (0,1 %) con margen
  de 5× y deja afuera la tasa de abajo entera. Si algún día aparece un camino
  con un desvío mayor —un teléfono que declare 30 y entregue 29,7—, la
  tolerancia no lo salva y **está bien que no lo salve**: eso es un camino que
  necesita cronómetro.
- Nada del front se tocó ni se abrió (regla de trabajo). `fps_min_met` no lo
  consume hoy ni `service/` ni `web/`; el único `fps_min` que viaja por
  `GET /api/config` es el del deporte (el del gate), que no cambió.
- Sesiones en paralelo: al cerrar quedan sin commitear `kinelab/explore.py`,
  `kinelab/tools/interpolar.py`, `service/app.py`, `service/exploracion.py`,
  `tests/conftest.py`, `tests/test_service.py`, `truth/kinelab_truth/mocap.py`
  y `data/examples/cmu-mocap/` — son del 07 y del 09. No los toqué.
- **Aviso para la sesión del 07:** después de mi commit, el árbol de trabajo
  pasó a tener **1 test en rojo que no es mío**.
  `tests/conftest.py` (sin commitear) agregó un octavo camino
  (`desconocido-video`) al fixture `capture_paths_yaml`, y
  `tests/test_capture_paths.py::test_load_fixture` sigue afirmando
  `len(cp.paths) == 7` → `assert 8 == 7`. Se arregla cambiando ese 7 por 8 en
  el test, en el commit del 07. **Sobre HEAD limpio la suite da 252 en verde**,
  verificado con un `git archive HEAD` extraído aparte: mi trabajo no lo toca.

## Para que pruebe Hernán

No hay front nuevo. Dos comandos, los mismos de siempre:

```bash
.venv/bin/python -m kinelab datos ~/Desktop/20260907_170638.mp4 --altura-m 1.75 --camino s22ultra-video-fhd30-cable
```

```bash
.venv/bin/python -m kinelab datos ~/Desktop/cortado.mp4 --altura-m 1.75
```

Lo que cambia no se ve en la consola (que imprime eventos y duraciones, que no
se movieron): se ve en `<video>.kinelab/analysis.json`, en `reps[0].metrics`.
Antes las 12 métricas tenían `"value": null`; ahora 7 tienen número, y las
otras 5 dicen por qué no. Todas siguen con `"judgment_allowed": false`.

## Preguntas para el orquestador

Ninguna. La decisión estaba tomada en `docs/PLAN.md` (0,5 % en el registro, la
tabla del arnés en enteros, el umbral del gate sin tolerancia) y se implementó
tal cual.
