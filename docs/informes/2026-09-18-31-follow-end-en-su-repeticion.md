# follow-end-en-su-repeticion — 2026-09-18

Resumen: El fin del acompañamiento ya no se va al swing siguiente. `stable_window_start`
gana una cota (`before`) y el deporte le pasa el fin de su propio candidato de
segmentación; sin quietud adentro, `follow_end` es `null` con la razón escrita en
`warnings[]`. En `cortado3-lento` / `take-01` la repetición 1 pasa de 1978 a `null`
(`follow_duration_ms` 2556,7 → `null`) y **`vid1` también**: de 931 a `null`, por el mismo
bug y sin que nadie lo hubiera visto — su 931 caía en la quietud del candidato siguiente.
`20260907_170638` conserva su 188, ahora con `method: stable_window_in_rep`. **Ningún
otro evento se movió en ningún clip**, `scale_px` sigue en 783,9 (cuadro 1594) y ninguna
métrica en cm cambió. `tol_frames` llega a `datos-eventos.json` y a la tabla por evento
(vid1: top ±4). El CSV y el overlay salen ahora de la misma señal de manos que los
eventos: el centro de manos cambia en 7–109 cuadros por clip, hasta 126 px. Tres restos
cerrados: `events/order.py` de baja, docstring del gate corregido, nota fechada bajo
ADR-019. Suite 390 pasados / 0 fallados / exit 0 (eran 381); arnés 43/0/exit 0; web lint
y build en verde. **Para decidir (no era de esta sesión): qué es el finish** — llegar a la
pose o soltarla —, porque hasta que se defina el motor marca el inicio de la quietud y en
cuatro de los cinco clips reales no hay `follow_end` que marcar (el único que lo tiene es
`20260907_170638`).

Encargo: `docs/prompts/31-follow-end-en-su-repeticion.md` — la cota del `follow_end` dentro
de su repetición, `tol_frames` a la pantalla, una sola señal de manos en el CSV, y tres
restos (order.py, docstring del gate, nota de deriva en ADR-019).

Hecho:
- `513194c` — `kinelab/events/primitives.py`: `stable_window_start` gana `before: int |
  None`; la ventana tiene que caber entera en `(after, before]` (una racha que arranca
  adentro y sigue después del tope cuenta sólo hasta el tope). Nuevo `MissingEvent(id,
  reason)`: un evento ausente **con** su razón, falso en un booleano, que el motor escribe
  como `null` y cuya razón manda a `warnings[]`. El schema no se tocó.
- `513194c` — `sports/golf/events.py`: la cota es `cand.end`. **El prompt suponía que el
  fin del candidato «hoy no llega hasta ahí» y sí llegaba**: `detect_golf_events(sig,
  cand, params)` ya recibe el `RepCandidate` entero, así que no hizo falta ni cambiar la
  firma ni pasarlo por `GolfEventParams`. `method` pasa a `stable_window_in_rep`, y
  `settle_forward` también se acota al fin de la repetición.
- `513194c` — `kinelab/analysis.py`: las razones de los `MissingEvent` van a `warnings[]`
  como `Repetición N: sin \`follow_end\` — …`.
- `513194c` — `kinelab/explore.py`: `eventos_tol_frames` en `datos-eventos.json`, y
  `per_frame_table` recibe el `wrist_score_min` del deporte (default 0,0, que es la firma
  anterior: la usa `truth/`, que no tiene deporte).
- `513194c` — front: `eventos_tol_frames` en `Resumen` (opcional), `textoTolerancia` en
  `etiquetas.ts` y «cuadro N · t s · ± K cuadros» en la cabecera de `TablaEventos`. Si el
  motor no la mandó (trabajo viejo) no se inventa un ±1.
- `6bea1fb` — `git rm kinelab/events/order.py` (huérfano desde ADR-018, nadie lo
  importaba); el docstring de `kinelab/ingest/gate.py` dice que los tres chequeos de la
  Fase 1 existen desde el 17 y los escribe `perception/run.py`; nota fechada bajo ADR-019
  con la deriva en y medida por el 29.

