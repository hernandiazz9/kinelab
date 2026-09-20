# una-sola-escala-en-la-pantalla — 2026-09-20

Resumen: La misma pantalla mostraba **dos números en cm para el mismo evento** y ninguno
decía cuál escala había usado. Medido sobre los ocho `pose.npz` guardados, la diferencia
iba de **1,66 a 4,39 cm** —`pelvis_sway_impact_cm` de `cortado3-lento`: **22,6 cm** en las
métricas contra **26,99** en la tabla, con un MDC de 2,42— y ahora es **≤ 0,046 cm**, que
es el redondeo del sextuplo a un decimal. La tabla por cuadro divide por la escala de la
repetición que contiene a cada fila, la publica fila por fila en la columna nueva
`escala_px`, y un cuadro fuera de toda repetición **no tiene cm** (antes tenía un número
dividido por una escala que no usaba nadie más). `reps[].scale_px` y `reps[].scale_source`
entran a `analysis.json` como **campos opcionales**: `schema_version` **2.0.0 → 2.1.0**,
minor. El fallback de `px_to_cm` **sigue vivo** —no se cambia un valor publicado por un
`null` sin decisión del dominio— pero deja de ser mudo: `scale_source` dice
`body_height_px_frame` y `warnings[]` explica que ahí el divisor no es uno solo.
**Ninguna métrica de `analysis.json` se movió en ningún clip**, que era la condición de
parada del prompt. Suite **397 pasados, 0 fallados, exit 0** (eran 389; el salteado es por
los pesos, que no están en el worktree); arnés **43/0, exit 0**; `pnpm lint` y `pnpm build`
exit 0; mutación manual **8 de 8 en rojo**. **Para decidir (no era de esta sesión): si se
agrega un selector de repetición** — hoy la pantalla dice «repetición 1 de N» y no deja
elegir, y en `cortado3-lento` la 2 tiene una escala 6 % distinta (831,3 contra 783,9).

Para Hernán: **la rama no entró a main porque `integrar` usa `flock` y macOS no lo tiene**
(el merge es limpio; desde main: `git merge --no-edit worktree-agent-a01c88f39db55f574`), y
después levantá el front (`.venv/bin/python -m service` + `cd web && pnpm dev`) y subí
`~/Desktop/cortado.mp4` (~10 s): la fila «pelvis vs address» en el top tiene que decir
−3,5 cm, el mismo número que la métrica de arriba — antes decía −4,6.

Encargo: `docs/prompts/33-una-sola-escala-en-la-pantalla.md` — una sola escala en la
pantalla y dicha: la escala por repetición publicada, la tabla por cuadro dividiendo por
ella, la procedencia de cada cm, «vs address» sin address dicho, y «repetición 1 de N».

Hecho:
- `9f8c008` — `kinelab/metrics/core.py`: `scale_detail()` gana `source`, con dos valores y
  sólo dos (`SCALE_SOURCE_CHAIN` = `stature_chain_rep`, `SCALE_SOURCE_FRAME` =
  `body_height_px_frame`), que son los dos caminos de `px_to_cm`. Con el fallback,
  `value` es `None` **a propósito**: ahí el divisor no es uno solo, es la altura de cuerpo
  del cuadro del evento cero de **cada** métrica, que no es el mismo para todas.
- `9f8c008` — `kinelab/analysis.py`: `reps[].scale_px` y `reps[].scale_source`; la razón
  del fallback a `warnings[]` (el sextuplo no la admite: `$defs/metric` es
  `additionalProperties: false`); `quality.scale_px` conserva su valor y su `method` ahora
  dice que es la mediana **entre repeticiones** y manda a `reps[].scale_px`.
  `SCHEMA_VERSION` **2.1.0**.
- `9f8c008` — `kinelab/contract/schema.json`: los dos campos, **opcionales** y con `enum`
  en `scale_source`. `CONTRATO.md` §La escala y §Versionado lo documentan;
  `data/examples/analysis.example.json` regenerado con el generador de siempre
  (`tests/helpers/gen_analysis_example.py`, pose sintética).
- `9f8c008` — `kinelab/explore.py`: `per_frame_table(..., reps=None)` al final de la firma
  (las tres llamadas posicionales siguen andando); `_scale_per_frame` arma el divisor
  cuadro a cuadro; columna nueva `escala_px`; y `datos-eventos.json` suma `escala_px`,
  `escala_fuente`, `escala_cuadro`, `referencia_cuadro`, `referencia_fuente`,
  `repeticion_mostrada` y `repeticiones`.