Probado:
- **Tabla antes/después, desde el `pose.npz` guardado** (invariante 1: no se volvió a
  correr el modelo en ningún clip).

  | clip · rep | `follow_end` antes | después | `follow_duration_ms` antes | después |
  |---|---|---|---|---|
  | `cortado` r1 | `null` | `null` | `null` | `null` |
  | `20260907_170638` r1 | 188 | **188** | `null` (no hay `analysis` con fps ≥ 120) | `null` |
  | `vid1` r1 | 931 | **`null`** | `null` (60 < 120 fps) | `null` |
  | `vid2` r1 | `null` | `null` | `null` | `null` |
  | `cortado3-lento` r1 | 1978 | **`null`** | **2556,7 ms** | **`null`** |
  | `cortado3-lento` r2 | `null` | `null` | `null` | `null` |
  | `take-01` r1 | 1978 | **`null`** | **2556,7 ms** | **`null`** |
  | `take-01` r2 | `null` | `null` | `null` | `null` |

  `tol_frames` (address / top / impacto / follow): 1/1/1/— en `cortado`, `vid2`,
  `cortado3` r1 y r2 y `take-01` r1 y r2; 1/1/1/**2** en `20260907_170638`; 1/**4**/1/— en
  `vid1`. **Address, top e impacto no se movieron ni un cuadro en ningún clip**, y de las
  métricas de `take-01` la única que cambió es `follow_duration_ms` (2556,7 → `null`):
  `scale_px` sigue en 783,9 px del cuadro 1594 y las ocho métricas en cm quedaron
  idénticas, aunque el `frame_end` de la repetición 1 bajó de 1978 a 1765 (el máximo de la
  cadena de la estatura cae en 1594, adentro de las dos ventanas).
- **Por qué `cortado3` r1 da `null`, con la señal**: entre el impacto (1364) y el fin del
  candidato (1765) la única racha de quietud es 1507–1566, **60 cuadros** a 240,15 fps
  (0,25 s) contra los **72** que pide `follow_still_s`. La que el motor elegía antes
  empieza en **1947** y es la del address de la repetición 2 (2322). En r2: racha
  2790–2844, **55 cuadros**, mismo resultado.
- **Por qué `vid1` se movió, con la señal**: su impacto es 741 y su candidato termina en
  **834**; la primera quietud de 18 cuadros después del impacto empieza en **929**, dentro
  del candidato **siguiente** (773–983), que el motor había descartado como repetición.
  Los 931 de antes eran, cuadro por cuadro, el mismo bug de `cortado3`: 190 cuadros
  después del impacto, 3,2 s a 60 fps. Es el segundo caso del mismo defecto y no estaba en
  la auditoría.
- **Punto 3, cuántos cuadros del CSV cambian.** Los cuadros con al menos una muñeca bajo
  `wrist_score_min` = 0,55 — que son exactamente los que cambian de posición de manos —:
  `cortado` **22** de 76 · `20260907_170638` **84** de 265 · `vid1` **39** de 1066 ·
  `vid2` **7** de 292 · `cortado3-lento` y `take-01` **109** de 2977. El corrimiento
  máximo del centro de manos es **126,4 / 117,8 / 101,8 / 50,2 / 98,3 px**, en ese orden. La velocidad
  filtrada (`hands_speed_bh_s`) cambia numéricamente en casi todos los cuadros porque el
  Butterworth con `filtfilt` no es causal; el cambio supera el 1 % del pico en **32 / 81 /
  66 / 18 / 155** cuadros. Ninguna otra columna del CSV se mueve.
- **Corridas reales**: `python -m kinelab analyze data/sessions/hernan/2026-09-15/driver/
  face_on/take-01 --altura-m 1.75` → exit 0, `verdict: confiable`, 2 repeticiones, las dos
  con `follow_end —` y sus dos avisos en `warnings[]`. Los cuatro `datos` se corrieron
  desde el `pose.npz` guardado (`explore(..., pose_npz=…)`, sin estimador) y los cuatro
  `datos-eventos.json` traen `eventos_tol_frames`.
- **Suites**: motor **390 pasados, 0 fallados, exit 0** (eran 381: +9 tests, ninguna
  aserción existente tocada). Arnés **43 pasados, 0 fallados, exit 0** — no se tocó
  `truth/`, y `per_frame_table` mantiene su firma vieja con el umbral en 0,0. `cd web &&
  pnpm lint && pnpm build`: los dos en verde, TypeScript incluido.
- **Mutación manual: 6 bugs inyectados, 6 en rojo, control en verde.** `before` ignorado en
  la primitiva → 2 tests; el deporte sin pasar la cota → 2; `MissingEvent` verdadero en un
  booleano → 4; `per_frame_table` ignorando el umbral → 1; `datos-eventos.json` sin
  `eventos_tol_frames` → 1; `settle_forward` sin acotar → 1. El último no lo agarraba nada
  y se le escribió su test: con los parámetros de golf de hoy (`refine_s` 0,15 s contra
  `follow_still_s` 0,3 s) el límite no llega a morder nunca, así que el caso se construye
  con la velocidad y los cuadros a mano — es la única forma de que quede defendido si
  alguien mueve esos dos números.

Queda abierto:
- **En cuatro de los cinco clips reales no hay `follow_end`** —el único que lo tiene es
  `20260907_170638`—, y en las dos repeticiones de `cortado3` tampoco. Antes había un número en dos de ellos y era falso; ahora hay un hueco con su
  razón, que es lo correcto, pero `follow_duration_ms` no se mide en ninguna toma del
  repo. Sale de la definición, no de un umbral (ver la pregunta de abajo).
- **`follow_still_s`, `still_speed_max` y `wrist_score_min` no se tocaron** (lo prohibía el
  prompt, y con n = 1 corresponde).
- **El `null_reason` del evento no viaja en el evento**, porque `$defs/event` es
  `additionalProperties: false`. Va a `warnings[]`. Si el orquestador quiere que la
  pantalla lo muestre pegado al evento y no en la lista de avisos, eso es un campo nuevo
  en el schema y un bump.
- **La pantalla no muestra la razón del hueco al lado del evento**: hoy la ve en los
  avisos de arriba, que es donde el motor la escribe.
- No se tocó `kinelab/metrics/`, `sports/golf/metrics.py`, el schema, `service/`,
  `truth/`, ni ningún umbral; no se re-corrió percepción sobre ninguna toma. El front no
  se abrió (el prompt dice que lo prueba Hernán).

Para que pruebe Hernán:
1. `.venv/bin/python -m service` y, en otra terminal, `cd web && pnpm dev`. Abrir
   http://localhost:3000.
2. **Subir `data/incoming/vid1.mp4`** (tarda ~80 s: es 4K 60). Es el que importa: en la
   tabla **En cada evento**, la columna **Top** tiene que decir `cuadro 722 · 12,028 s ·
   ± 4 cuadros`, y address e impacto `± 1 cuadro`. Ese ±4 es la banda real del top de ese
   clip (tres candidatos a 2–3 px de distancia con 4,7 px de ruido por cuadro) y hasta hoy
   sólo estaba en `analysis.json`.
3. Los trabajos **que ya están en la lista** son de antes y no traen el campo: ahí no
   aparece ningún ±, a propósito — no se inventa un ±1 donde el motor no lo mandó. Si
   querés una prueba más corta, `~/Desktop/cortado.mp4` tarda ~10 s y muestra `± 1 cuadro`
   en los tres eventos.
4. En cualquier trabajo con dos repeticiones y sin quietud propia (por ejemplo
   `cortado3-lento.mp4`, ~5 min de pose) el aviso nuevo aparece **arriba, entre los
   avisos**: «Repetición 1: sin `follow_end` — sin quietud de 0,3 s entre el impacto
   (cuadro 1364) y el fin de la repetición (cuadro 1765)…».

Preguntas para el orquestador:
- **Qué es el finish** (la que la auditoría le dejó a Hernán, §6 D-4): llegar a la pose
  final o soltarla, ≈380 ms de diferencia. Hoy el motor marca el **inicio** de la quietud
  y lo dice en el `method`. Mientras no se defina, `follow_duration_ms` no existe en
  ninguna toma del repo, así que la pregunta dejó de ser teórica.
- **`follow_still_s` con material nuevo.** La pausa del finish mide 60 cuadros en la
  repetición 1 de `cortado3` y 55 en la 2, contra los 72 que pide el umbral. Con n = 1 no
  se toca; con la sesión de validación filmada, ahí sí hay con qué decidir si 0,3 s es el
  número o si el finish de un golfista dura menos.
- **`vid1` es un caso nuevo del mismo defecto** y no estaba en la auditoría: el `follow_end`
  931 que la demo pública mostraba era la quietud del movimiento siguiente. Si esa demo se
  vuelve a publicar, el número cambia a un hueco.
- **La razón del hueco en la pantalla**: hoy está en los avisos generales. Ponerla pegada
  al evento pide un campo en `$defs/event` y un bump de schema; no lo hice porque el
  prompt lo prohibía explícitamente.