- `9f8c008` — `tests/test_una_sola_escala.py` (nuevo, 7 tests) y un test nuevo en
  `tests/test_escala.py`; los tres `schema_version == "2.0.0"` de `tests/test_fase2.py`
  pasan a `"2.1.0"`.
- `5c469e9` — front: la escala y la referencia en la cabecera de `TablaCuadros` y de
  `TablaEventos`, la escala de la repetición al lado de las métricas, «Repetición 1 de N»
  siempre (sin selector: el prompt lo prohíbe y con razón), `textoEscala()` y
  `ESCALA_FUENTE` en `etiquetas.ts`, los campos opcionales en `api.ts`, y
  `CONTRATO_VIGENTE` a 2.1.0. El comentario de `TablaCuadros:4` decía 118 columnas: hoy
  son **116 con altura y 107 sin ella** (eran 115 y 106; la columna nueva es `escala_px`).

Probado:
- **Tabla antes/después desde los `pose.npz` guardados** (invariante 1: no se corrió el
  modelo en ningún clip). El «antes» es HEAD extraído con `git archive` a una carpeta
  aparte y corrido con el mismo script: son dos códigos sobre la misma pose.

  | clip | cuadros | reps | escala(s) px | filas con cm | pico `hands_speed_cm_s` | peor dif tabla↔métrica |
  |---|---|---|---|---|---|---|
  | `cortado` | 76 | 1 | 1089,6 | 76 → **69** | 835,6 → **675,3** | 1,75 → **0,039** |
  | `20260907_170638` | 265 | 1 | 1091,8 | 265 → **78** | 831,0 → **672,0** | 1,66 → **0,046** |
  | `vid1` | 1066 | 1 | 1196,4 | 1066 → **163** | 779,2 → **687,1** | 1,84 → **0,035** |
  | `vid2` | 292 | 1 | 1183,4 | 292 → **164** | 734,4 → **639,1** | 2,48 → **0,032** |
  | `vid3` | 189 | **0** | — | 189 → **0** | 629,2 → **null** | — |
  | `Cortado-lenta` | 598 | 1 | 451,7 | 598 → **500** | 838,3 → **741,7** | 1,83 → **0,038** |
  | `cartado2-lenta` | 292 | **0** | — | 292 → **0** | 132,1 → **null** | — |
  | `cortado3-lento` | 2977 | 2 | **783,9 · 831,3** | 2977 → **1363** | 848,3 → **700,9** | **4,39** → **0,029** |
  | `take-01` | 2977 | 2 | 783,9 · 831,3 | 2977 → 1363 | 848,3 → 700,9 | 4,39 → 0,029 |
  | `vid1` sin altura | 1066 | 1 | 1196,4 | 0 → 0 | null → null | — |

  **Ninguna métrica de `analysis.json` se movió en ningún clip** (el prompt pedía parar si
  alguna se movía). `quality.scale_px` tampoco cambió de valor ni de cuadro en ninguno.
  Las únicas columnas que se mueven son las ocho en cm de la tabla por cuadro y
  `hands_speed_cm_s`, que es exactamente lo que el prompt esperaba.
- **Los dos números del mismo evento, antes y después.** Peor caso `cortado3-lento` /
  `take-01`: `pelvis_sway_impact_cm` valía **22,6 cm** en las métricas y **26,99 cm** en la
  tabla — **4,39 cm** de diferencia contra un MDC de **2,416**. Ahora los siete pares
  comparables (sway/lift de pelvis, tórax y cabeza) coinciden en los ocho clips con un
  máximo de **0,046 cm**, que es el `round(value, 1)` del sextuplo y nada más.
- **`cortado3-lento` es el caso que muestra por qué `quality.scale_px` no alcanzaba**: sus
  dos repeticiones tienen escalas **783,9 y 831,3 px** (6,0 % de diferencia), y el número
  publicado en `quality` es 783,9 — el de la repetición 1, que no es el divisor de la 2.
- **Ningún clip real cae al fallback**: los ocho dan `scale_source: stature_chain_rep`. El
  camino `body_height_px_frame` está probado sobre el swing sintético con las rodillas en
  `NaN` (`test_sin_cadena_el_analysis_dice_que_cayo_al_fallback`), que es la única forma de
  ejercitarlo hoy.
- **Suites**: motor **397 pasados, 0 fallados, 1 salteado, exit 0** (eran 389 pasados;
  +8 tests). El salteado es `test_perception.py:534`, que pide los pesos reales de
  `models/` y esos no están en el worktree porque git los ignora: en el checkout principal
  ese test corre. Arnés (`truth/.venv/bin/pytest -q` desde `truth/`): **43 pasados, 0
  fallados, exit 0** — `per_frame_table` conserva su firma posicional y `truth/` no se
  tocó. `cd web && pnpm lint` exit 0 · `pnpm build` exit 0 (TypeScript incluido) ·
  `node --experimental-strip-types src/lib/retirados.verificar.mjs` exit 0, **0 fallas**,
  11 bordes de versión (los de 2.0.0 y 2.0.1 pasan a «contrato anterior», que es cierto:
  no traen `reps[].scale_px`).
- **Mutación manual: 8 bugs inyectados, 8 en rojo, control en verde** (130 pasados sobre
  las cinco suites tocadas). Los ocho: la tabla ignorando `reps`; la escala extendiéndose
  a los cuadros fuera de toda repetición; `scale_detail` diciendo siempre `stature_chain_rep`;
  `reps[].scale_px` sin publicar; la razón del fallback sin ir a `warnings[]`; la
  referencia diciendo «address» sin address; la columna `escala_px` sin salir al CSV; y la
  pantalla mostrando la mediana de `quality` en vez de la escala de la repetición 1. El
  último no lo agarraba nada al principio —con repeticiones del mismo tamaño la mediana
  **es** la de la primera— y por eso su test construye un clip de **tres** repeticiones con
  la primera 1,15× más grande, escalada desde los tobillos en la quietud entre swings.

Queda abierto:
- **La rama NO está integrada a main, y no por un conflicto: `integrar` no corre en esta
  Mac.** `~/.claude/skills/orquestador/scripts/integrar` usa `flock` (línea 15) y `flock`
  **no existe en macOS** — no está en `/usr/bin`, ni en `/opt/homebrew/bin`, ni en
  `/usr/local/bin`. El script muere con `flock: command not found` (exit 127) **antes** de
  tocar nada, así que main quedó intacto. La rama es
  `worktree-agent-a01c88f39db55f574` (`976c06a`) y **el merge es limpio**: `git merge-tree
  --write-tree main HEAD` sale con exit 0 y sin conflictos, y el único commit que main
  ganó mientras tanto es `fc4959d`, que no toca ninguno de estos archivos. No lo mergeé a
  mano porque la skill lo prohíbe explícitamente. Para integrarlo, desde el checkout
  principal y en main: `git merge --no-edit worktree-agent-a01c88f39db55f574`. **El
  arreglo del script es del orquestador**, no de este encargo: en macOS la cola se puede
  hacer con `mkdir` (atómico) o con `shlock`, o se instala `util-linux`.
- **No hay selector de repetición, a propósito** (lo prohibía el prompt). Lo que haría
  falta, anotado para el encargo que lo tome: `explore()` arma `datos-eventos.json`, el
  overlay, las fotos por evento y el `address` de la tabla por cuadro con
  `analysis["events"][0]` (`explore.py:366`), así que elegir otra repetición no es cambiar
  un índice en el front — hay que parametrizar `explore()` por repetición (o escribir un
  `datos-eventos.json` por repetición y un overlay por repetición) y que la pantalla pida
  la que corresponde. Mientras tanto, la pantalla lo **dice**.
- **El fallback de `px_to_cm` sigue vivo y ningún clip real lo ejercita.** Si alguna vez
  cae, el `scale_px` de esa repetición sale `null` con `scale_source:
  body_height_px_frame`, y ahí los cm de sus métricas están divididos por números
  distintos entre sí. Matarlo sigue siendo una decisión del dominio y sigue sin tomarse.
- **`escala_cuadro` sólo se publica con una repetición.** Con varias, el cuadro que trae
  `quality.scale_px` es el de la repetición que aportó la mediana y puede no ser la que se
  muestra: mandar a mirar ese cuadro sería mandar a mirar uno que no produjo esa escala.
  Publicar el cuadro por repetición pide un campo más en `reps[]` y otro bump.
- **Un cuadro fuera de toda repetición perdió sus cm**, y en `vid1` eso es 903 de 1066
  filas. Es lo que el prompt pedía y es lo correcto —no hay ninguna escala que sea la
  suya—, pero la tabla por cuadro se usa como lupa de exploración y ahí ahora hay más
  huecos que antes. Las columnas en `%` de altura no cambiaron: siguen en todos los cuadros.
- **Los trabajos que ya están en la lista son 2.0.0** y no traen los campos nuevos: ahí la
  pantalla no muestra ninguna escala, a propósito, y sí muestra el aviso de contrato
  anterior. Hay que subir uno nuevo para ver lo de este encargo.
- **`data/exploracion/` y la demo no se regeneraron** (lo prohibía el prompt), así que el
  sitio publicado sigue mostrando los números viejos de la tabla por cuadro.
- No se tocó `kinelab/ingest/`, `sports/`, `truth/`, `service/`, ningún umbral, ningún
  `metric_version` ni el `registry_version`; no se corrió pose sobre ningún clip.

Para que pruebe Hernán:
1. `.venv/bin/python -m service` y, en otra terminal, `cd web && pnpm dev`. Abrir
   http://localhost:3000.
2. **Subir `~/Desktop/cortado.mp4`** (~10 s, 76 cuadros, una repetición). En **«Con este
   archivo»** tiene que aparecer, arriba de la tabla de métricas: **«Repetición 1 de 1.»**
   y **«Los cm de abajo se dividieron por 1.089,6 px · máximo de la cadena de la estatura
   en la repetición (cuadro 75).»**
3. **En «En cada evento»**, la misma escala y **«Las filas "vs address" se miden contra el
   address (cuadro 7)»**. Y el número que importa: la fila **«pelvis vs address (dx / dy)»**
   en la columna **top** tiene que decir **−3,5 cm**, que es el mismo número que la métrica
   `pelvis_sway_top_cm` de arriba. Antes decía **−4,6** y la métrica **−3,5**: eran los dos
   números distintos para el mismo evento que este encargo fue a cerrar.
4. **En «Todos los cuadros»**, la misma línea arriba de la tabla, más «los cuadros fuera de
   una repetición no tienen cm». Filtrá por `escala` y va a aparecer la columna **«escala
   usada en esta fila (divisor de los cm)»**: **1.089,6 px** en los cuadros 7 a 75 —los de
   la repetición— y **vacía** en los siete primeros (0 a 6). En esos siete, las columnas en
   cm también están vacías y las de `% altura` no: 69 de 76 filas tienen cm.
5. **Un trabajo de la lista de antes** (cualquiera de los que ya estaban): ahí **no** tiene
   que aparecer ninguna línea de escala —el motor no la mandó y no se inventa— y **sí** el
   aviso de arriba «Este trabajo se calculó con un contrato anterior: su `analysis.json` es
   2.0.0 y el vigente es 2.1.0…», que ahora es verdad para los 2.0.0.
6. Si querés ver el caso de dos repeticiones con **dos escalas distintas**, subí
   `data/incoming/cortado3-lento.mp4` (~5 min de pose): la pantalla dice «Repetición 1 de
   2» y la escala **783,9 px**; la repetición 2 tiene **831,3** y está en `analysis.json`,
   no en la pantalla.

Preguntas para el orquestador:
- **`integrar` está roto en esta Mac y no es de este encargo arreglarlo.** Usa `flock`, que
  no viene en macOS; muere con exit 127 antes de tocar nada. Toda sesión que trabaje en un
  worktree va a terminar con su rama sin integrar hasta que se arregle. La cola sigue
  haciendo falta (ocho merges simultáneos dan 1 de 8): en macOS sirve `mkdir` como lock
  atómico, o `shlock`, o instalar `util-linux`.
- **Si se abre el encargo del selector de repetición.** Hoy toda la pantalla es la
  repetición 1 y lo dice, pero en `cortado3-lento` la 2 tiene una escala 6 % distinta y sus
  propias métricas, y no hay forma de verlas sin abrir `analysis.json`. Lo que cuesta está
  arriba, en «Queda abierto»: no es un índice en el front.
- **Si el fallback de `px_to_cm` se mata.** El prompt decidió no matarlo en este encargo y
  fue lo correcto; ahora que la procedencia está publicada, la pregunta se puede contestar
  con datos el día que un clip real caiga ahí. Hoy ninguno de los ocho cae.
- **Que la tabla por cuadro perdió cm en la mayoría de sus filas** (en `vid1`, 903 de
  1066). Es lo correcto y es lo que el prompt pidió, pero es un cambio visible en la
  herramienta de exploración: si molesta, la alternativa no es volver atrás sino mostrar
  esos cuadros con la escala de la repetición más cercana **dicha como tal**, que es otra
  decisión.
- **Los `analysis.json` y los CSV de `data/exploracion/` y de la demo siguen con los
  números viejos** (congelados por el prompt). Cuándo se regeneran y se vuelve a desplegar
  es del encargo 25, no de éste.
