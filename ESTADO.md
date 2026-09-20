# Estado del trabajo

Dónde quedó el repo al cerrar la última sesión. Se lee **después** de los seis
documentos de `AGENTS.md` y se actualiza al cerrar cada sesión.

## 20 de septiembre de 2026 — encargo 35: el motor publica todas las repeticiones

Prompt: `docs/prompts/35-el-motor-publica-todas-las-repeticiones.md`. Informe:
`docs/informes/2026-09-20-35-el-motor-publica-todas-las-repeticiones.md`. **Sin sesión
en paralelo** (lo pedía el prompt). Commits: `4cb85a5` (motor y servicio), `3114f86`
(tests), `5730219` (demo y contrato) y el de cierre, con este archivo y el informe.
Hecho en un worktree, arrancado desde `main` (`f95875c`).

### Qué existe ahora

- **`datos-eventos.json` publica `repeticiones_detalle`**: una entrada por repetición,
  en orden, con `rep`, `frame_start`, `frame_end`, `eventos_frame`, `eventos_t_s`,
  `eventos_tol_frames`, `eventos_subcuadro`, `escala_px`, `escala_fuente`,
  `escala_cuadro`, `referencia_cuadro`, `referencia_fuente`, `duraciones`, `picos`,
  `en_cada_evento` y `diferencias_vs_address`. Los nombres son los que ya existían en
  el primer nivel: es el mismo dato, una repetición más abajo.
- **Los campos de primer nivel NO se movieron** y siguen diciendo
  `repeticion_mostrada: 1`. Son **transitorios** y están marcados con un comentario:
  los retira el encargo 36. Medido: 27 claves antes, 28 después, la nueva es
  `repeticiones_detalle`, y ninguna de las 27 cambió de valor.
- **`_rebasar` es el corazón del encargo.** Las columnas `*_vs_address_*` de la tabla
  por cuadro se calculan contra **un solo** cuadro (el address de la repetición 1);
  para otra repetición se le resta la fila de su propio address y la referencia se
  cancela. La repetición cuyo address **es** ese cuadro pasa con `base=None` y no se
  le toca un float: por eso el primer nivel queda idéntico **por construcción**.
- **El overlay rotula los eventos de todas las repeticiones** (`R2 IMPACT`) y sigue
  siendo **uno solo**. `_TEXT_TEMPLATES` suma el `R99` para que la fuente se siga
  fijando con la línea más ancha posible.
- **Las fotos**: la repetición 1 conserva `evento-<id>.png` y las demás salen como
  `evento-r<N>-<id>.png` (`foto_de_evento`). La lista blanca de
  `service/exploracion.py` las acepta **por forma** —expresión anclada, N de 1 a 3
  cifras, el evento uno de los cuatro que ya estaban—, porque cuántas hay lo decide el
  material. `archivos_servibles()` las lista por repetición y por evento.
- **La demo se las lleva sola**: `exportar_fotos` junta `evento-*.png` y no tiene lista
  de nombres. Fijado con una `evento-r2-top.png` en el trabajo sintético de su test.
- **`CONTRATO.md` §Versionado dice que `datos-eventos.json` no es parte del contrato**
  y no lleva `schema_version`: es la salida del modo exploración, así que agregarle un
  campo no bumpea nada. §La escala anota que ahora la escala de cada repetición llega
  a la pantalla.
- **Tests nuevos**: `tests/test_todas_las_repeticiones.py` (8) y uno en
  `tests/test_service.py`.

### Medido

- **Suites**: motor **457 pasados, 0 fallados, 1 salteado, exit 0** (eran 448; **+9
  tests**). El salteado es el de los pesos de `models/`, que git ignora. Arnés **43
  pasados, 0 fallados, exit 0**. `pnpm lint` exit 0 · `pnpm build` exit 0 ·
  verificador de retirados exit 0, 0 fallas.
- **Corrida real sobre el `pose.npz` guardado de `cortado3-lento`** (2977 cuadros,
  240,15 fps) a un directorio temporal, contra el mismo script corrido sobre `f95875c`
  extraído con `git archive`: **2 repeticiones**. Rep 1: cuadros 1052–1765, address
  1052 / top 1284 / impacto 1364, escala **783,9 px**, 966,1 / 333,1 ms, tempo 2,90,
  pico 4,76 bh/s. Rep 2: 2322–2970, address 2322 / top 2548 / impacto 2624, escala
  **831,3 px** (+6,0 %), 941,1 / 316,5 ms, tempo 2,97, pico **4,85 bh/s**. `follow_end`
  falta en las dos (viene del 31).
- **Lo que arregla el rebase**: en la repetición 2, `pelvis_dx_vs_address_cm` daba
  **−2,21 cm** en el top medida contra el address de la repetición 1 y da **−7,05**
  contra el suyo, que es el número de la métrica (−7,1). En el impacto, **12,54 → 7,69**
  contra una métrica de 7,7. **4,84 cm**, dos veces el MDC de 2,416.
- **El pico de primer nivel (4,85 bh/s) es el de la repetición 2**, publicado en una
  pantalla que dice «repetición 1». El detalle ya trae el de cada una.
- **Archivos `evento-*`**: 6 contra 3 (tres por repetición, sin `follow_end`). Un solo
  `overlay.mp4`, 16,47 → 16,48 MB. `datos-eventos.json`, **21,4 → 60,3 KB**
  (~19 KB por repetición; casi todo es `en_cada_evento`).
- **Mutación manual: 7 bugs inyectados, 7 en rojo, control en verde.** Dos de ellos
  —el rótulo sin la repetición y los picos calculados sobre el clip entero— **no los
  agarraba nada** con `synth_swing(n_reps=3)`, porque sus tres repeticiones son
  idénticas; el clip del test pasó a ser la concatenación de tres swings con downswing
  de 0,27 / 0,33 / 0,40 s y el golfista corrido 120 px después del primero.

### Qué falta o no se probó

- **Los campos de primer nivel siguen duplicando `repeticiones_detalle[0]`**, atados
  por un test. Los retira el 36, que tiene que borrar ese test en el mismo movimiento.
- **`escala_cuadro` sigue en `null` con más de una repetición**, también por
  repetición: el cuadro del máximo de la cadena por repetición no está en
  `analysis.json` (`reps[]` lleva `scale_px` y `scale_source`, no el cuadro) y
  agregarlo es un bump de contrato que el prompt prohibía. Misma limitación que anotó
  el 33.
- **`picos` por repetición es el de su tramo** y el de primer nivel sigue siendo el del
  clip: es la única clave del detalle que no vale «lo que hoy es de la rep 1», porque
  lo que hoy hay no es de ninguna en particular.
- **El front no se tocó y no hace falta abrirlo**: pide `evento-<evento>.png` por
  nombre (`web/src/app/page.tsx:305`) y nunca recorre la lista de archivos, así que las
  claves nuevas no lo rozan.
- **El verificador de retirados hay que correrlo desde `$KLAB/web`**: lee
  `web/public/demo/`, que git ignora, y en el worktree no existe. Ahí muere con ENOENT
  y **exit 0** — el error no llega al código de salida, que es una trampa para cualquier
  sesión que lo corra en un worktree y lea sólo el exit code. Los tres archivos que
  compara son idénticos en los dos lados y esta sesión no tocó ninguno.
- **No se tocó** `web/`, `kinelab/contract/schema.json`, `analysis.json` (sigue en
  2.1.0), `kinelab/analysis.py`, `kinelab/metrics/`, `sports/`, `truth/`, ningún
  umbral, ningún `metric_version` ni el `registry_version`. No se regeneró
  `data/exploracion/` ni la demo, y no se corrió pose sobre ningún clip.

### Desviaciones

- **Del contrato, ninguna**, y por eso no hay entrada en §Desviaciones:
  `datos-eventos.json` no es parte del contrato y no lleva versión, cosa que ahora
  §Versionado dice explícitamente.
- **Del prompt, una.** La lista de archivos que este encargo podía tocar **no incluye
  `service/app.py`**, que es donde vive `ARCHIVOS.get(nombre)`. Para respetarla, la
  lista blanca pasó a ser un `dict` con `get` y `in` extendidos a la familia
  `evento-r<N>-…` (`_Servibles`, en `service/exploracion.py`), en vez de una función
  `media_type(nombre)` con dos líneas en `app.py`, que sería lo natural. Anda, está
  testeado y la expresión sigue anclada (no admite `/` ni `.`); queda como pregunta
  para el orquestador.

---

## 20 de septiembre de 2026 — encargo 34: de dónde sale la calibración del fps

Prompt: `docs/prompts/34-fuente-de-la-calibracion.md`. Informe:
`docs/informes/2026-09-20-34-fuente-de-la-calibracion.md`. **Sin sesión en paralelo**
(lo pedía el prompt). Commits: `b94e1be` (motor, datos, contrato y tests), `b4a981e`
(front) y el de cierre, con este archivo y el informe. Hecho en un worktree; el
primer intento del 34 se abandonó y éste arrancó limpio desde `main`.

### Qué existe ahora

- **`capture-paths.yaml` está en 1.2.0** con `calibration_clip_sha256`: de qué clip
  salió el cronómetro de un camino calibrado. **Opcional y FUERA de
  `_CALIBRATION_FIELDS`**, que son todo o nada: un camino calibrado que no lo declara
  sigue cargando, sigue analizando y sigue habilitando juicio. La procedencia **se
  registra, no se exige** — exigirla habría tumbado el único camino calibrado que
  existe (n = 1). Un camino **declarado** no puede declararlo y el validador lo
  rechaza: sin cronómetro no hay clip que lo haya medido.
- **`capture.json` está en 1.3.0** con `fps_calibration {clip_sha256, same_file}`.
  `same_file`: `true` si la toma se calibró a sí misma, `false` si hereda la tasa de
  otro archivo del mismo camino, `null` cuando no se puede saber (el camino no declara
  sha, el camino no está calibrado, o el archivo es anterior a 1.3.0). **`null` no es
  `false`.** Sale sin hash extra: `sha256_original` ya se calculaba.
- **Los dos bumps son minor**, y por la misma razón: campo nuevo, opcional, ningún
  valor publicado se mueve. Un `capture-paths` 1.1.0 y un `capture.json` 1.2.0 siguen
  validando. **No hay entrada en `CONTRATO.md` §Desviaciones**: los dos siguen
  §Versionado tal como está escrita, sin la excusa que necesitó `fps_provenance`.
- **El sha del único camino calibrado está declarado**: `Cortado-lenta.mp4`,
  `ff13415e0a1a…`, el único de los tres clips lentos con el cronómetro **andando** en
  el cuadro. Se leyó del `capture.json` de su exploración y se verificó contra el
  archivo con `shasum -a 256`: no se inventó.
- **No hay `Check` nuevo y `CHECK_ORDER` no se movió.** Es procedencia, no un chequeo:
  ningún veredicto cambia y ninguna toma se rechaza por esto. La frase va a
  `analysis.warnings`, que es el canal que llega a la pantalla también en exploración,
  donde el gate no corre. Queda **junto al aviso de ADR-016 y después de él**, que es
  el más fuerte: ahí la tasa entera es un supuesto, acá está medida y lo único que
  falta es de qué clip salió. Hay un test que fija ese orden.
- **`fps_truth` imprime el sha al terminar**, en la línea exacta que se pega en el
  YAML (`calibration_clip_sha256: "…"`), y también en `--json`. Reusa `sha256_file`;
  se calcula en el CLI y no en `analyze()` para no releer 90 MB en cada ingesta.
- **Las dos fichas de captura tienen quien las vigile.**
  `service.exploracion.ficha_de_captura` y `exportar_demo.ficha_de_captura_min` son
  copias paralelas y hasta hoy nada testeaba que coincidieran:
  `tests/test_fichas_de_captura.py` compara **el conjunto entero de claves y todos los
  valores**, en cuatro casos.
- **El front lo dice en un solo lugar**, la ficha del archivo
  (`FichaArchivo.tsx`), que es el natural: ya muestra el camino y si está calibrado.
  Los otros tres lugares donde aparece el fps quedan como estaban. Si el motor no mandó
  el campo, **no se muestra nada**.
- **`kinelab/ingest/__main__.py` usa `CAPTURE_PATHS_FILE`** en vez del literal.
- **Tests nuevos**: `tests/test_procedencia_calibracion.py` (37) y
  `tests/test_fichas_de_captura.py` (14).

### Medido

- **Suites**: motor **448 pasados, 0 fallados, 1 salteado, exit 0** (eran 397 + 1
  salteado; **+51 tests**). El salteado es el de los pesos de `models/`, que git ignora
  y por eso no están en el worktree. Arnés **43 pasados, 0 fallados, exit 0**.
  `pnpm lint` exit 0 · `pnpm build` exit 0.
- **La corrida real**, `cortado3-lento.mp4` re-ingestado por CLI a un directorio
  temporal (no se pisó ningún trabajo): **gate ok, 9 de 9**, los mismos nueve ids de
  `CHECK_ORDER`, `schema_version: "1.3.0"`, y
  `fps_calibration: {"clip_sha256": "ff13415e0a1a…", "same_file": false}`. El aviso
  sale como **`warnings[0]`** de los 5 del análisis.
- **`Cortado-lenta.mp4`, el clip que calibró el camino, da `same_file: true`** y se
  rechaza igual por `duration_plausible` (2,49 s reales contra 3): la procedencia no
  toca el veredicto, que es el punto.
- **Censo de los 26 `capture.json` que hay en `data/`** (leídos, no regenerados): **2
  quedan en `same_file: false`** y con aviso — la exploración de `cortado3-lento` y
  `sessions/hernan/2026-09-15/.../take-01` —, **1 en `true`** (`Cortado-lenta`) y **23
  en `null` sin aviso**, porque usan caminos **declarados** y de ésos ya avisa ADR-016.
  El prompt esperaba «varios trabajos de exploración»: son dos, y la razón es que casi
  toda la exploración corrió con `desconocido-video`.
- **Mutación manual**: sacarle una clave a una sola de las dos fichas pone **13 de 14**
  en rojo en `test_fichas_de_captura.py`.

### Qué falta o no se probó

- **Los 26 `capture.json` que ya están en disco no se regeneraron** (la demo y
  `data/exploracion/` están congelados): siguen en 1.2.0, sin `fps_calibration`. Al
  re-analizarlos van a mostrar el aviso de `null` —«esta toma no registra con qué
  clip…»— hasta que se los re-ingeste. La frase está redactada para ser cierta también
  en ese caso: dice lo que sabe la **toma**, no lo que dice el YAML de hoy, porque
  `analysis.py` no vuelve a resolver el camino contra `capture-paths.yaml` (y no
  debería: el `capture.json` es lo que la ingesta escribió).
- **El front no se abrió** (regla de trabajo): lo prueba Hernán, con la lista del
  informe. Para ver los tres estados hay que **subir un trabajo nuevo**: los que están
  en la lista son anteriores a 1.3.0 y no traen el campo, así que no muestran nada.
- **`same_file: true` sigue siendo n = 1 y es el clip corto.** El único archivo que se
  calibró a sí mismo es `Cortado-lenta`, que el gate rechaza por durar 2,49 s. El clip
  que pasa el gate (`cortado3-lento`) es justamente el que hereda la tasa. Eso no lo
  arregla este encargo: lo arregla el pedido que viene desde el 24 y el 26 — una toma
  de 25 s con el cronómetro andando en el cuadro.
- **No se tocó** `kinelab/contract/schema.json` ni nada de `analysis.json` (su
  `schema_version` sigue en 2.1.0), ni `kinelab/metrics/`, ni ningún umbral, ni el 717,
  ni `sports/`, ni `truth/`. No se corrió pose sobre ningún clip. No se regeneró
  `data/exploracion/` ni la demo.
- **El bug de `--data` de `explore()` que anota `ESTADO.md` sigue abierto**: es de otro
  encargo y no se tocó.

### Desviaciones

- **Del contrato, ninguna**, y por eso no hay entrada en §Desviaciones. Los dos bumps
  son minor por §Versionado tal como está escrita.
- **Del prompt, dos cosas que agrega y una premisa que confirma como falsa.**
  1. El prompt nombraba sólo `same_file`; el `capture.json` lleva además
     **`clip_sha256`**. Sin él la frase del punto 3 no se puede escribir: `analysis.py`
     sólo lee el `capture.json` y no tendría de dónde sacar **de qué clip** salió el
     fps, que es literalmente lo que el prompt pide decir.
  2. El validador **rechaza** un `calibration_clip_sha256` en un camino sin calibrar, y
     exige que el sha tenga forma de sha (64 hex en minúscula). No es «exigir la
     procedencia»: faltar sigue estando permitido. Lo que se prohíbe es declarar una
     calibración que no existe, y un sha mal pegado, que sería peor que ninguno —
     diría `same_file: false` sobre el archivo correcto.
  3. **El punto 8 tenía razón y queda confirmado**: el bug que suponía el plan en
     `__main__.py:103` **no existe**. `default_capture_paths_file()` no toma argumentos
     y usarla ahí habría ignorado `--data`: sería una regresión. Se cambió sólo el
     literal por la constante, que es lo que el prompt pedía.

---

## 20 de septiembre de 2026 — encargo 33: una sola escala en la pantalla, y dicha

Prompt: `docs/prompts/33-una-sola-escala-en-la-pantalla.md`. Informe:
`docs/informes/2026-09-20-33-una-sola-escala-en-la-pantalla.md`. **Sin sesión en
paralelo** (lo pedía el prompt). Commits: `9f8c008` (motor, contrato, schema, ejemplo y
tests), `5c469e9` (front) y el de cierre, con este archivo y el informe.

### Qué existe ahora

- **`analysis.json` está en 2.1.0.** Entran `reps[].scale_px` y `reps[].scale_source`,
  los dos **opcionales** —campo nuevo y opcional es minor por §Versionado, y así un 2.0.0
  ya escrito sigue validando—. El motor los escribe siempre, en `null` cuando no hay
  escala. **Ningún valor publicado cambia**, así que no se movió ningún `metric_version`
  ni el `registry_version` (golf sigue en 0.3.0).
- **`scale_source` tiene dos valores y sólo dos**, porque son los dos caminos de
  `px_to_cm`: `stature_chain_rep` (hay cadena; `scale_px` es el divisor de todas las
  métricas en cm de esa repetición) y `body_height_px_frame` (no hay cadena; `scale_px` es
  `null` porque el divisor **no es uno solo**: es la altura de cuerpo del cuadro del evento
  cero de cada métrica). El fallback **sigue vivo**; lo que deja de ser es mudo.
- **La tabla por cuadro usa la escala de la repetición que contiene a cada fila.**
  `per_frame_table` gana `reps=None` **al final** de la firma, así que las tres llamadas
  posicionales (dos de `tests/test_eventos_senal.py` y una de `truth/tests/test_angulos.py`)
  siguen andando y con los números de antes. Un cuadro fuera de toda repetición **no tiene
  cm**. Columna nueva `escala_px`: el divisor de esa fila, en píxeles, vacío donde no hay.
  **115 → 116 columnas** con altura declarada y **106 → 107** sin ella.
- **`datos-eventos.json`** suma `escala_px`, `escala_fuente`, `escala_cuadro`,
  `referencia_cuadro`, `referencia_fuente`, `repeticion_mostrada` y `repeticiones`.
  `escala_cuadro` sólo con una repetición: con varias, el cuadro de `quality.scale_px` es
  el de la que aportó la mediana y puede no ser la que se muestra.
- **`quality.scale_px` no cambió de valor ni de cuadro en ningún clip**; su `method` dice
  ahora que es la mediana **entre repeticiones** y que con dos o más no es el divisor de
  ninguna, y manda a `reps[].scale_px`.
- **La pantalla lo dice**, en tres lugares: la cabecera de `TablaCuadros` (escala,
  referencia, y que los cuadros fuera de una repetición no tienen cm), la de
  `TablaEventos` (lo mismo, más «Repetición 1 de N: todo lo de esta pantalla es esa») y al
  lado de las métricas (`Metricas`, con la escala de **esa** repetición: `quality.scale_px`
  no sirve ahí). Si el motor no mandó el campo —trabajo anterior a 2.1.0— **no se muestra
  nada**. `CONTRATO_VIGENTE` del front pasa a 2.1.0, así que un trabajo 2.0.0 saca el aviso
  de contrato anterior, y es cierto: no trae la escala por repetición.
- **Sin address, «vs address» lo dice.** `explore.py` cae al cuadro 0 y los valores no
  cambian; `referencia_fuente` dice `cuadro 0 (sin address)` y la pantalla lo muestra al
  lado de las ocho columnas `*_vs_address_*`.
- **`tests/test_una_sola_escala.py`** (nuevo, 7 tests) y uno nuevo en `tests/test_escala.py`.
  El comentario de `TablaCuadros.tsx:4` decía 118 columnas (eran los CSV congelados de la
  demo): corregido con los números de hoy.

### Medido

- **Antes → después desde los ocho `pose.npz` guardados** (invariante 1: el modelo no se
  volvió a correr; el «antes» es HEAD extraído con `git archive` y corrido con el mismo
  script). **Ninguna métrica de `analysis.json` se movió en ningún clip** — era la
  condición de parada del prompt. Lo único que se mueve son las ocho columnas en cm de la
  tabla por cuadro y `hands_speed_cm_s`.
- **Los dos números del mismo evento.** Peor caso `cortado3-lento` / `take-01`:
  `pelvis_sway_impact_cm` valía **22,6 cm** en las métricas y **26,99 cm** en la tabla —
  **4,39 cm**, contra un MDC de **2,416**. En los ocho clips la peor diferencia iba de
  **1,66 a 4,39 cm** y ahora es **≤ 0,046 cm**, que es el `round(value, 1)` del sextuplo.
- **`cortado3-lento` muestra por qué `quality.scale_px` no alcanzaba**: sus dos
  repeticiones tienen **783,9 y 831,3 px** (6,0 % de diferencia) y el número publicado es
  el de la primera.
- **Filas con cm**, antes → después: `cortado` 76 → 69 · `20260907_170638` 265 → 78 ·
  `vid1` 1066 → 163 · `vid2` 292 → 164 · `Cortado-lenta` 598 → 500 · `cortado3-lento` y
  `take-01` 2977 → 1363 · `vid3` 189 → **0** y `cartado2-lenta` 292 → **0** (los dos sin
  ninguna repetición). El pico de `hands_speed_cm_s` baja en consecuencia (por ejemplo
  `cortado` 835,6 → 675,3 cm/s) y pasa a `null` en los dos sin repeticiones.
- **Ningún clip real cae al fallback**: los ocho dan `stature_chain_rep`. El camino
  `body_height_px_frame` se prueba con el swing sintético con las rodillas en `NaN`.
- **Suites**: motor **397 pasados, 0 fallados, 1 salteado, exit 0** (eran 389 pasados;
  +8 tests). El salteado es `test_perception.py:534`, que pide los pesos de `models/` y
  esos no están en el worktree porque git los ignora. Arnés **43 pasados, 0 fallados,
  exit 0**. `cd web && pnpm lint` exit 0 · `pnpm build` exit 0 ·
  `node --experimental-strip-types src/lib/retirados.verificar.mjs` exit 0, 0 fallas.
- **Mutación manual: 8 bugs inyectados, 8 en rojo, control en verde.** El octavo —mostrar
  la mediana de `quality` en vez de la escala de la repetición 1— **no lo agarraba nada**
  al principio, porque con repeticiones del mismo tamaño la mediana *es* la de la primera:
  su test construye un clip de **tres** repeticiones con la primera 1,15× más grande.

### Qué falta o no se probó

- **La rama quedó SIN integrar a main, y no por un conflicto.**
  `~/.claude/skills/orquestador/scripts/integrar` usa `flock` (línea 15) y `flock` **no
  existe en macOS**: el script muere con exit 127 **antes** de tocar nada, así que main
  quedó intacto. La rama es `worktree-agent-a01c88f39db55f574` (`976c06a`) y el merge es
  **limpio** (`git merge-tree --write-tree main HEAD` → exit 0, sin conflictos; el único
  commit que main ganó es `fc4959d`, que no toca estos archivos). Desde el checkout
  principal y en main: `git merge --no-edit worktree-agent-a01c88f39db55f574`. **Esto le
  va a pasar a toda sesión que trabaje en un worktree** hasta que se arregle el script; la
  cola sigue haciendo falta y en macOS se puede hacer con `mkdir` o `shlock`.
- **No hay selector de repetición** (lo prohibía el prompt, y con razón). Lo que haría
  falta está en el informe §Queda abierto: `explore()` arma `datos-eventos.json`, el
  overlay, las fotos por evento y el `address` de la tabla con `analysis["events"][0]`
  (`explore.py:366`), así que no es un índice en el front — hay que parametrizar `explore()`
  por repetición. Mientras tanto la pantalla lo dice.
- **La tabla por cuadro perdió los cm de la mayoría de sus filas** (en `vid1`, 903 de
  1066). Es lo que el prompt pedía y es lo correcto —no hay escala que sea la de esos
  cuadros—, pero es un cambio visible en la lupa de exploración. Las columnas en `%` de
  altura no cambiaron.
- **El fallback de `px_to_cm` sigue vivo y ningún clip real lo ejercita.** Matarlo sigue
  siendo una decisión del dominio, y ahora se puede tomar con la procedencia publicada.
- **El front no se abrió** (regla de trabajo): lo prueba Hernán, con la lista de seis
  puntos del informe. Los trabajos que ya están en la lista son 2.0.0 y no traen los campos
  nuevos: hay que subir uno para ver esto.
- **`data/exploracion/` y la demo no se regeneraron** (congelados por el prompt): el sitio
  publicado sigue con los números viejos de la tabla por cuadro.
- No se tocó `kinelab/ingest/`, `sports/`, `truth/`, `service/`, ningún umbral, ningún
  `metric_version` ni el `registry_version`; no se corrió pose sobre ningún clip.

### Desviaciones

- **Del contrato, ninguna**, y por eso no hay entrada en §Desviaciones. El bump
  `analysis.json` **2.0.0 → 2.1.0** sigue la regla de §Versionado tal como está escrita
  —«métrica nueva y opcional es minor»—: entran dos campos **opcionales**, ninguno se
  renombra, ninguna unidad cambia y ningún valor publicado se mueve. Van opcionales a
  propósito: requeridos habrían invalidado los `analysis.json` 2.0.0 ya escritos, que es
  lo que §Versionado llama major, y eso sí habría necesitado una desviación como la del
  bump de `fps_provenance`. El bump queda documentado en §Versionado con sus tres razones.
- **Del prompt, una.** El punto 3 pedía «la procedencia por métrica donde hoy cae el
  fallback de `px_to_cm`». No puede ir en el sextuplo: `$defs/metric` es
  `additionalProperties: false` y agregarle un campo sería otro bump, que el mismo prompt
  prohibía. Va a `warnings[]` —el patrón de ADR-019— y a `reps[].scale_source`, que está
  al lado de `reps[].metrics`. La frase dice además lo que la caída tiene de particular:
  ahí el divisor no es uno solo.

---

## 20 de septiembre de 2026 — encargo 32: la máscara del sujeto, medida

Prompt: `docs/prompts/32-mascara-del-sujeto.md`. Informe:
`docs/informes/2026-09-20-32-mascara-del-sujeto.md`. **En paralelo con el 31**, que ya
cerró y cuyos archivos no toca esta sesión. Commits: `83338ca` (el script) y el de
cierre, con este archivo y el informe. **Es un experimento, no un producto**: no entra
nada al motor.

### Qué existe ahora

- **`banco/mascara_sujeto.py`** (nuevo, 1164 líneas con su docstring). Mide qué compra y
  qué cuesta una máscara del sujeto. **Importa** `kinelab.tools.camera_drift` (`mascara`,
  `estimar`, `alto_cuerpo_px`, `primer_cuadro_con_pose`, `Params`) en vez de copiarla, más
  `perception.video.iter_frames` y `perception.posestore.load_pose`. Nada de `kinelab/` lo
  importa a él, no escribe en `analysis.json` ni en `pose.npz`, y no corre pose sobre nada.
- **El método**: estabilizar contra el cuadro de referencia con la homografía del fondo del
  29 · **mediana temporal por píxel** descartando de cada muestra los píxeles donde la pose
  dice que está el sujeto (silueta dibujada desde los keypoints, **no** el `bbox`) · umbral
  por píxel `max(12, 3 · 1,4826 · MAD)` con el MAD temporal del propio modelo · **dos
  máscaras** del mismo umbral, la del sujeto (con cierre) y la **fina**.
- **El palo** se ajusta con una **Hough anclada en las muñecas** más `cv2.fitLine` (Huber) en
  tres vueltas. Anclar aguanta el shaft punteado; soltar después recupera la punta.
- **Dos modelos de fondo**: el **global** (muestras de todo el clip, con el sujeto
  enmascarado) y el **local** (±0,5 s alrededor de un evento, **sin** enmascarar, así el
  cuerpo casi quieto entra al modelo y sólo queda de primer plano lo rápido).
- **Controles por CLI**: `--ocupacion silueta|bbox|bbox-y-palo`, `--gris`, `--umbral`,
  `--k-mad`, `--ventana-local`, `--paso-local`, `--solo-recortes` (escribe los recortes con
  grilla para etiquetar sin armar ningún fondo), `--recorte-radio`, `--recorte-zoom`.
- **Salidas** en `data/incoming/<clip>.kinelab/mascara/` y en `~/Desktop/cortado.kinelab/mascara/`
  (las dos ignoradas por git): `mascara.json`, `etiquetas.json` (a ojo, `estimacion`),
  `fondo-global.png`, `sin-fondo.png`, `palo-{global,local}-<cuadro>.png` con la recta
  ajustada y la etiqueta a ojo dibujadas, `escala-<cuadro>.png` y `recorte-<cuadro>.png`.

### Medido

- **El palo en el top se separa y la recta coincide con lo que se ve.** `cortado3-lento`,
  10 cuadros alrededor del top (1284), fondo local: error de ángulo contra la etiqueta a ojo
  **0,9° de mediana, 1,6° de máximo, 10 de 10 por debajo de 5°**; punta a 37 px,
  perpendicular a 13 px. Con fondo global, 8 de 10 (pierde el 1281 y el 1282).
- **El palo en el impacto no existe en el archivo.** 10 cuadros alrededor de 1364: error
  **66° de mediana** con fondo local, **0 de 8** por debajo de 5°. **A ojo tampoco**: en 2 de
  los 10 cuadros no se distingue ningún shaft y en los otros 8 sólo un tramo pegado a la
  mano. En `vid1` (UHD 60) **no se ve en ninguno de los 5** cuadros.
- **La silueta del cuerpo sale a medias y depende de que el sujeto se corra del lugar**:
  cobertura del bbox **0,378 / 0,422 / 0,182** y keypoints adentro de la máscara **62 % /
  77 % / 27 %** en `cortado3-lento` / `vid1` / `cortado`. El indicador que lo explica es
  **«sin fondo»** —píxeles que ninguna muestra mostró sin el sujeto encima—: **1,93 % · 0,58 %
  · 6,09 %** del cuadro.
- **La escala no mejora**: la extensión vertical de la máscara da **1,165–1,181** contra la
  cadena (913–926 px en cinco cuadros, ±0,7 %) donde de coronilla a suela daría **1,044**. El
  sobrante está abajo, 117–122 px por debajo de los tobillos (26–27 cm), y en `escala-1594.png`
  se ve que **el zapato que no se mueve no entra en la máscara**. En `vid1`, 1,099–1,104.
- **Cuesta** 68 ms/cuadro en FHD y 407 en UHD, más 27–72 s de modelo de fondo **por toma**
  (no se reusa entre tomas: cambia la escena). Corridas completas: 148 s, 287 s y 43 s.
- **Controles**: la ocupación por silueta contra `bbox` contra `bbox-y-palo` da **1,93 % ·
  7,76 % · 10,53 %** de «sin fondo»; el color contra `--gris`, **0,383 / 62 %** contra
  **0,309 / 50 %** de cobertura y keypoints, a cambio de 4× el tiempo del modelo.
- **Suite del motor: 390 pasados, 0 fallados, exit 0** (sin cambios; no se tocó `kinelab/`).

### Qué falta o no se probó

- **La recomendación es no abrir un encargo de producto del shaft como evento**, y está en el
  informe §6 con sus tres líneas. El evento que peor mide el motor es el impacto, y ahí la
  máscara no ve el palo en ninguno de los tres clips.
- **Lo que bloquea el impacto no es visión, es el obturador**, y **nunca se midió**:
  `CAPTURA.md` §Luz calcula 21,2 px de barrido a 1/240 s y pide 1/1000 s, pero ningún clip del
  repo tiene el obturador medido ni declarado. Está propuesto como encargo chico en el informe.
- **La tabla de modelos de segmentación** (informe §5) es de licencias, no de mediciones: dos
  de sus seis filas **no tienen respuesta a la tercera pregunta de ADR-010** (datos de
  entrenamiento). Nada se instaló ni se corrió.
- **No se probó en `down_the_line`** porque no hay ningún clip de esa vista.
- **La máscara fina resta la silueta de la pose** antes de buscar el palo, así que el tramo de
  shaft que pasa por delante del cuerpo se pierde por construcción.
- **`cortado` tiene una segunda persona en cuadro** con su palo visible; no rompió nada acá,
  pero es material que el gate `single_subject` debería mirar.
- No se tocó `kinelab/`, `sports/`, `service/`, `web/`, `truth/`, ningún `analysis.json`,
  ningún `pose.npz` ni ningún umbral del motor. No se instaló nada, no se corrió pose sobre
  cuadros enmascarados, no se estimó el palo desde el antebrazo y no se compensó la deriva en
  ninguna métrica. El prompt no tenía front.

### Desviaciones

- **Del contrato, ninguna.** No entra ni sale ningún campo de ningún schema y ningún valor
  del motor cambia: todo lo que escribe esta sesión vive en `data/incoming/*/mascara/` y en
  `~/Desktop/cortado.kinelab/mascara/`, que git ignora.
- **Del prompt, una: el fondo local.** El prompt pedía «mediana temporal de los cuadros donde
  el sujeto no está». Eso es el fondo **global**, y está hecho; pero el palo en el impacto vive
  encima del propio cuerpo, donde ese modelo no tiene fondo, así que se agregó un segundo
  modelo con una ventana de ±0,5 s **sin** enmascarar. Es la misma mediana con otra ventana,
  no otro algoritmo, y los dos se reportan por separado. Sin él, el fondo global perdía además
  2 de los 10 cuadros del top.

---

## 18 de septiembre de 2026 — encargo 31: el fin del acompañamiento, dentro de su repetición

Prompt: `docs/prompts/31-follow-end-en-su-repeticion.md`. Informe:
`docs/informes/2026-09-18-31-follow-end-en-su-repeticion.md`. **En paralelo con el
32** (que escribe sólo en `banco/` y en `data/incoming/*/`). Commits: `513194c`
(motor, deporte, exploración, front y tests), `6bea1fb` (los tres restos) y el de
cierre, con este archivo y el informe.

### Qué existe ahora

- **`stable_window_start` tiene cota**: `before: int | None`, y la ventana de
  quietud tiene que caber **entera** en `(after, before]` — una racha que arranca
  adentro y sigue después del tope cuenta sólo hasta el tope. `None` = la firma
  anterior.
- **El deporte le pasa el fin de su propio candidato de segmentación** (auditoría
  del 16/9 §6 D-4). No hizo falta cambiar ninguna firma: `detect_golf_events(sig,
  cand, params)` ya recibía el `RepCandidate` entero y `cand.end` estaba ahí. El
  prompt suponía lo contrario («hoy no llega hasta ahí»).
- **`MissingEvent(id, reason)`** en `kinelab/events/primitives.py`: un evento
  ausente **con** su razón, **falso en un booleano** a propósito. En
  `analysis.json` sale `null` —`$defs/event` es `additionalProperties: false`— y
  la razón va a `warnings[]`, como las de ADR-019, con el texto que escribe el
  deporte (el motor no sabe qué umbral se usó: invariante 13).
- **El `method` del `follow_end` dice `stable_window_in_rep`**, porque lo que se
  marca es el **inicio** de la quietud del finish. Qué es el finish para el
  entrenador —llegar a la pose o soltarla, ≈380 ms— sigue sin decidirse, y ahora
  el código lo dice en vez de suponerlo. `settle_forward` también se acota al fin
  de la repetición.
- **`tol_frames` de cada evento llega a `datos-eventos.json`**
  (`eventos_tol_frames`) **y a la tabla por evento** de la pantalla, al lado del
  cuadro: «cuadro 722 · 12,028 s · ± 4 cuadros». Si el motor no la mandó (trabajo
  anterior a hoy) no se muestra nada: no se inventa el ±1 fijo que la auditoría
  marcó como falso.
- **Una sola señal de manos**: `per_frame_table` recibe el `wrist_score_min` del
  deporte, así que el CSV, el overlay y los eventos salen de la misma. El default
  sigue en 0,0 —la firma vieja, que usa `truth/`, que no tiene deporte—.
- **Tres restos cerrados**: `kinelab/events/order.py` dado de baja (huérfano desde
  ADR-018, nadie lo importaba); el docstring de `kinelab/ingest/gate.py` dice la
  verdad sobre los chequeos de la Fase 1 (existen desde el 17 y los escribe
  `perception/run.py`); y una nota fechada bajo ADR-019 con la deriva en y medida
  por el 29.

### Medido

- **Antes → después, desde el `pose.npz` guardado** (invariante 1, el modelo no se
  volvió a correr): `cortado3-lento` / `take-01` rep 1 **1978 → `null`** y
  `follow_duration_ms` **2556,7 ms → `null`**; **`vid1` 931 → `null`**, que es el
  mismo bug y **no estaba en la auditoría**; `20260907_170638` conserva **188**;
  `cortado`, `vid2` y `cortado3` rep 2 ya eran `null`.
- **Address, top e impacto no se movieron ni un cuadro en ningún clip.** En
  `take-01` la única métrica que cambió es `follow_duration_ms`: `scale_px` sigue
  en **783,9 px del cuadro 1594** y las ocho métricas en cm quedaron idénticas,
  aunque el `frame_end` de la rep 1 bajó de 1978 a 1765.
- **Por qué `cortado3` rep 1 da `null`**: entre el impacto (1364) y el fin del
  candidato (1765) la única racha de quietud es 1507–1566, **60 cuadros** a 240,15
  fps contra los **72** que pide `follow_still_s`. La que el motor elegía antes
  empieza en **1947**: es el address de la rep 2 (2322). Rep 2: racha 2790–2844,
  **55 cuadros**.
- **Por qué `vid1`**: impacto 741, candidato hasta **834**, y la primera quietud de
  18 cuadros empieza en **929** — adentro del candidato **siguiente** (773–983),
  que el motor había descartado como repetición.
- **Punto 3, cuántos cuadros del CSV cambian**: los que tienen al menos una muñeca
  bajo 0,55, que son exactamente los que cambian de posición de manos —
  **22** de 76 (`cortado`) · **84** de 265 (`20260907_170638`) · **39** de 1066
  (`vid1`) · **7** de 292 (`vid2`) · **109** de 2977 (`cortado3` y `take-01`)—, con
  corrimientos de hasta **126,4 px**. La velocidad filtrada cambia numéricamente en
  casi todos los cuadros (el Butterworth con `filtfilt` no es causal) y supera el
  1 % del pico en 32 / 81 / 66 / 18 / 155.
- **Suites: motor 390 pasados, 0 fallados, exit 0** (eran 381: +9 tests, ninguna
  aserción existente tocada). Arnés **43 pasados, 0 fallados, exit 0**. `cd web &&
  pnpm lint && pnpm build` en verde.
- **Mutación manual: 6 bugs inyectados, 6 en rojo, control en verde.** `before`
  ignorado en la primitiva → 2 tests; el deporte sin pasar la cota → 2;
  `MissingEvent` verdadero en un booleano → 4; `per_frame_table` ignorando el
  umbral → 1; `datos-eventos.json` sin `eventos_tol_frames` → 1; `settle_forward`
  sin acotar → 1. Ese último no lo agarraba nada y se le escribió su test: con
  `refine_s` 0,15 s contra `follow_still_s` 0,3 s el límite nunca llega a morder,
  así que el caso se construye con la velocidad a mano.

### Qué falta o no se probó

- **En cuatro de los cinco clips reales no hay `follow_end`** —sólo lo tiene
  `20260907_170638`—, así que `follow_duration_ms` no se mide en ninguna toma del
  repo. Antes había un número en dos de ellas y era falso. Lo que lo desbloquea es
  la **definición del finish**, que decide Hernán, no un umbral.
- **`follow_still_s`, `still_speed_max` y `wrist_score_min` no se tocaron** (lo
  prohibía el prompt, y con n = 1 corresponde). La pausa del finish mide 60 y 55
  cuadros contra los 72 que pide el umbral: con la sesión de validación filmada
  habrá con qué decidir si 0,3 s es el número.
- **La razón del hueco no viaja en el evento**, porque `$defs/event` es
  `additionalProperties: false`: va a `warnings[]`. Ponerla pegada al evento en la
  pantalla pide un campo nuevo en el schema y un bump; el prompt lo prohibía.
- **El front no se abrió** (regla de trabajo): lo prueba Hernán, con la lista del
  informe. Los trabajos que ya están en `data/exploracion/` son anteriores y no
  traen `eventos_tol_frames`; hay que subir uno nuevo para ver la columna.
- No se tocó `kinelab/metrics/`, `sports/golf/metrics.py`, el schema, `service/`,
  `truth/`, ningún umbral, ni se re-corrió percepción sobre ninguna toma.

### Desviaciones

- **Del contrato, ninguna.** No entra ni sale ningún campo de ningún schema;
  `analysis.json` sigue en 2.0.0 y `eventos_tol_frames` es de
  `datos-eventos.json`, que el contrato no describe. Lo único que cambia de valor
  es `follow_duration_ms`, que pasa a `null` donde el número era falso.
- **Del prompt, una.** Decía que el fin del candidato «hoy no llega» al detector y
  pedía llevarlo por `GolfEventParams` o por la firma. Ya llegaba (`cand.end`), así
  que no se cambió ninguna firma. Queda dicho acá y en el informe.

---

## 18 de septiembre de 2026 — encargo 29: la deriva de cámara, medida

Prompt: `docs/prompts/29-deriva-de-camara-censo.md`. Informe:
`docs/informes/2026-09-18-29-deriva-de-camara-censo.md`. **Sin sesión en paralelo**
(lo pedía el prompt). Commits: `83c152f` (la herramienta y sus tests) y el de
cierre, con este archivo y el informe.

### Qué existe ahora

- **`kinelab/tools/camera_drift.py`** (nuevo): mide cuánto se corre la imagen
  durante el gesto y **no compensa nada**. Homografía del fondo entre un cuadro
  de referencia y cada cuadro muestreado — SIFT con el sujeto enmascarado
  (`bbox` de `pose.npz` dilatado 20 % más un disco sobre las muñecas de radio
  0,65 altos de cuerpo, que cubre el palo), ratio test de Lowe y RANSAC —,
  evaluada en **cuatro filas** de la imagen: caderas, hombros, cabeza y pies del
  cuadro de referencia, sobre la columna del sujeto. Cuatro y no una está
  medido: en `cortado3-lento` hay 8,7 px entre la fila de la cabeza y la de los
  pies en el mismo cuadro.
- **Escribe `camera-drift.json` al lado de la pose y nada más.** No toca
  `analysis.json` ni `pose.npz` (hay un test que lo verifica por bytes), ninguna
  métrica lo lee, y **`camera_motion_px` no se cambió**. Agnóstica al deporte:
  de `analysis.json`, si está, sólo lee los cuadros de `address`, `top` e
  `impact`, que son nombres del contrato.
- **`no_rigido` mira dos condiciones y no una**: `residuo_px > 1,5` (mediana del
  error de reproyección de los inliers) **o** `inliers_frac < 0,80`, las dos
  procedencia `estimacion`, y `no_rigido_por` dice cuál fue. El residuo solo no
  sirve —RANSAC lo acota por construcción—: medido, una deformación no rígida lo
  sube de 0,00 a 1,98 px mientras la fracción de inliers cae de 1,00 a 0,76.
- **Controles por CLI**: `--region superior|inferior`, `--sin-palo`,
  `--dilatacion`, `--palo-radio`, `--ref`, y `--dibujar FRAME`, que escribe el
  cuadro con el fondo enmascarado a la vista y los inliers dibujados.
- **`tests/test_camera_drift.py`** (nuevo, 18 tests), todo contra
  transformaciones construidas en el propio test.
- **`data/incoming/cartado2-lenta.kinelab/`**: se corrió `datos` porque era el
  único clip sin pose. 292 cuadros, 462 px de cuerpo, **sin eventos** (es el
  clip del cronómetro detenido).

### Medido

- **Contra la auditoría del 16/9, en `cortado3-lento.mp4`: aceptado en x.**
  Rep 1 **+13,5 a +22,2 px** contra su rango +14 a +23 (el mínimo queda 0,5 px
  afuera, dentro de los ±3 px de aceptación); rep 2 **−10,1 a −22,1 px** contra
  −8 a −25, entero adentro.
- **La y de la auditoría se queda corta por un factor 2,5–3.** Dice «unos 10 px»
  y son **−26,3 a −29,8 px** en el impacto de la rep 1: con `scale_px` 783,9 y
  1,75 m, **5,9–6,7 cm**, o sea **2,1–2,4× el MDC** de `pelvis_lift_top_cm`
  (2,769). En x, 3,4–5,0 cm contra el MDC 2,416 de `pelvis_sway_impact_cm`.
  `quality.camera_motion_px` de esa misma toma sigue dando **1,347**.
- **Censo de los 9** (`--cada 10`, por defecto): `cortado` ±5,2 px (76 cuadros,
  el más quieto) · `cartado2-lenta` 10,2 · `Cortado-lenta` 21,7 · `vid3` 23,4 ·
  `cortado3-lento` y `take-01` 43,1 (idénticos, como corresponde: misma pose) ·
  `vid2` 46,3 · `20260907_170638` 135,0 · `vid1` **119,4 en y** con 366–1058
  inliers y residuo 0,27–0,67 px, o sea cámara y no artefacto. Residuo mediano
  0,24–0,42 px y 162–954 inliers en los nueve. **`no_rigido`: 1 cuadro en 9
  clips** (`20260907_170638` 260, final del clip). 2–56 s por clip.
- **Control (a), mitad superior contra inferior**: en la rep 1 las tres variantes
  coinciden dentro de 0,7 px; **en la rep 2 la superior da −2,1 donde `todo` da
  −19,3**. No alcanza para concluir paralaje: la superior tiene 53 inliers
  contra 121, falla en 67 de 304 cuadros, y evaluarla en la fila de los pies es
  extrapolar ~800 px fuera de su soporte (su `max |dy|` da +904,7 px). Lo que sí
  queda dicho: **el número de `todo` es el de la mitad inferior** — la deriva
  que se reporta es la del suelo, no la del fondo lejano.
- **Control (b), la máscara no deja pasar al sujeto**: con las manos 6,8× más
  rápidas en el downswing que en el address, el residuo contra una recta pasa de
  0,10 a 0,23 px en x. Apagar el disco del palo mueve la deriva ≤ 0,81 px;
  agrandar la máscara a 33 % de fondo libre (21 inliers) agrega ±5 px de
  dispersión, que es acondicionamiento y no fuga.
- **Control extra: el cuadro de referencia no manda.** Con `--ref 1052` en vez
  del 0, los ocho números de eventos cambian ≤ 0,4 px, y la resta no cancela
  nada por construcción.
- **Suites: motor 381 pasados, 0 fallados, exit 0** (eran 363: +18 tests,
  ninguna aserción existente tocada). Arnés **43 pasados, 0 fallados, exit 0**
  —no se tocó `truth/`—.
- **Mutación manual: 7 bugs inyectados, 7 en rojo, control en verde.** Máscara
  invertida → 9 tests; homografía en la fila equivocada → 5; homografía al revés
  → 6; `dx`/`dy` intercambiados → 5; `no_rigido` sólo por residuo → 2; resta de
  eventos vuelta suma → 1; disco del palo sin dibujar → 1. Los dos últimos
  taparon huecos que la mutación encontró: con el `address` sintético **en** el
  cuadro de referencia su deriva era cero y restar o sumar daba lo mismo, y el
  disco del palo no lo defendía ningún test de resultado (apagarlo mueve ≤ 0,81
  px), así que se le escribió un test de geometría.

### Qué falta o no se probó

- **La causa no está separada**, que era el objetivo del control (a): falta
  fondo lejano utilizable. Para la sesión de validación conviene agregarle a
  `docs/filmacion-s22.md` §7 **un objeto fijo alto**, no sólo el del suelo, o la
  mitad superior va a seguir sin tener con qué.
- **El residuo no rígido de 10–12 px de la auditoría no aparece**: con el sujeto
  enmascarado una sola homografía ajusta el fondo con 0,39 px de mediana sobre
  162 inliers.
- **`quality.camera_motion_px` sigue como estaba** (lo prohibía el prompt). No
  miente, mide otra cosa; lo que engaña es el nombre. La propuesta —renombrarlo
  a `camera_jitter_px` en el mismo bump 2.2.0 que traiga el campo de deriva— es
  **major** por §Versionado y está en el informe, para el orquestador.
- **`ESPECIFICACION.md`, `CONTRATO.md` y `CAPTURA.md` no se tocaron**: el
  encargo era medir, y meter la deriva en el contrato tiene encargo propio.
- **El `--cada 10` por defecto** sobre 2977 cuadros son 304 muestras y 33 s; el
  análisis fino del control (b) usó 2 y 4. No se propuso cambiar el default.
- No se tocó `kinelab/perception/`, `kinelab/analysis.py`, `kinelab/metrics/`,
  `sports/`, `service/`, `web/`, `truth/`, ningún `analysis.json` ni ningún
  umbral. **No se compensó nada en ninguna métrica**, y el modelo de pose no se
  volvió a correr salvo en `cartado2-lenta.mp4`, que no tenía (lo autorizaba el
  prompt). El front no se abrió (regla de trabajo).

### Desviaciones

- **Del contrato, ninguna.** No entra ni sale ningún campo de ningún schema,
  ningún valor cambia y `camera-drift.json` es un archivo nuevo que el contrato
  no describe y que ninguna métrica lee.
- **Del prompt, una.** Pedía «una bandera `no_rigido` cuando el residuo supera
  un umbral parametrizado». El residuo de los inliers no sirve solo para eso
  —RANSAC lo acota por construcción, y está medido— así que se lo dejó como
  primera condición, como pedía el prompt, y se le sumó la fracción de inliers,
  que es la que separa. Las dos son `estimacion` y las dos se cambian por CLI.

---

## 18 de septiembre de 2026 — encargo 30: el exit 134 era la telemetría de onnxruntime

Prompt: `docs/prompts/30-exit-134-del-arnes.md`. Informe:
`docs/informes/2026-09-18-30-exit-134-del-arnes.md`. **Sin sesión en paralelo**
(lo pedía el prompt). Commits: el del código y documentos, y el de cierre con
este archivo y el informe. El del código: `db46aa4`.

### Qué existe ahora

- **El aborto al salir tiene causa, y no era ninguna de las tres que suponía el
  prompt.** No es la sesión de CoreML viva, ni una carga ansiosa del paquete, ni
  algo del arnés: es la **telemetría de onnxruntime 1.30**, que desde esa
  versión existe también en macOS (`core/platform/posix/telemetry.cc`, con el SDK
  1DS de Microsoft adentro de `onnxruntime_pybind11_state.so`). Su hilo de subida
  despacha un evento cuando el intérprete ya corrió los destructores estáticos y
  el `recursive_mutex` del despachador ya no existe → `libc++abi`, SIGABRT, exit
  134, siempre **después** de que el trabajo quedó escrito. Los **23** informes
  de macOS del proyecto (12/9 al 18/9) tienen todos **la misma pila**.
- **`kinelab/perception/__init__.py` pone `ORT_DISABLE_TELEMETRY` antes de que
  onnxruntime se cargue.** Importar cualquier módulo del paquete ejecuta primero
  ese `__init__`, así que llega siempre a tiempo; y el `__init__` sigue sin
  importar nada (no trae onnxruntime ni los pesos). Sin telemetría no hay hilo, y
  sin hilo esa pila es imposible. No se tapó nada: no hay `os._exit` ni se ignora
  ningún exit code.
- **`truth/tests/conftest.py`** (nuevo): importa `kinelab.perception` antes que
  cualquier test del arnés. Hoy es red de seguridad —los tests ya lo importan por
  otro camino, medido— y no una segunda copia de la razón, que vive en un solo
  lugar.
- **`truth/corridas.sh N`** (nuevo, default 10): corre N veces la suite del
  arnés, imprime el exit de cada una y falla si alguna no da 0. Está en
  `AGENTS.md` §Comandos, y la causa en §Cosas que muerden.
- **Dos tests nuevos del motor que miran lo que los otros no pueden**:
  `test_datos_en_un_subproceso_termina_con_exit_0` (el exit del **proceso**, con
  onnxruntime de verdad; los tests de `explore` corren en el mismo intérprete y
  el aborto es posterior a todo) y
  `test_importar_kinelab_perception_apaga_la_telemetria_de_onnxruntime`.
- **Punto 3a del prompt, decisión del orquestador:** `run_perception` ya no mira
  el veredicto entero del `capture.json` sino **sólo los chequeos de ingesta**
  (`_blocking_checks` en `kinelab/perception/run.py`); los tres de la Fase 1 los
  escribe esa misma función en ese mismo archivo y se rehacen en cada corrida.
  Una toma rechazada por encuadre se vuelve a correr con `--overwrite`.
- **Punto 3b:** `ARRANQUE.md:64` dice ahora que el umbral de encuadre se fijó
  midiendo (717 px, `body_height_px_min`), con el texto del informe del 17.

### Medido

- **Diagnóstico, diez corridas de cada comando antes de tocar nada.** Aborta
  **7 de 10** `cd truth && .venv/bin/pytest` (`0 134 0 134 134 134 0 134 134
  134`), con 43 pasados en las diez. **Cero** abortos en: `datos` (0 ×10),
  `kinelab.perception` (2 ×10), `service` con SIGINT sin trabajos y con un
  trabajo listo (0 ×10 cada uno), `import kinelab.perception`, `import
  onnxruntime`, `import cv2`, sesión CoreML creada y no usada, y sesión CoreML +
  inferencia viva al salir (0 ×10 cada uno). Ningún archivo de `truth/tests`
  aborta solo; la combinación de cuatro abortó 3 de 6.
- **Que es la telemetría, con `HOME` aislado**: `import onnxruntime` **crea** su
  almacén (`…/Microsoft/DeveloperTools/.onnxruntime/` con `deviceid` y
  `onnxruntime.db`); con `import kinelab.perception` antes, **no lo crea**, ni
  con sesión ni con `PoseEstimator`. Sobre el `HOME` real: una corrida del arnés
  sin el arreglo suma **3 eventos** a la cola (844 → 847), con el arreglo suma
  **0** y no toca el archivo. Había **847 eventos en cola** desde el 12/9 y
  bajaron a 295 durante las pruebas: **se están subiendo**.
- **Después del arreglo**: `truth/corridas.sh 10` → 10 de 10 exit 0. `datos` 0
  ×10, `kinelab.perception --overwrite` diez veces sobre el mismo take → 2 ×10
  (ninguna vez 1 ni 134), `service` 0 ×10 y 0 ×10, imports y sesiones 0 ×10.
- **El 3a sobre material real**, en una copia de la toma de `cortado3-lento`
  (2977 cuadros, para no re-correr la definitiva): la regla vieja de HEAD levanta
  `PerceptionError` sobre el `capture.json` ya rechazado; la nueva **corre** (40 s,
  `exit 2`, 691 px contra 717) y **reescribe** el chequeo, sin duplicarlo. Lo que
  bloquea sigue bloqueando: con `vfr_ratio_le_1_10` en `false` se niega.
- **Suites: motor 363 pasados, 0 fallados, exit 0** (eran 360: +3 tests, ninguna
  aserción tocada). Arnés **43 pasados, 0 fallados, exit 0** — y ahora en las 10
  corridas, que es como se lee.
- **Mutación manual: 4 en rojo y 1 control en verde.** Sin la variable → 1 rojo;
  `_blocking_checks` con la regla vieja → 1; sin bloquear nunca → 2; el
  subproceso apuntado a un video que no existe → 1. `truth/corridas.sh 2` con un
  test del arnés roto a propósito → exit 1 en las dos. Control: sin
  `truth/tests/conftest.py` la suite sigue en verde y la variable sigue en `'1'`.

### Qué falta o no se probó

- **No hay reproductor a pedido del aborto.** Se reproducía a las 13:02 (7 de 10)
  y dejó de hacerlo a las 13:11, **con o sin el arreglo**: sacándolo a mano a las
  14:05 dio 10 de 10 exit 0, y con la telemetría en frío (`HOME` nuevo), 6 de 6.
  Así que el antes/después estadístico es 7 de 10 → nada que comparar. Lo que
  vale es la medición determinista: sin telemetría no existe el hilo de la pila.
  Probable causa del silencio: la cola de eventos bajó de 847 a 295 mientras se
  subían, y el aborto ocurre al decodificar una **respuesta**.
- **La carpeta de telemetría de Microsoft** (295 eventos y un `deviceid` de esta
  Mac) sigue donde estaba, fuera del repo. No se borró: es decisión de Hernán.
- **`kinelab/ingest/gate.py` tiene un docstring hoy falso** («los chequeos de la
  Fase 1 todavía no existen»), y es donde debería vivir un `INGEST_CHECK_IDS` con
  los nueve del contrato; `run.py` los toma por el complemento de
  `framing.CHECK_IDS`. No era archivo de este encargo.
- **`kinelab/analysis.py:271` sigue negándose a analizar una toma con el gate en
  `reject`**: una toma rechazada por encuadre se re-corre por percepción pero no
  se analiza. Estaba en el NO del prompt.
- **El `capture.json` de la toma de `data/sessions/` todavía trae el id viejo
  `body_height_frac` con `passed: null`**, de antes del 17. No molesta y se va al
  re-correr percepción, que la auditoría pidió no hacer sobre esa toma.
- No se tocó `kinelab/explore.py`, `service/exploracion.py` ni
  `service/__main__.py`, ni ningún umbral, ni `sports/`, `web/`,
  `kinelab/metrics/`, `kinelab/events/`, `kinelab/analysis.py` ni
  `kinelab/perception/framing.py`. **No cambió ningún número de ninguna
  corrida.** El front no se abrió (regla de trabajo).

### Desviaciones

- **Del contrato, ninguna.** Ningún campo entró ni salió de ningún schema y
  ningún valor cambió. Los nueve chequeos de ingesta de `CONTRATO.md`
  §capture.json siguen siendo los mismos; lo único que cambió es cuáles de ellos
  deciden si la percepción arranca.
- **Del prompt, una, y es la principal.** El punto 2 pedía el arreglo bajo tres
  hipótesis («si es la sesión viva al salir…», «si el paquete carga el estimador
  al importar…», «si el arnés queda con algo vivo…»). Las tres están medidas y
  las tres son falsas: la causa es la telemetría de onnxruntime. Por eso **no** se
  agregó `close()`, ni `del` de la sesión, ni `atexit`: no arreglan nada y serían
  ruido. Sí se respetó lo que el prompt prohíbe — nada de `os._exit`, ningún exit
  code ignorado, el aborto no se escondió.

---

## 18 de septiembre de 2026 — encargo 17: el umbral de encuadre, en píxeles

Prompt: `docs/prompts/17-gate-encuadre-en-px.md`. Informe:
`docs/informes/2026-09-18-17-gate-encuadre-en-px.md`. **Sin sesión en paralelo**
(lo pedía el prompt: este encargo edita `kinelab/` y corre el motor sobre
material real). Commits: `6bae365` (código y documentos) y el de cierre, con este
archivo y el informe.

### Qué existe ahora

- **El chequeo de encuadre tiene umbral por primera vez desde la Fase 1**, y son
  **píxeles de cuerpo**, no fracción del cuadro:
  `PerceptionGates.body_height_frac_min` → **`body_height_px_min`**
  (`kinelab/sport.py`), validado `> 0` en vez del rango `(0, 1]`, y
  `sports/golf/config.py` lo instancia en **717**. Procedencia `estimacion`:
  arnés de **nivel 0**, sin estimador de pose, σ = 4,866 px, donde
  `head_lift_top_cm` cruza su tolerancia de 5 cm (informe del 13 §3; le siguen
  `head_sway_top_cm` a 608 y `thorax_sway_top_cm` a 552).
- **El chequeo se llama `body_height_px`** (`kinelab/perception/framing.py`, y en
  `CHECK_IDS`). `value` = mediana redondeada, `expected` = el umbral, y **la
  fracción del cuadro va dentro de `reason`, también cuando pasa**, porque
  `Check` no admite campos extra. Frase al fallar: «*El jugador mide N px de alto
  en el cuadro y hacen falta 717: acercá el trípode. Son el M % del alto del
  cuadro.*» Se borró `_finite_or_none`, que quedó sin uso.
- **`CAPTURA.md`**: la fila del gate, el párrafo del umbral en §Encuadre con
  procedencia y las dos cuentas del S22 (717 px = **37,3 % de 1920** en *Slow
  motion* FHD 240, **30,9 % de 2320** en *Video* FHD), la columna «¿pasa los 717
  px?» en la serie de seis clips, y las fracciones de `vid1` y `vid2`
  desinvertidas (lo medido es **vid1 28,7 % · vid2 28,2 % · vid3 29,5 %**).
  También se corrigió, con fecha, la afirmación «*un clip de este teléfono puede
  pasar el gate entero*», que este cambio volvió falsa.
- **`docs/filmacion-s22.md` §7 «La sesión de validación»**, nueva: trípode con
  peso y sin tocar, toda estabilización apagada, un objeto chico y contrastado
  fijo en el suelo, 25 s de escena vacía al armar cada vista, 2 s de pie derecho
  al empezar cada toma, el cuerpo por encima del **37,3 %**, 25 s por toma en
  todas, 10–20 swings por vista con pelota (la mitad sosteniendo la pose final
  1–2 s), palo y altura declarados bien, y los originales de `DCIM/Camera` por
  cable más un recorte de la Mac y **una toma por WhatsApp como video que tiene
  que salir rechazada**. El §2 quedó reconciliado con la decisión del
  orquestador del 18/9: **el cronómetro va en la primera toma de cada vista y en
  la de la escena vacía, no en cada toma**, porque calibra el camino del teléfono
  y no el video; y está escrito que con el camino medido nadie más necesita
  cronómetro. El repaso final pasó a §8.

### Medido

- **Corrida real sobre `cortado3-lento.mp4`** en un `--data` de scratch: la
  ingesta da **exit 0 · 9 de 9 · `gate: OK`**; la percepción da **exit 2 ·
  `gate: RECHAZADO` · 11 de 12**, con `body_height_px` fallando **691 contra
  717**. Es el resultado esperado: 26 px, medio paso de trípode.
- **Los siete clips del repo, de sus reportes ya escritos, sin correr nada**:
  pasan `vid3` 1132 px, `vid1` 1104, `vid2` 1083, `20260907_170638` 973 y
  `cortado` 869; **no pasan** `cortado3-lento` 691 y `Cortado-lenta` 414. Los
  cinco que pasan el encuadre se rechazan igual por `fps_min_for_gesture`; el
  único que llega al fps es el que no pasa el encuadre. **Ningún clip del repo
  pasa el gate completo.** Y la fracción engañaba: ordenarlos por fracción da un
  orden distinto que por píxeles en **9 de los 21 pares**.
- **El modo exploración no bloquea** y suma la frase a sus avisos, como se
  esperaba: `datos` sobre `Cortado-lenta.mp4` sigue calculando todo y agrega
  «*el gate diría: El jugador mide 413 px de alto… y hacen falta 717*».
- **Suites: motor 360 pasados, 0 fallados, exit 0** (eran 357: +3 tests, 2
  adaptados). Arnés **43 pasados, 0 fallados, exit 134** — el aborto
  intermitente del encargo 30; no se tocó `truth/`.
- **Mutación manual: 9 de 9 en rojo.** Dos de ellas (el valor desde el mínimo en
  vez de la mediana, y el id viejo en la rama que pasa) **pasaron en verde en la
  primera vuelta** y señalaban huecos de los tests: se agregó un clip sintético
  con un tramo sostenido más chico (mediana 900, mínimo 600, tiene que pasar) y
  la aserción del id en las cuatro ramas.
- `rg body_height_frac` en `kinelab/`, `sports/`, `tests/`, `truth/`,
  `service/`, `web/src/` y los seis documentos base: **cero**.

### Qué falta o no se probó

- **Una toma rechazada por encuadre no se puede volver a correr.** `run.py:74` se
  niega a correr pose sobre un gate en `reject`, y la Fase 1 escribe su propio
  rechazo en ese mismo `capture.json`: `python -m kinelab.perception TAKE
  --overwrite` sale con `exit 1` citando la razón que escribió la corrida
  anterior. Antes no pasaba porque el chequeo salía `passed: null`. Medido.
  `run.py` no era archivo de este encargo; la decisión es del orquestador.
- **El valor del chequeo depende del `fps_real` del camino declarado**: la
  mediana móvil de `body_height_px` es de 1 segundo, o sea `1,0 × fps` cuadros.
  `Cortado-lenta` da **414,1 px** con el camino calibrado (240,15 fps) y
  **412,8 px** con `desconocido-video` (30,017). Son 1,2 px; acá no cambia
  ningún veredicto, pero un clip a 2 px del umbral sí puede pasar o no según con
  qué camino se lo declare.
- **`ARRANQUE.md:64`** quedó con el nombre viejo y con una afirmación hoy falsa
  («el umbral exacto de `body_height_frac` está sin fijar a propósito»). No es
  archivo de este encargo; el texto de reemplazo está en el informe.
- **`web/public/demo/…/capture.json`** todavía trae el id `body_height_frac`: es
  un dato publicado, se rehace al regenerar la demo.
- No se tocó `kinelab/ingest/gate.py`, `sports/golf/mdc.yaml`,
  `kinelab/perception/run.py`, `kinelab/explore.py`, `service/`, `web/`,
  `truth/`, `data/capture-paths.yaml` ni la toma de `data/sessions/`. **El 717
  no se movió.** El front no se abrió (regla de trabajo).

### Desviaciones

- **Del contrato, ninguna.** El id del chequeo no aparece en `CONTRATO.md` —la
  lista de §capture.json son los nueve chequeos de ingesta; los de la Fase 1 se
  suman después y el contrato no los enumera—, así que no hubo qué poner al día.
  Ningún campo entró ni salió de ningún schema.
- **Del prompt, una hacia arriba.** Además del renombre que pedía, se corrigió
  en `CAPTURA.md` §Lo que queda por verificar la afirmación de que
  `cortado3-lento` pasa el gate entero: con el 717 puesto deja de ser cierta, y
  un documento que dice algo falso es exactamente lo que este proyecto no hace.

---

## 18 de septiembre de 2026 — encargo 28: la pantalla deja de decir cosas falsas

Prompt: `docs/prompts/28-pantalla-sin-falsedades.md`. Informe:
`docs/informes/2026-09-18-28-pantalla-sin-falsedades.md`. Corrió en paralelo con
el **27**, que toca `kinelab/`, `sports/`, los documentos base, `pyproject.toml`,
`tests/` y `data/examples/`. **Esta sesión tocó sólo `web/src/`**, más este
archivo y su informe. No se corrió `pytest`: el motor estaba a medio escribir en
el árbol de la otra sesión, y correrlo habría dado números de un código que no
es HEAD (es la regla de la auditoría del 16). Ningún archivo de `kinelab/`,
`sports/`, `service/`, `truth/`, `data/exploracion/` ni `web/public/demo/` se
tocó, y no se desplegó nada. Commit del código: `9107e5b`.

### Qué existe ahora

- **`web/src/lib/retirados.ts`**, el único lugar con las claves que ADR-018
  retiró: `hip_line_rate_deg_s`, `shoulder_line_rate_deg_s`,
  `arm_left_rate_deg_s`, más `gain` y `sequence_order`, que hoy no aparecen en
  ningún dato y están para que no aparezcan si alguien los vuelve a agregar.
  Exporta `esRetirado`, `sinRetirados`, `retiradosEn`, y también
  `contratoAnterior` / `CONTRATO_VIGENTE` ("2.0.0"), que es la otra pregunta del
  mismo tipo: qué de este archivo ya no vale.
- **Se aplica en los tres lugares**: la tabla de picos y el desplegable «Todas
  las variables en cada evento» (`TablaEventos.tsx`) y las columnas del CSV
  (`TablaCuadros.tsx`, que además cuenta las que muestra y no las del archivo).
  **No se oculta lo desconocido**: lo que el motor mide y la pantalla no sabe
  nombrar sigue saliendo con su identificador (encargo 01).
- **La banda de cada métrica es `uncertainty.method`**, la frase del motor
  (`kinelab/metrics/core.py:241`), en vez del «±1 cuadro:» fijo que tenía
  `Metricas.tsx:42`. Sin `method` va el rango sin rótulo: no se inventa uno. Y
  con `judgment_allowed: true` la pantalla dice «juicio habilitado
  (judgment_allowed)»; la frase «se puede comparar», que prometía una
  comparación que la pantalla no hace, no existe más.
- **Los avisos son `analysis.warnings` entero, en orden y tal cual.** `Avisos.tsx`
  ya no muestra `aviso`, `fps_aviso` ni `gate_diria` de `datos-eventos.json`,
  que son copias de entradas de esa misma lista: las reemplaza. `fps_note`, que
  viene de `capture.json` y no está en `warnings`, queda como estaba. Sin
  `analysis.json` —y mientras se está bajando— queda el comportamiento de hoy,
  que es un subconjunto: en el peor caso se ve de menos por un instante, nunca
  un número sin su aviso.
- **`analysis.json` se baja en `page.tsx`**, no en `Metricas.tsx`, que va abajo
  de todo: los avisos de arriba lo necesitan. Una sola lectura, guardada con su
  URL al lado para que la respuesta de un trabajo anterior nunca se aplique al
  que se está viendo. `Metricas` pasó a recibirlo por prop.
- **Dos líneas nuevas arriba del resultado**, separadas de lo que escribe el
  motor porque las compone la pantalla y hablan de la pantalla: que el trabajo se
  calculó con un contrato anterior (con las dos versiones y que se corrige
  re-analizando) y que trae campos que ya no son una medición y no se muestran,
  con sus nombres.
- **El ± del sub-cuadro tiene nombre: «precisión interna del cruce».** En
  `page.tsx` (el instante del impacto) y en `textoSubcuadro` de `etiquetas.ts`,
  que es lo que se ve también en las fotos por evento y en la cabecera de la
  tabla. Con una línea al lado que dice qué es y qué no: no incluye el sesgo
  contra el contacto con la pelota, que no está medido. **Sin números**: el
  único que existe salió de un informe, no del motor.
- **`web/src/lib/retirados.verificar.mjs`**, verificador sin framework de tests
  (ADR-015), con el patrón de `pose3d.verificar.mjs`:
  `cd web && node --experimental-strip-types src/lib/retirados.verificar.mjs`.

### Medido

- **Verificador: exit 0, 0 fallas.** Sobre los tres trabajos de la demo, el
  filtro saca **exactamente** las tres `*_rate_deg_s` y ninguna otra, en las tres
  fuentes: `columnas` de `datos-eventos.json`, `picos`, y el encabezado de
  `datos-por-cuadro.csv`. vid1 109 → 106 columnas, los dos del mocap 118 → 115;
  picos 4 → 1 y 5 → 2. Los números que dejan de verse: `hip_line_rate_deg_s`
  **3662,0** · 4202,5 · 3243,74; `shoulder_line_rate_deg_s` 2228,31 · 2307,46 ·
  453,07; `arm_left_rate_deg_s` 1026,43 · 3694,02 · 532,56. La lista esperada
  está escrita a mano en el verificador desde ADR-018: comparar el módulo contra
  sí mismo no comprueba nada.
- **Control del otro lado**: `data/incoming/vid1.kinelab` (2.0.0, re-analizado
  con HEAD) pierde **0 de 115** columnas y 0 de 2 picos, y
  `data/examples/analysis.example.json` (2.0.0) no saca el aviso de contrato
  anterior. Los tres de la demo sí: son 1.2.0.
- **Mutación manual: 7 de 7 ponen el verificador en rojo** (sacar una clave de
  la lista, agregar una que no es de ADR-018, `sinRetirados` que no filtra,
  `retiradosEn` vacío, `contratoAnterior` siempre falso, con el `<` al revés, y
  `CONTRATO_VIGENTE` en 1.0.0), con 3 a 12 fallas cada una. Restaurado, vuelve a
  0.
- **Ninguna frase se repite en los tres trabajos.** vid1 pasa de 3 a 4 frases
  arriba, y la que gana estaba en `analysis.warnings` y no en ninguna de las tres
  copias: «Sin altura declarada del atleta: las métricas en cm quedan en null…».
  Los dos del mocap quedan en 3 y 3. Las tres copias de `datos-eventos.json`
  están todas adentro de `analysis.warnings` en los tres: reemplazarlas no pierde
  nada.
- **Grep sobre los chunks del build de demo, antes y después.** Antes:
  `grep -rl '1 cuadro: '` y `grep -rl 'se puede comparar'` encuentran
  `out/_next/static/chunks/app/page-88a59fb9ab051a85.js`. Después: **nada, las
  dos** (exit 1). Y las frases nuevas sí están en el chunk nuevo
  (`page-aaa6c870f51f5f04.js`), buscándolas con el `\xf3` con el que el
  compilador escribe la «ó». En `web/out/demo/` los `analysis.json` siguen
  diciendo «±1 cuadro en cada evento ancla…» en `uncertainty.method`: es dato del
  motor y es lo que la pantalla ahora muestra.
- **`pnpm lint` exit 0 · `pnpm build` exit 0 · `NEXT_PUBLIC_KINELAB_MODO=demo
  pnpm build` exit 0.**

### Qué falta o no se probó

- **La demo no se regeneró y no se desplegó**, por diseño: el arreglo es sólo de
  código. El comando de un solo tirón está en el informe. `armar_salida` y
  `raiz_repo` existen con esos nombres en `kinelab/tools/publicar.py` (:238
  y :150).
- **`data/publicados.json` marca los tres trabajos con `despliegue: null`** y
  `despliegue_null_reason` «--solo-construir». El sitio vivo existe igual: lo
  desplegó el orquestador a mano el 15/9. El registro no lo sabe.
- **En la demo la banda de `tempo_ratio` de vid1 va a seguir diciendo ±1
  cuadro**, porque es lo que dice su `uncertainty.method` de 1.2.0. El ±4 real
  del top está en el vid1 re-analizado (`data/incoming/vid1.kinelab`, 2.0.0) y
  llega a la demo cuando se regenere (encargo 13 de la secuencia del 16).
- **No se abrió el navegador** (regla de trabajo). Todo lo de arriba se verificó
  sobre los datos, el verificador y los chunks del build.
- **No se corrió `pytest`** por la sesión en paralelo, ver arriba.

### Desviaciones

- **Del contrato, ninguna.** No se tocó ningún `analysis.json`, ningún schema ni
  ningún número.
- **Del prompt, una hacia arriba, chica.** El verificador cubre además
  `contratoAnterior` (los tres trabajos de la demo, el ejemplo 2.0.0 del repo y
  diez bordes de versión). El prompt pedía sólo las columnas retiradas; la
  mutación manual mostró que sin eso la función que decide una línea de la
  pantalla no la miraba nadie, y está en el mismo archivo.
- **`web/src/lib/api.ts`**: `uncertainty.method` pasó de `string` a `string?`.
  Es el rótulo que ahora se muestra y sale de un archivo en disco que pudo
  escribir otra versión del contrato; con el tipo obligatorio, el caso «si no
  viene, el rango sin rótulo» que pide el prompt no se podía escribir sin
  mentirle al compilador. No cambia ningún dato.

---

## 18 de septiembre de 2026 — encargo 27: contención del juicio (ADR-019)

Prompt: `docs/prompts/27-contencion-del-juicio.md`. Informe:
`docs/informes/2026-09-18-27-contencion-del-juicio.md`. Corrió en paralelo con el
**28**, que toca sólo `web/`. No se editó ningún archivo suyo.

Commits: `843d1f4` (código, documentos y el ejemplo regenerado), y el de cierre
con este archivo y el informe.

### Qué existe ahora

- **ADR-019 escrito en `DECISIONES.md`**, y `judgment_allowed` con **dos
  condiciones nuevas e independientes** (`kinelab/metrics/registry.py`), cada una
  con su comentario y su test:
  - `Metric.mdc_validation`, enum de dos valores (`sin_validar` por default,
    `material_real` el único que habilita), validado en `__post_init__` como ya
    se valida `level`. **No es una procedencia**: `PROVENANCES` y el enum de
    `fps_provenance` del schema quedaron intactos.
  - rango obligatorio: `reference is not None`, `kind == "range"` y procedencia
    fuera de `estimacion`/`sin_verificar` (`WEAK_PROVENANCES`). La condición
    vieja —`ref is None or ref.range_width is None`— es de donde salieron los 21.
- **`registry_version` de golf 0.2.0 → 0.3.0**, con el porqué al lado del número.
  El registro genérico del motor queda en 0.1.0. `schema_version` sigue en 2.0.0
  y ningún `metric_version` se movió: **ningún valor cambió**.
- **Dos avisos nuevos en `warnings[]`**, que se suman a los de fps de ADR-016 y
  no los reemplazan. El de la regla sale de lo que el archivo dice —si alguna
  métrica tuviera juicio, no se escribe— y el del MDC lo declara el deporte en
  `Registry.mdc_note`, para que el motor no nombre el arnés ni el modelo de
  cámara (invariante 13).
- **Repetibilidad en `null` con razón** mientras no haya piso de ruido medido
  (`kinelab/metrics/generic.py`), en escalares y en curvas, conservando `n`. El
  CLI imprime la razón en vez de «SD None».
- **El `source` del MDC del sub-cuadro** dice de qué arnés viene y que no está
  validado; la `provenance` sigue en `medido_aqui`, que es de dónde sale el
  número y lo único que el schema admite ahí.
- `pyproject.toml` sin `addopts = "-q"`; notas fechadas de ADR-018 en
  `ESPECIFICACION.md` 3.2 y Fase 5; `CONTRATO.md` §El sextuplo, §summary,
  §subframe y §Versionado, y `CONTEXTO.md` §Vocabulario e invariante 4,
  alineados.
- **`data/sessions/` existe por primera vez.** `cortado3-lento.mp4` vive en
  `data/sessions/hernan/2026-09-15/driver/face_on/take-01`, con gate 9 de 9,
  `pose.npz` y `analysis.json`.

### Medido

- **0 de 21 `judgment_allowed`** en cortado3, y **24 de 24 valores idénticos** a
  `docs/informes/auditoria-2026-09-16/reproduccion.md` §3 (21 con valor y 3
  `null`). Mismos cuadros de evento, misma escala (783,9 px, cuadro 1594), misma
  calidad `confiable`.
- **Suites:** motor **357 pasados, 0 fallados, exit 0** (eran 345: +12 tests
  nuevos, 11 adaptados sin perder ninguna aserción). Arnés **43 pasados, 0
  fallados** en tres corridas, con **exit 134 en una de las tres**, después del
  resumen: el aborto conocido al cerrar el intérprete es **intermitente**, no
  sistemático. No se tocó.
- **Mutación manual: 5 de 5 en rojo.** Sacar la condición (a) → 1 rojo; sacar la
  (b) entera → 3; dejar pasar la procedencia floja → 2; `mdc_validation` con
  default `material_real` → 3; la repetibilidad volviendo a publicar la SD → 2.
- **El punto 6 del encargo 16 cerró acá.** `datos` con `--altura-m 1.75` sobre
  `~/Desktop/cortado.mp4` y `data/incoming/vid1.mp4`, contra la columna «ahora»
  del informe 14 §4. En **vid1 los siete valores no se mueven** (a lo sumo 0,1 cm
  de redondeo). En **cortado se mueven 0,0 a 1,8 cm**, todos por debajo de su
  propio MDC, y la causa es el encargo 18: el top pasó de 33 a **35**. La única
  que no se mueve es `pelvis_sway_impact_cm`, que no se ancla al top. La tabla
  está en el informe.

### Qué falta o no se probó

- **La tabla del informe 26 §4 no es una medición**, y tampoco ninguna SD entre
  repeticiones. Los 21 `judgment_allowed: true` que publicó tienen aritmética
  exacta y ninguno resiste como juicio: `docs/informes/2026-09-16-auditoria-primer-juicio.md`
  §1. No se usa como referencia de nada.
- **Re-habilitar juicio es métrica por métrica**: `mdc_validation="material_real"`
  más un `Reference("range", …)` con procedencia, cada uno con la tabla que lo
  respalde. No hay bandera global, a propósito.
- **`follow_end` y la deriva de cámara siguen abiertos** (encargos propios). El
  `follow_end` 1978 de la rep 1 de cortado3 sigue cayendo en la quietud previa al
  swing siguiente; no se tocó nada de eso.
- **`kinelab/events/order.py` sigue huérfano** (lo anotó el 18). No es archivo de
  este encargo.
- No se tocó `web/`, `service/`, `truth/`, `sports/golf/mdc.yaml` ni
  `data/capture-paths.yaml`. El front no se abrió (regla de trabajo).

### Desviaciones

- **Del contrato, ninguna.** `summary.metrics` es un objeto libre en el schema,
  así que el `null_reason` de la repetibilidad entra sin tocarlo, y el sextuplo
  no cambió: la razón por la que algo no es juicio va a `warnings[]`.
- **Del prompt, una, y es de redacción del aviso.** El prompt pedía los dos
  avisos «siempre que haya al menos una métrica con valor». El primero se escribe
  además **sólo si ninguna métrica del análisis tiene juicio**: si alguna lo
  tuviera, la frase «ninguno de estos números es un juicio» sería falsa, y un
  aviso bien escrito sobre algo falso es exactamente el error del prototipo
  anterior (`HERENCIA.md` §Prohibido portar). Con el registro de golf la
  condición se cumple siempre; hay un test que prueba las dos ramas.
- **Del prompt, una segunda, de arquitectura.** El aviso del MDC nombra el arnés,
  su nivel y el modelo de cámara, y eso no puede vivir en `kinelab/`
  (invariante 13). Se agregó `Registry(version, *, mdc_note=None)`: el deporte
  declara la frase, el motor la transcribe sin saber qué dice.

## 15 de septiembre de 2026 — encargo 18: la señal de manos pesada por confianza, la banda del top y el MDC del sub-cuadro

Prompt: `docs/prompts/18-senal-de-manos.md`. Informe:
`docs/informes/2026-09-15-18-senal-de-manos.md`. Corrió en paralelo con el **16**
(contrato 2.0.0) y el **26** (guía de filmación). Con el 16 hubo que coordinar:
tres enganches de este encargo viven en archivos suyos y **los escribió él**, a
pedido y con el código exacto (ver §Desviaciones). No se editó ningún archivo del
16 ni del 26.

Commits: `c94c8d8` (motor), `c7a322c` (este ESTADO y el informe), `54532d1`
(deporte y tests). **Y `03aea3f`, que es el trabajo del 16 commiteado por esta
sesión a pedido de Hernán**: la sesión del 16 terminó sin commitear, con el
contrato 2.0.0 entero sin commitear en el árbol y `54532d1` dependiendo de él. Se
verificó antes sin tocarlo —motor 345 y arnés 43 en verde, `pnpm lint` y
`pnpm build` limpios— y el mensaje dice qué le falta: **su informe, su sección de
este archivo y las corridas reales de su punto 6.**

### Qué existe ahora

- **`hands_center` pesa por confianza** (`kinelab/events/signal.py`). Acepta los
  `scores` del modelo y un `min_score`: cada muñeca pesa lo que el modelo dice
  que vale en ese cuadro, y la que cae bajo el umbral **no entra**. Si se caen
  las dos, el punto queda `NaN` y lo rellena el mismo relleno acotado de la
  percepción (`interpolate_gaps`, rachas ≤ 5, sin extrapolar bordes). Sin
  `scores`, las dos pesan igual: la firma vieja sigue dando lo de siempre.
- **La banda del top** (`kinelab/events/primitives.py`):
  `direction_change_farthest_band` deja la regla de ADR-017 intacta —gana la
  mayor excursión— y agrega los **rivales**, los candidatos a menos de `margin`
  de la excursión ganadora; `tol_frames` es la distancia en cuadros hasta el más
  lejano. Y `still_noise_px`, el σ de los residuos de una recta ajustada a la
  quietud del address, que ahora comparten la banda y el sub-cuadro del impacto.
- **En `sports/golf/events.py`**: `wrist_score_min` **0,55** y `top_band_sigmas`
  **2,0** en `GolfEventParams` (procedencia `estimacion`); `margin = 2 σ_px` con
  el σ del propio clip; y `events[].impact.subframe.mdc` leído de
  `sports/golf/mdc.yaml` §`events.impact.subframe` — **nunca escrito a mano**
  (ESPECIFICACION 3.3), con `provenance: medido_aqui` para el MDC, distinto de la
  `estimacion` del valor.
- **19 tests nuevos** en `tests/test_eventos_senal.py`.

### Medido

**1 · El umbral salió de un barrido con un criterio que no mira el resultado.**
De 0,00 a 0,65 sobre los cinco clips reales y el mocap: se eligió **el mayor
umbral con el que en ningún cuadro se caen las dos muñecas**. Hasta 0,55 son cero
cuadros sin muñeca; en 0,60 aparecen 3; en 0,65 `vid1` se queda con una racha de
5 —que ya no se rellena— y el top se va a 570. El techo está medido y a dos
décimas. Los scores que lo justifican: en los dos clips del 7/9 la muñeca
izquierda cae a **0,34–0,44 justo en el top** y la derecha no baja de 0,53;
en los otros tres clips ninguna baja de 0,458; en el mocap valen 1,000.

**2 · El peso y el umbral hacen cosas distintas, y hay que separarlos.** Desde el
`pose.npz` guardado (invariante 1) y confirmado de punta a punta con `datos`.
`igual` es como estaba (las dos muñecas pesan lo mismo), `pesado` agrega el peso
por confianza sin umbral, `umbral` es lo que queda hoy:

| clip · vista | address | top `igual` | top `pesado` | **top `umbral`** | impacto | referencia |
|---|---|---|---|---|---|---|
| `cortado.mp4` | 7 | 33 | 33 | **35** | 44 | 36 |
| `20260907_170638.mp4` | 111 | 137 | 137 | **139** | 147 | 139 |
| `vid1.mp4` | 672 | 722 | 722 | **722** | 741 | 722 |
| `vid2.mp4` | 58 | 115 | 115 | **115** | 134 | 114 |
| `vid3.mp4` | — | 0 repeticiones en los tres modos | | | — | — |
| mocap 64_01 `face_on` | 141 | 270 | 270 | **270** | 329 | 269 |
| mocap 64_01 `down_the_line` | 146 | 263 | 263 | **263** | 332 | 269 |

**El peso por confianza, solo, no mueve ningún top**: ni uno, en ninguno de los
siete casos. Lo que lo mueve es el **umbral**, y tiene sentido — con 0,36 contra
0,67 la muñeca perdida todavía se lleva el 35 % del promedio, y el 35 % de un
salto de 300 px son 105 px. Pesar reparte; hace falta decidir.

La «referencia» es la muñeca derecha sola, la señal limpia que usó el 15: **el
error contra ella pasa de −3 / −2 / 0 / +1 a −1 / 0 / 0 / +1**. Donde más se nota
es en el `follow_end`, que sale de la misma quietud: `20260907` 219 → 232 →
**188** y `vid1` 842 → 931 → **931**, y las dos terminan en el cuadro de la señal
limpia (188 y 930). En `20260907` son 31 cuadros —1,03 s— de follow-through que
antes se contaban de más.

**El mocap no se mueve en ningún modo ni en ninguna vista**: con scores 1,000 en
todos los cuadros, pesar y filtrar tienen que ser la identidad, y lo son. Address
e impacto no se movieron en ningún clip; el instante **sub-cuadro** del impacto sí
se corre, pero **por debajo de su propio MDC** en los cuatro clips (0,07 · 0,35 ·
0,60 · 0,74 ms contra 2,927).

**3 · La banda la enciende un solo clip, y es el que había que agarrar.** En
`vid1` los cinco cambios de sentido dan 28,5 · 51,7 · **590,9** · 587,7 · 588,5 px
de excursión: el ganador se lleva el top por **2,2 px** sobre el 726 y **3,2 px**
sobre el 725, con **4,70 px** de ruido medido (el mismo estimador sobre la señal
vieja da **2,274 px**, que reproduce exacto el 2,27 que citó el 15). La banda no
depende del cambio de señal: `vid1` da tolerancia 4 en los tres modos de arriba. Antes salía con `tol_frames` 1,
como si no hubiera duda; ahora sale con **4**, y se propaga: `tempo_ratio` 2,632
pasa de **[2,45 · 2,83] a [2,0 · 3,6]**. Es hoy el único número del proyecto
donde la banda se ve: el resto de las duraciones de los clips reales sigue en
`null` por `fps_min` 120. En los otros seis casos la ventaja del ganador es de
cientos de px y la tolerancia queda en 1.

**4 · El MDC del sub-cuadro llegó al evento**: `2,927 ms`, en los siete clips, y
**también cuando el cruce sale `null`** por vista (`down_the_line`): el MDC
describe al estimador, no a la toma. Contra ±1 cuadro entero son **11×** a 30 fps
y **5,7×** a 60.

**5 · Lo que el umbral cuesta, medido y fijado con tests.** Dejar una muñeca
afuera cambia de estimador a mitad de la señal: el centro de las dos pasa a ser
la otra sola, un escalón de **media empuñadura**. Aislado en el sintético
—muñeca intacta, sólo el score bajado— el top se corre **5 cuadros a 120 fps y 8
a 240**. Con el daño posicional realista encima, el umbral igual gana siempre:
−1 contra −11 a 120 fps, −9 contra −15 a 240. En los clips reales el efecto total
fue de 1 a 2 cuadros y siempre hacia el cuadro de la señal limpia.

Suites: **motor 345 en verde** sobre una copia limpia del HEAD final, **arnés
43** (los 19 nuevos incluidos). **Mutación manual: 8 de 8**
ponen en rojo entre 1 y 9 tests, incluidos los dos que pedía el prompt —pesar por
1 − confianza (7 rojos) y umbral en 0 (6 rojos)—, más el margen al revés, la
banda con el rival más cercano, ADR-017 al revés, el ruido como desvío de la
media, la procedencia del MDC y la banda desactivada.

### Qué falta o no se probó

- **El escalón de media empuñadura** (medido arriba). Corregirlo sería estimar el
  medio vector de la empuñadura e interpolarlo por la racha; no se hizo porque es
  un estimador nuevo que el prompt no pedía y porque ese vector es justo lo que
  más rota en el top. **Decisión del orquestador.**
- **`web/src/components/Metricas.tsx:42` dice «±1 cuadro» en texto fijo** y con
  el `tol_frames` 4 de `vid1` eso es falso. No es archivo de este encargo; el 16
  también lo anotó. Es de una línea.
- **`kinelab/events/order.py` quedó huérfano** cuando el 16 borró
  `sequence_order`. Está en mi directorio y **no lo di de baja**: borrarlo antes
  de que el 16 cerrara rompía el árbol.
- **La exploración por cuadro no usa la señal nueva**: `kinelab/explore.py:165`
  llama `swing_signals(pose, fps)` sin deporte, así que el CSV y el overlay
  siguen con el centro a peso igual mientras los eventos del mismo archivo salen
  de la señal pesada. Es archivo del 16.
- **El error del top sigue sin medirse contra GolfDB** (ESPECIFICACION 2.5). La
  «referencia» de este encargo es una segunda señal, no una verdad.
- Las 17 tomas de `data/exploracion/` conservan su top viejo hasta que se
  re-analicen (invariante 18). No se rehicieron.
- El front no se abrió ni se tocó `web/` ni `service/` (regla de trabajo).

### Desviaciones

- **Del contrato, ninguna.** `subframe.mdc` es campo del schema 2.0.0, que
  escribió el 16 con la forma que este encargo necesitaba
  (`{value, unit, provenance, source}`).
- **Del prompt, una de archivos, y es la grande.** El encargo pedía tres cosas
  cuyos enganches viven en archivos del 16 —`kinelab/analysis.py` (pasarle
  `scores` y umbral a `hands_center`), `kinelab/metrics/core.py` (propagar
  `tol_frames` en vez de ±1 fijo) y `kinelab/contract/schema.json` (el lugar de
  `subframe.mdc`)—, y el propio prompt los ponía en la lista de NO tocar. **No se
  tocaron**: se le pidieron al 16 por escrito, con el código exacto, y los
  escribió él. Sin esos enganches el trabajo de este encargo quedaba escrito y
  sin correr. Es el caso que la §5 de la skill de encargo no cubre —un encargo
  que necesita una línea de un archivo ajeno—, y la salida fue coordinar, no
  rodear.
- **De orden de commits, otra consecuencia de lo mismo.** `sports/golf/events.py`
  escribe `subframe.mdc`, y con el schema 1.2.0 (`additionalProperties: false`)
  esa clave hace fallar la validación de **todo** `analysis.json`. Por eso este
  encargo commiteó en dos partes: primero los dos archivos del motor —verificados
  solos sobre una copia limpia de HEAD, 320 en verde— y recién después de que el
  schema 2.0.0 del 16 estuviera en HEAD, el deporte y los tests.
- **Del prompt, una de alcance hacia abajo:** el escalón de media empuñadura se
  midió y se documentó, pero **no se corrigió**. El prompt no lo pedía y la
  corrección es un estimador nuevo.

---

## 15 de septiembre de 2026 — encargo 26: lo que enseñó el cronómetro, el segundo clip y el test del camino calibrado

Prompt: `docs/prompts/26-lo-que-enseno-el-cronometro.md`. Informe:
`docs/informes/2026-09-15-26-lo-que-enseno-el-cronometro.md`. Corrió con el 16,
el 18 y otras sesiones en paralelo: `kinelab/`, `sports/`, `service/`, `web/` y
`truth/` aparecen modificados en `git status` y **no se tocó ni se commiteó
nada de eso**. Lo mío: `CAPTURA.md`, `docs/filmacion-s22.md`,
`docs/checklist-captura.md`, `tests/test_capture_paths.py`, `data/incoming/`
(ignorado por git), `ESTADO.md` y el informe.

### Qué existe ahora

- **`docs/filmacion-s22.md` reescrita** con las nueve lecciones que midió el 24,
  cada una con su porqué en una línea, más una décima que se midió en esta
  sesión. Arriba de todo, una sola regla: *Slow motion FHD 240, cronómetro
  andando dentro del cuadro, 25 segundos por toma*.
- **`CAPTURA.md`**, cuatro lugares: §Calibración con cronómetro gana la
  subsección **«El método preferido: el cronómetro DENTRO del cuadro del
  gesto»** con los cinco números medidos y sus tres cuidados; §Encuadre gana la
  **serie de seis clips** (21,6 % el peor, 36,0 % el último) y el carrito de
  golf; §Transferencia gana la fila del **recorte en la Mac**; §El gate de
  ingesta gana la nota de **`duration_plausible` en cámara lenta** (el umbral no
  se movió); §Lo que queda por verificar se parte en «contestado» y «abierto».
- **`docs/checklist-captura.md`** sincronizado en cinco casillas (cronómetro en
  marcha, duración real vs. reproducción, no recortar, la serie de encuadre, el
  carrito).
- **`tests/test_capture_paths.py`**: `test_repo_has_the_calibrated_slomo_path_of_the_s22`,
  el hermano del de los declarados. Clava `mode: slomo`, `fps_real` 240,15,
  `fps_playback` 30,0169, el `stretch_factor` como cociente medido y los seis
  campos del cronómetro llenos. **48 en verde** en ese archivo (eran 47).

### Medido

**1 · El segundo clip no pudo verificar nada: su cronómetro está detenido.**
`cartado2-lenta.mp4` (292 cuadros, mismo modo, mismo recorte, 5 minutos después
del otro) lee **00:00.00 en los 292 cuadros**. Verificado por plantilla seguida
cuadro a cuadro (correlación mínima 0,986 contra el cuadro 0 sobre el ancla, y
0,82 en las centésimas, todo explicado por deriva sub-píxel y desenfoque: los
cinco cuadros peor correlacionados leen 00:00.00 a ojo). Tiras en
`data/incoming/cronometro-26/`. **La tasa de captura del proyecto sigue siendo
n = 1.**

**2 · Lo que el segundo clip sí confirma es la REPRODUCCIÓN.** `fps_playback`
30,016952 contra los 30,0169 del camino (0,00017 % de diferencia), `vfr_ratio`
1,0027063599 — **idéntico hasta el décimo decimal** al del primer clip y al del
tercero —, y los mismos 10 deltas de PTS distintos. Los tres archivos salen del
mismo proceso de retiming. Pero la reproducción no es lo que el cronómetro mide.

**3 · Apareció un tercer clip lento, y con él el gate pasó entero por primera
vez.** `~/Desktop/cortado3-lento.mp4` (creado 17:26, una hora después de los
otros dos; 2977 cuadros, 99,14 s de reproducción, **12,40 s reales**). Con
`s22ultra-slomo-fhd240-recorte-mac`: **9 de 9 chequeos, `verdict: ok`**,
`fps_provenance: medido_aqui`. **Es el primer `capture.json` del proyecto que
pasa**, y pasó por la lección 4 del 24 —filmar más largo—, sin mover un umbral.

**4 · Y con él, los primeros `judgment_allowed: true` del proyecto.**
Percepción: 2977 cuadros, detección **1,0000**, cuerpo **691 px = 36,0 % del
alto** (el mejor encuadre de los seis clips reales), cámara 1,35 px, gate de
Fase 1 OK. `analyze`: calidad **confiable**, `warnings: []`, **2 repeticiones**
(1 descartada por `sin_address`), `follow_end` detectado por primera vez en un
clip real. **Once de las doce métricas con `judgment_allowed: true`**; la única
que no es `pelvis_thrust_top_cm`, y falla por vista.

**5 · La serie de encuadre ganó su sexto punto, y sube.** 28,2 / 28,7 / 29,5 /
41,9 / **21,6** / **36,0 %**. El salto de 14,4 puntos entre el quinto y el sexto
es sólo trípode: misma lente, mismo modo, mismo teléfono.

Suites: `tests/test_capture_paths.py` **48 en verde**; **4 de 4 mutaciones** del
YAML ponen rojo al test nuevo (`fps_real`, `mode`, `stretch_factor` redondeado,
`calibrated_by`). La suite entera del motor **no está en verde y no es mía**:
las corridas dieron entre 3 y 25 rojos según el minuto, todos en
`tests/test_fase2.py`, `tests/test_perception.py` y `tests/test_service.py`, y
todos por trabajo a medio escribir de las sesiones paralelas sobre
`kinelab/events/signal.py`, `kinelab/analysis.py`, `kinelab/metrics/generic.py`
y `sports/golf/events.py`. El único archivo de código que toqué es
`tests/test_capture_paths.py`.

### Qué falta o no se probó

- **La verificación independiente de los 240,15 fps sigue pendiente**, y ahora
  se sabe exactamente qué hace falta: un clip de *Slow motion* FHD 240 con el
  cronómetro **andando** en el cuadro. Es el pedido a Hernán.
- **Sigue faltando el ORIGINAL sin recortar** de `DCIM/Camera` (pedido del 24).
  Los tres clips lentos son recortes de la Mac: `elst` que esconde 14, 26 y 4
  cuadros respectivamente.
- **El delta de arranque de Slow motion FHD 240 sigue sin medirse**, por la
  misma razón.
- **Los números de §4 no son reproducibles desde HEAD.** `analyze` corrió
  contra un árbol de trabajo con cambios sin commitear de las sesiones 16 y 18
  (la primera corrida se cayó con `NameError: interpolate_gaps` en
  `kinelab/events/signal.py`, a medio editar; la segunda, minutos después, ya
  funcionó). **El gate de §3 sí es reproducible**: la ingesta no toca ninguno de
  esos archivos. Los valores de las métricas y los cuadros de los eventos hay
  que rehacerlos cuando el 16 y el 18 cierren.
- **`cortado3-lento.mp4` no tiene cronómetro propio**: pasó el gate con la
  calibración prestada del otro clip. Lo que el gate verifica por clip es la
  reproducción, no la captura. Está escrito en `CAPTURA.md`.
- **Dos repeticiones, una descartada, y un `follow_duration_ms` de SD 1292 ms.**
  Los primeros números con juicio habilitado del proyecto son también los
  primeros que nadie revisó. No se ingestó la toma a `data/sessions/`.
- **La pantalla no se abrió** (regla de trabajo). No hacía falta: todo esto es
  documentos, un test y el motor por línea de comandos.

### Desviaciones

- **Del contrato, ninguna.** No se tocó `capture-paths.yaml`, ni el schema, ni
  ninguna métrica. El camino calibrado quedó exactamente como lo escribió el 24.
- **Del prompt, una hacia arriba y anotada: se midió un clip que el prompt no
  nombraba.** El punto 3 pedía verificar los 240,15 fps contra
  `cartado2-lenta.mp4`, y ese clip no puede contestar (§1). `cortado3-lento.mp4`
  apareció en el escritorio después de escrito el prompt, es del mismo modo y
  del mismo camino, y es la única pieza de material capaz de decir algo sobre la
  misma pregunta. Se midió, se reportó, y **no se escribió ningún camino
  nuevo**: usa el que ya existe.
- **Del prompt, una de archivos**: se tocó `docs/checklist-captura.md`, que el
  prompt daba como opcional («si hace falta»). Hizo falta: tres de sus casillas
  quedaban contradiciendo lo nuevo.
- **De proceso, y es la misma trampa que anotó el 25: el commit `eed337c` se
  llevó un `git mv` de otra sesión.** Además de mis tres documentos, ese commit
  contiene el renombre `truth/tests/test_gain_subframe.py →
  test_subframe_encuadre.py` (**0 líneas**: sólo el renombre), que la sesión de
  `truth/` tenía **staged** en el índice cuando yo commiteé los míos. `git add`
  de rutas explícitas no lo agregó — ya estaba en el índice, y el índice es uno
  solo. El árbol quedó bien (el contenido de ese archivo sigue sin commitear, en
  manos de su sesión), pero el renombre figura en el commit equivocado.
  **No se corrigió**, por la misma razón que dio el 25: reescribir un commit
  mientras otra sesión puede estar trabajando sobre esos archivos es peor que la
  molestia.

  Para el que venga, y ya van dos: antes de commitear, `git status` no alcanza
  — hay que mirar **qué hay staged que no es tuyo** (`git diff --cached --name-only`)
  y, si hay algo, esperarlo o avisarle a la otra sesión.

---

## 15 de septiembre de 2026 — encargo 25: publicar un trabajo a internet desde la pantalla

Prompt: `docs/prompts/25-publicar-un-trabajo.md`. Informe:
`docs/informes/2026-09-15-25-publicar-un-trabajo.md`. Corrió con el 24 en
paralelo (`data/capture-paths.yaml`, `data/incoming/`): ese archivo aparece
modificado en `git status` y **no se tocó ni se commiteó**. El 16, 18 y 21 siguen
abiertos; ninguno de sus archivos se tocó (`kinelab/explore.py`,
`kinelab/events/`, `sports/`, `truth/`, `Reproductor.tsx`, `page.tsx` quedaron
intactos).

### Qué existe ahora

- **`kinelab/tools/publicar.py`**: `python -m kinelab.tools.publicar TRABAJO
  [--quitar] [--solo-construir]`. Cuatro pasos —exportar, registrar, construir,
  desplegar—, uno por trabajo, reversible. El índice se arma del **conjunto que
  hay en disco**, nunca del argumento: publicar uno nuevo no saca del listado a
  los que ya estaban. `--solo-construir` deja el sitio listo sin tocar internet.
- **`web/public/demo/` salió de git** (`git rm -r --cached`, 38 archivos,
  20,4 MB). Sigue en disco. Lo que va a git es **`data/publicados.json`**: el
  registro de qué se mandó afuera, desde cuándo y con qué enlace.
- **Lo que se sube es un árbol armado acá**, no el repo: `web/.vercel/output/`
  con la Build Output API v3 (`static/` + `config.json`), y de ahí
  `vercel deploy --prebuilt --prod`. El `noindex` viaja en `config.json`, porque
  con `--prebuilt` el `web/vercel.json` no se aplica.
- **En el backend**: `POST /api/datos/{id}/publicar` y su `DELETE`, que corren el
  comando en un hilo y devuelven 202 con el paso; `GET /api/publicacion` con qué
  está publicado y qué está corriendo; y `publicado`, `publicado_url` y
  `publicado_en` en cada fila de `GET /api/datos`. Uno por vez: el segundo pedido
  es 409. La cola está en `service/publicacion.py`, archivo nuevo.
- **En la pantalla** (`ListaTrabajos.tsx`): botón «publicar» por fila, con una
  confirmación que dice el texto entero —el video y sus datos quedan accesibles
  para cualquiera que tenga el enlace—, el paso en el que va mientras corre, y
  publicado: la etiqueta, el enlace, «copiar enlace» y «quitar de internet».
  Nada de publicar al subir, ni por defecto, ni en lote. En modo demo no se
  muestra ninguna de las acciones.
- **25 tests nuevos**: 19 en `tests/test_publicar.py` (comando, con el ejecutor
  de comandos inyectado) y 6 en `tests/test_service.py` (endpoints, con el
  comando simulado).

### Medido

**1 · El ciclo, sobre trabajos reales.** Publicado `17ed40a4…` (`cortado.mp4`)
con `--solo-construir`: **3,60 MB, 12 archivos, 14,4 s** de punta a punta.
El índice quedó con **cuatro**: los tres que ya estaban más el nuevo. Después
`--quitar` sobre ése: **10,6 s**, el índice volvió a **tres**, el `video.mp4` del
quitado da **404** servido por `curl` y el de `vid1` sigue dando **200** con sus
6.422.370 bytes. El registro lo pasó a `quitados` con su fecha.

**2 · El estático servido por `curl`** desde `web/.vercel/output/static/` (sin
abrir el navegador): `/` 200 text/html 6604 B · `/demo/index.json` 200 4614 B ·
`trabajo.json` 24.541 B · `video.mp4` 200 video/mp4 1.328.950 B ·
`transformacion.json` 1235 B · `pose3d.json` 375.327 B · un archivo inexistente,
404.

**3 · El registro quedó al día con la realidad.** Los tres que están en el sitio
se re-exportaron y se anotaron: `vid1.mp4` 14,89 MB (13 archivos),
`cmu-64_01-face_on` 2,71 MB, `cmu-64_01-down_the_line` 2,53 MB. Total en disco
**22 MB** en `web/public/demo/`, cero en git. De paso, los dos de mocap pasaron a
`pose3d.json` **1.1.0** con la capa de ángulos: era lo que el 23 dejó pendiente.

**4 · El backend, con `curl` contra `python -m service` de verdad** (sin
publicar nada): `GET /api/publicacion` devuelve los tres con su enlace,
`corriendo: null`; `GET /api/datos` marca `publicado=true` en esos tres y
`false` en los otros quince. `POST` de un id que no existe, 404 con la frase;
`DELETE` de uno que no está publicado, 404 con la suya; `..%2F..%2Fx`, 404.

**5 · El bug que el prompt anticipaba no existía.** `escribir_indice` ya
recorría la carpeta de salida en vez de la lista de argumentos (encargo 22). El
test que lo cuida se escribió igual, y la mutación que lo reintroduce lo pone
rojo.

Suites: motor **320 en verde** (25 nuevos, 52 s), arnés **49** (12,3 s),
`pnpm lint` limpio y los dos builds limpios. **Mutación manual: 13 de 13.** Una
se escapaba —reescribir `publicado_en` al republicar: las dos fechas caían en el
mismo segundo y el test pasaba igual— y el test se rehizo con una fecha vieja
escrita a mano.

### Qué falta o no se probó

- **No se desplegó nada.** Todo lo de esta sesión se corrió con
  `--solo-construir`: internet no se tocó. El paso 4 —`vercel link` +
  `vercel deploy --prebuilt --prod`— está escrito y testeado con el ejecutor
  inyectado, pero **nunca corrió contra Vercel de verdad**. Lo dispara Hernán
  desde la pantalla o con el comando sin `--solo-construir`.
- **`web/` todavía no está vinculado**: no hay `web/.vercel/project.json`, así
  que el primer deploy corre `vercel link --yes --project kinelab --scope
  hernandiazz9s-projects`. Si el proyecto o el equipo no se llaman así, ese
  comando falla y hay que vincular a mano (las dos constantes están arriba de
  `kinelab/tools/publicar.py`).
- **La `SITIO` que se anota es la URL de deploy que traía el prompt**
  (`kinelab-qnm5fa60a-…`), no el alias estable de producción. Si Vercel da otro
  alias, se cambia con `--sitio` o `KINELAB_SITIO` y los enlaces del registro se
  reescriben al republicar.
- **La pantalla no se abrió** (regla de trabajo). Sin verla, lo que más puede
  fallar: los botones de la derecha de cada fila en una ventana angosta (la
  fila pasó de ser un `<button>` entero a un `<div>` con el botón principal y las
  acciones al lado), y `navigator.clipboard`, que en `http://localhost` existe
  pero en un `http://` de red no.
- **El deploy no informa progreso**: el paso 4 es una sola línea que dura lo que
  dure `vercel deploy`. La pantalla dice «paso 4 de 4 · desplegando» y no se
  mueve hasta que termina.
- **Sin borrado del trabajo local.** Quitar de internet no borra
  `data/exploracion/<id>/`, a propósito; eso sigue siendo `rm -rf`.
- **El sitio entero se reconstruye y se sube por cada publicación.** Con tres
  trabajos son 22 MB y ~15 s de build; con veinte, no se midió.

### Desviaciones

- **Del contrato, ninguna.** `data/publicados.json` no es un artefacto del
  contrato: no hay métricas, ni números con unidad, ni nada derivado de la pose.
  Es el registro operativo de qué salió de esta Mac, con su `schema` adentro
  (`kinelab.publicados/1.0.0`), igual que `transformacion.json` y `pose.json` del
  22. `CONTRATO.md` §Layout no se tocó.
- **Del prompt, tres de archivos.** (1) `service/publicacion.py`, archivo
  **nuevo**: la cola de publicación no es la de exploración y meterla en
  `service/exploracion.py` mezclaba dos colas en un archivo cuyo encabezado habla
  de otra cosa. Al ser nuevo no puede chocar con ninguna sesión. (2)
  `web/eslint.config.mjs`: una línea para ignorar `.vercel/**`. Sin eso
  `pnpm lint` pasa a lintear el bundle minificado que arma este encargo y
  devuelve 2861 problemas que no son de nadie. (3) `tests/test_publicar.py` y el
  bloque nuevo de `tests/test_service.py`, que el propio prompt pide.
- **Del prompt, una de alcance hacia arriba**: `GET /api/publicacion`. El prompt
  pedía `publicado` y su URL en las filas de `GET /api/datos`, y está; pero el
  progreso vive en otro lado porque la lista se refresca desde `page.tsx`, que
  **no** es archivo de este encargo, y sin un endpoint propio `ListaTrabajos` no
  podía sondear nada sin tocarlo.
- **`service/exploracion.py` quedó sin cambios** aunque el prompt lo asignaba:
  `publicado` se agrega en `service/app.py` al armar la respuesta. La fila de un
  trabajo no tiene por qué saber de publicaciones.
- **De proceso: el commit `1b0a640` del encargo 24 se llevó trabajo de éste.**
  Además de sus tres archivos (`data/capture-paths.yaml`, `ESTADO.md` y su
  informe), ese commit contiene las **38 eliminaciones de `web/public/demo/`**
  que esta sesión había dejado en el índice con `git rm -r --cached` (41 archivos
  cambiados en total). El árbol quedó como tenía que quedar —los datos
  publicados están fuera de git—, pero la baja figura en el commit equivocado y
  con el mensaje equivocado. **No se corrigió**: reescribir el commit de otra
  sesión que puede seguir corriendo es peor que la molestia. Es exactamente lo
  que avisa §5 de la skill de encargo: el índice de git es uno solo.

  Para el que venga: si hay otra sesión en el mismo directorio, dejar algo
  **staged** y seguir trabajando es lo que hay que evitar. `git rm --cached` y el
  commit que lo acompaña tienen que ir juntos.

---

## 15 de septiembre de 2026 — encargo 24: el cronómetro filmado, y el primer camino calibrado

Prompt: `docs/prompts/24-cronometro-y-swing-lento.md`. Informe:
`docs/informes/2026-09-15-24-cronometro-y-swing-lento.md`. El 16, 17, 18 y 21
siguen abiertos y no se tocó ninguno de sus archivos. Hay otra sesión trabajando
en `service/app.py`, `kinelab/tools/publicar.py`, `service/publicacion.py` y
`tests/test_publicar.py`: no se tocaron. En esta sesión **no se cambió una sola
línea de código**: sólo `data/capture-paths.yaml`, `data/incoming/` (ignorado
por git), `ESTADO.md` y el informe.

### Qué existe ahora

- **El primer camino CALIBRADO del proyecto**, en `data/capture-paths.yaml`:
  `s22ultra-slomo-fhd240-recorte-mac`, `calibrated: true`, `mode: slomo`,
  `fps_real` **240,15**, `fps_playback` **30,0169**, `stretch_factor`
  **8,0005**, con `fps_method` contando las dos lecturas y el conteo de cuadros.
  Hasta hoy los cuatro caminos del repo eran declarados (ADR-016) y por eso
  ninguna métrica del proyecto podía ser juicio.
- **La primera tasa de captura medida**, del cronómetro que Hernán filmó
  **dentro del mismo cuadro** que el swing (`~/Desktop/Cortado-lenta.mp4`, copia
  en `data/incoming/`, sha256 `ff13415e…`). 41 lecturas leídas del clip, 39
  usadas: ajuste **240,15 fps ±0,60 (1 σ)**, residuo rms 0,011 s (2,7 cuadros).
- **Es uniforme, y está acotado.** Los tres tercios dan 238,38 / 239,66 /
  242,73 fps, cada uno dentro de su propio 1 σ del global. Y el residuo máximo
  de la recta (0,037 s) acota a **1,3 cuadros de 598** cualquier tramo que
  hubiera sido capturado a velocidad normal. El modo *Slow motion* FHD del S22
  no mezcla velocidades.
- **El gate pasa 8 de 9.** Por primera vez pasan `fps_min_for_gesture` (240,15
  contra 100) y `fps_matches_path`, y por primera vez un `capture.json` sale con
  `fps_provenance: medido_aqui`. **Rechaza por `duration_plausible`**: la toma
  dura **2,49 s reales** (598 cuadros / 240,15) y el gate pide 3. **El umbral no
  se tocó.** Con `stretch_factor` 8, llegar a 3 s reales pide **≥ 721 cuadros,
  o sea ≥ 24 s de reproducción**.
- **Las doce métricas, calculadas** (modo exploración, porque `run_perception`
  se niega sobre una toma rechazada): **diez con valor**, `follow_duration_ms`
  sin `follow_end` y `pelvis_thrust_top_cm` por vista. Con
  `fps_provenance="medido_aqui"`, **diez tendrían `judgment_allowed: true`** —
  evaluado con la propia función del registro sobre estos valores, sin tocar
  nada. Hoy las doce dicen `false`, y **no por el fps**: la exploración fuerza
  `sin_verificar` siempre (ADR-016, encargo 06). Falta un solo eslabón, y es el
  gate.
- **El impacto verificado contra la pelota a 240 fps.** La pelota está en el tee
  hasta el cuadro 367 y ya salió en el 368; el motor pone el impacto en el 365
  (cruce sub-cuadro en 364,79). **Sesgo −11,3 ms (2,71 cuadros), el motor
  temprano**, contra una incertidumbre sub-cuadro declarada de ±1,3 ms. A 60 fps
  eran 0,68 cuadros y por eso en `vid1` el motor «acertaba».
- Imágenes para mirar en `data/incoming/cronometro-24/` (siete cuadros por
  índice y siete tiras ampliadas del cronómetro y de la pelota) y salidas del
  motor en `data/incoming/Cortado-lenta.kinelab/`. Los dos, ignorados por git.

### Medido

**1 · El archivo es un recorte hecho en la Mac, no el del teléfono.** `udta` de
Samsung de 1 MB → **185 B**, `handler_name` `Core Media Video`, y un `elst` de
QuickTime con `media_time` 40432/90000 = 0,449 s que esconde **los primeros 14
cuadros**: **612 paquetes, 598 cuadros presentados**. No tiene
`com.android.capture.fps` ni ninguna `com.samsung.*`. ffprobe, ffmpeg y el motor
coinciden los tres en 598.

**2 · Reproducción 30,016828 fps, `vfr_ratio` 1,0027** (CFR), primer delta
0,033333 s: normal, porque el recorte se llevó el arranque de la cámara.
`fps_truth --duracion-real 2.4901 --nominal 240` → veredicto **`ESTIRADO`**,
captura 240,15, factor 8,00.

**3 · Calidad `confiable`**: detección 1,0000; cuerpo **414 px = 21,6 % del
alto** (el peor encuadre de los cinco clips reales: antes 28,2 / 28,7 / 29,5 /
41,9 %); plausibilidad 22/598 (3,7 %, 19 de codo); movimiento de cámara 1,05 px;
**multi-sujeto 0,0134 = 8 cuadros**: el carrito de golf de la derecha se detecta
como persona en el 1,3 % de los cuadros, y el seguidor nunca lo sigue.

**4 · Eventos**: address 86 (0,3581 s), top 293 (1,2201 s), impacto 365
(1,5199 s), sin `follow_end`. **Backswing 862,0 ms** [857,8 · 866,1],
**downswing 299,8 ms** [295,6 · 304,0], **tempo 2,88**. A 240,15 fps ±1 cuadro
son **±4,16 ms**: por primera vez la cuantización del tiempo queda por debajo
del MDC de las duraciones (12,6 y 13,0 ms).

**5 · El cronómetro refresca ~15 veces por segundo**, no 100: cada meseta dura
10–22 cuadros y el valor salta 6 o 7 centésimas. Ahí está todo el ruido que
quedó. Y el teléfono del cronómetro se corre **30 px en x y 71 px en y** a lo
largo del clip, así que hubo que alinear cuadro por cuadro para leerlo.

Suites: motor **320 en verde** (51,6 s; incluye los de la sesión paralela),
arnés **49** (14,1 s), `tests/test_capture_paths.py` **47**. El camino nuevo es
**el primero que ejercita la rama `calibrated: true`** de
`test_repo_capture_paths_yaml_is_valid`.

### Qué falta o no se probó

- **Falta el archivo ORIGINAL sin recortar**, de `DCIM/Camera`, del mismo modo y
  con el mismo cronómetro. Es el pedido abierto a Hernán y resuelve dos cosas
  juntas: calibrar el camino **del teléfono** (el de hoy calibra un recorte) y,
  si dura ≥ 24 s de reproducción, **pasar el gate entero por primera vez**.
- **Hay un segundo clip lento sin mirar**: `~/Desktop/cartado2-lenta.mp4`
  (318 paquetes / **292 cuadros**, mismo modo y mismo recorte). Son 1,22 s
  reales: tampoco pasaría `duration_plausible`. No se ingestó ni se exploró.
- **El delta de arranque de *Slow motion* FHD 240 sigue sin medirse** (pregunta
  3 del informe del 03): el recorte se llevó los cuadros del arranque.
- **El aviso de `analysis.json` dice algo falso con un camino calibrado**:
  `warnings[1]` sale *"camino declarado sin cronómetro … 240.15 fps asumidos"*
  cuando el camino **está** calibrado y el número está **medido**. Es
  `kinelab/analysis.py:195`, que usa `DECLARED_NOTE` para todo lo que no sea
  `medido_aqui`. **No se tocó**: el prompt prohibía `kinelab/`.
- **No hay test que fije el camino calibrado.** Existe
  `test_repo_has_the_declared_paths_of_adr_016` para los declarados; el nuevo
  sólo se valida por schema. Son cinco líneas en
  `tests/test_capture_paths.py`, que no me asignaba el prompt.
- **La pantalla no se abrió** (regla de trabajo). No hacía falta: todo esto es
  motor y archivos.
- **Un solo swing, un solo cronómetro, un solo teléfono.** El `fps_real` de
  *Video* FHD 60 y FHD 30 del mismo S22 sigue sin cronómetro, y sus tres caminos
  siguen declarados.

### Desviaciones

- **Del contrato, ninguna.** El camino nuevo usa el schema 1.1.0 tal como está;
  `capture.json` sale en 1.2.0 sin campos nuevos; no se agregó ni se movió
  ninguna métrica.
- **Del prompt, una de criterio, anotada.** El prompt pedía escribir el camino
  sólo si los tramos daban la misma tasa **dentro de un 1 %**; los extremos
  difieren **1,81 %**. Se escribió igual, con la razón en el informe §4 y en las
  `notes` del YAML: cada tramo cae dentro de su propio 1 σ (la diferencia entre
  el primero y el tercero es 0,9 σ), el 1,81 % es ruido del refresco del
  cronómetro y no una diferencia medible, y la cota dura —que ningún tramo mayor
  a 1,3 cuadros pudo haberse capturado a velocidad normal— es la que contesta de
  verdad la pregunta que el 1 % quería hacer. Si el orquestador prefiere el
  criterio literal, el camino sale del YAML borrando su bloque.
- **Del prompt, una hacia abajo**: no se corrieron `kinelab.perception` ni
  `kinelab analyze` sobre la toma ingestada, porque el gate la rechazó y
  `run_perception` se niega (`kinelab/perception/run.py:74`). Los números
  salieron por `kinelab datos` con el mismo camino, que es lo que el encargo 06
  ya había hecho en la misma situación.

---

## 15 de septiembre de 2026 — encargo 23: los ángulos en 3-D, y cuánto se equivoca la cámara

Prompt: `docs/prompts/23-angulos-en-3d.md`. Informe:
`docs/informes/2026-09-15-23-angulos-en-3d.md`. El 22 ya había cerrado
(`c762bdc`); el 16, 17, 18 y 21 siguen abiertos y no se tocó ninguno de sus
archivos. `kinelab/`, `sports/`, `service/`, `Reproductor.tsx`, `api.ts` y
`page.tsx` quedaron intactos.

### Qué existe ahora

- **Once ángulos en `pose3d.json`, en 3-D y proyectados.** En el mocap el ángulo
  3-D es el **verdadero**: tres puntos medidos en el espacio, sin proyección en
  el medio y sin los 21–32° de ADR-007. Los ocho de tres puntos (codo, rodilla,
  cadera y hombro de los dos lados) usan **los mismos tres puntos** que dibuja el
  overlay plano, y un test los compara contra las columnas del propio motor
  (`kinelab.explore.per_frame_table`) para que no se desincronicen. Más la
  inclinación de tronco, y el **giro de la línea de caderas** y el de la **de
  hombros** alrededor del eje vertical respecto de la línea de tiro, que en 2-D
  no existen.
- **`pose3d.json` pasa a `kinelab.pose3d/1.1.0`**: `angulos` (unidad, los dos
  marcos, las procedencias, las once definiciones con sus puntos, su anclaje de
  dibujo, su `respecto_de` y qué es el proyectado de cada una, el rótulo de la
  capa y el resumen de este trial), `angulos_3d` y `angulos_proyectados` por
  vista. Campos nuevos y opcionales → minor. **245 KB → 375 KB.**
- **`python -m kinelab_truth.mocap 64 --angulos`**: la tabla de los **diez
  trials** del sujeto 64 —sesgo y límites de acuerdo por ángulo, vista y evento,
  más el peor cuadro de la repetición— en 2,4 s, y escrita en
  `truth/reports/angulos-proyeccion-2026-09-15.json`.
- **La capa de ángulos en el visor**, con su interruptor: el número al lado de
  la articulación, con el amarillo del overlay plano, siguiendo al punto al
  girar y sin pisarse entre rótulos. Al llegar a una de las dos vistas del
  protocolo aparece debajo el valor proyectado y la diferencia, más la línea que
  dice qué es cada uno. Los dos números salen **del archivo**: la pantalla no
  compone ninguno.
- **El esqueleto entra entero.** El encuadre se calcula sobre la caja que
  contiene al sujeto en **todos** los cuadros, con margen fijo para los números,
  y el zoom lo multiplica en vez de recalcularlo (si no, la rueda dejaba de
  hacer nada).
- **El texto ya no tapa la figura**: una línea a la vista y el argumento entero
  detrás de «por qué esto no se puede hacer con un celular».
- **12 tests nuevos** en `truth/tests/test_angulos.py`, y la verificación
  headless de `pose3d.verificar.mjs` con tres comprobaciones nuevas (encuadre,
  zoom y la capa de ángulos).

### Medido

**1 · El ángulo del codo de atrás, desde `face_on`, sobre-lee 28,5° en el
address** [25,2 · 31,9] y hasta **57,8°** en el peor cuadro de la repetición. En
64_01 el codo derecho mide **151,7° en 3-D y la cámara lo ve en 179,8°**: un
brazo perfectamente estirado que no lo está. Sin estimador de pose y sin ruido:
es la proyección sola. La literatura de ADR-007 mide 21,5–32,7° de error medio de
codo **con** estimador adentro.

**2 · La vista decide qué ángulo se puede leer.** El codo de atrás es el peor
desde `face_on` (+28,5°) y el mejor desde `down_the_line` (−1,6°); el de adelante
al revés. Las rodillas sobre-leen **28–31°** en el address desde `face_on` y
menos de 2° desde `down_the_line`: el golfista flexiona hacia esa cámara.

**3 · El giro de la línea de caderas.** Desde `face_on` el estimado por
acortamiento acierta la magnitud dentro de **1,0°** (el signo no lo recupera:
es un `arccos`). Desde `down_the_line`, en el address, dice **+82,8°**
[78,0 · 87,7] cuando las caderas apuntan al objetivo, y **+88,2°** en el peor
cuadro. Es el mismo colapso que el 13 midió en °/s y el 19 en largo proyectado,
ahora en grados y sobre un ángulo que un entrenador nombra.

**4 · La inclinación de tronco sub-lee 11,3° desde `face_on`** en el address
(13,9° reales contra 0,8° en la imagen en 64_01): la misma geometría que
`CONTRATO.md` §La escala midió para los cm, ahora en grados.

**5 · El esqueleto se salía, y ahora no.** Recuadro de 337 × 599 px: antes, con
la cámara en `down_the_line`, **337 de 11.648 puntos afuera del canvas en 257 de
448 cuadros**, y en el peor de 216 ángulos, 211 puntos. Desde `face_on` entraba
**por 3,4 px de 1920**. Ahora, en los mismos 216 ángulos, **0 puntos afuera con
41,9 px de sobra**. El precio es tamaño: la figura queda **13 % más chica** que
el mapeo crudo del cuadro (594 → 515 px de alto desde `face_on`).

**6 · El archivo se sirve con los ángulos.** `curl` a un backend propio en el
8767: **200**, `application/json`, **375.327 bytes**, `kinelab.pose3d/1.1.0`, 11
definiciones, series de 11 × 448 y los dos juegos de proyectados. `pose.npz`
sigue en 404 y un trabajo de celular no tiene `pose3d.json`.

Suites: arnés **49 en verde** (12 nuevos, 12,3 s), motor **295** (44 s, no se
tocó), `pnpm lint` y `pnpm build` limpios. **Mutación manual: 9 de 9** en
`mocap.py` y **6 de 6** en el TypeScript. Dos mutaciones no se cazaban —el
tronco medido contra la vertical hacia abajo (daría 153° donde hay 27°) y la
diferencia de los giros contra el valor con signo— y se agregaron los dos tests
que las cazan.

### Qué falta o no se probó

- **Hay que regenerar la demo estática del 22.** `web/public/demo/` tiene los dos
  ejemplos de mocap con `pose3d.json` **1.0.0**, sin ángulos. El visor abre igual
  y lo dice (interruptor apagado y la frase «este pose3d.json es anterior a la
  capa de ángulos»), pero la capa no está. Es correr `exportar_demo.py`, que es
  archivo del 22 y no se tocó.
- **La pantalla no se abrió** (regla de trabajo). Sin verla, lo que más puede
  fallar: once números al lado de once articulaciones en un recuadro angosto
  —hay resolución de choques, pero no está mirada—, y el rótulo negro de arriba
  del canvas sobre la cabeza ahora que la figura llena más el recuadro (42 px de
  margen vertical contra ~26 de rótulo).
- **El proyectado de los dos giros es `estimacion`.** Alrededor del eje vertical
  no hay ángulo que medir en una imagen: lo que se compara es el estimado por
  acortamiento, que es el `shoulder_rotation_deg` que `HERENCIA.md` prohíbe
  portar, puesto acá **sólo** para medir cuánto se equivoca. No recupera el
  signo, y por eso la diferencia va contra el valor absoluto del 3-D.
- **Un sujeto, diez swings, una geometría de cámara** (3 m, 1,2 m de altura, dos
  azimuts). La tabla no dice nada de otro golfista ni de otra cámara, y **no
  mide al estimador de pose**: mide la proyección sola. Barrer distancia, altura
  y azimut con `harness.py` es otro encargo.
- **Nada entró al registro de métricas ni a `analysis.json`.** `kinelab/` no se
  tocó.

### Desviaciones

- **Del contrato, ninguna.** No se agregó ninguna métrica, ningún campo de
  `analysis.json` ni ninguna entrada al registro. `CONTRATO.md` §Niveles sigue
  diciendo que los ángulos absolutos de codo, rodilla y muñeca son nivel 3, y
  esto no los construye: los mide en el mocap para mostrar por qué están ahí.
  `pose3d.json` sigue fuera del contrato (pregunta abierta del 19).
- **Del prompt, una de archivos**: además de `mocap.py`, `truth/tests/` y
  `Visor3D.tsx`, se tocaron `web/src/lib/pose3d.ts` y
  `web/src/lib/pose3d.verificar.mjs`. Los dos son del 19 y no los tiene ningún
  encargo abierto. Razón: el encuadre y la proyección son matemática pura, y
  viven ahí justamente para poder verificarlos sin abrir el navegador (que es lo
  que la regla de trabajo prohíbe); meterlos en el componente los dejaría sin
  verificación. `proyectar()` no cambió de firma ni de resultado: ahora delega en
  `proyectarEn`, y la verificación contra el arnés sigue dando 0,855 / 0,922 px.
- **Del prompt, una hacia arriba**: el visor tolera un `pose3d.json` 1.0.0 sin
  ángulos en vez de romperse. No estaba pedido, pero hay uno publicado en la
  demo y sin esto la pantalla quedaba en blanco.
- **`POSE3D_SCHEMA` 1.0.0 → 1.1.0** decidido en esta sesión, con el criterio de
  `CONTRATO.md` §Versionado (campos nuevos y opcionales → minor). `pose3d.json`
  no está en el contrato, así que no va a §Desviaciones de ahí.

---

## 15 de septiembre de 2026 — encargo 22: el repo en GitHub y la demo estática

Prompt: `docs/prompts/22-github-y-demo-estatica.md`. Informe:
`docs/informes/2026-09-15-22-github-y-demo-estatica.md`. El 19 ya había cerrado
(`1240ebb`); el 16, 17, 18, 20 y 21 seguían abiertos y sin commitear, y ninguno
de sus archivos se tocó salvo lo que dice §Desviaciones.

### Qué existe ahora

- **El repo está en GitHub, privado**: https://github.com/hernandiazz9/kinelab,
  `main` subido, `visibility: PRIVATE` verificado. La lista de lo que habría que
  revisar antes de hacerlo público —siete puntos, del GPS del lugar de filmación
  al correo en 79 commits— está en el informe. **No se borró nada.**
- **`kinelab/tools/exportar_demo.py`**: de un trabajo de `data/exploracion/`
  produce la versión web en `web/public/demo/<id>/`. Recorta al tramo del gesto,
  recorta al rectángulo que contiene al sujeto con margen, reescala, pasa las
  fotos a JPEG, y **deja escrito cómo deshacer las tres cosas**. Medido sobre
  `vid1`: **424 MB → 14,89 MB**, y el golfista pasa de **29,0 % a 56,0 %** del
  alto del cuadro (×1,93).
- **`transformacion.json`**, el artefacto central del encargo: `offset_x`,
  `offset_y`, `escala`, `cuadro_offset`, el recorte, los dos tamaños, la caja del
  sujeto, y los puntos que caen fuera del cuadro del origen contados. **Los
  keypoints no se reescriben**: `pose.json`, `analysis.json`, el CSV y los
  eventos siguen en `image_px` y en cuadros del original. La regla está escrita
  dentro del archivo, en `nota`, no en un comentario del código.
- **`pose.json`**: los 26 puntos por cuadro del tramo, con nombres, huesos,
  scores, plausibilidad y `provenance`. Formato elegido acá (`kinelab.pose2d/
  1.0.0`) porque el 21 no había cerrado; es la forma que su prompt pide para
  `GET /api/datos/<id>/pose`.
- **Modo demo del front**: `NEXT_PUBLIC_KINELAB_MODO=demo` →`output: "export"`,
  lectura de `/demo/index.json` y `/demo/<id>/trabajo.json`, sin backend. La
  decisión está en **un solo lugar** (`web/src/lib/api.ts`); los componentes
  llaman a las mismas funciones en los dos modos. El formulario de subir se
  reemplaza por la frase que dice por qué. `noindex` en el `<meta>` (en los dos
  modos) y `X-Robots-Tag` desde `web/vercel.json`.
- **`web/vercel.json`** con `framework: nextjs` y
  `buildCommand: NEXT_PUBLIC_KINELAB_MODO=demo pnpm build`: la demo no depende
  de que alguien configure una variable en un panel. El único paso manual en
  Vercel es poner el directorio raíz en `web`.
- **`primerCuadro` en `Reproductor.tsx` y `DosCuadros.tsx`** (default 0): el
  cuadro del origen que es el t=0 del archivo. Los números de cuadro que se ven
  siguen siendo los del original —672 sigue siendo 672— y la conversión a tiempo
  del archivo queda en un solo lugar.
- **La demo exportada, commiteada**: `vid1` y los dos ejemplos de mocap, 20,4 MB.
- **23 tests** en `tests/test_exportar_demo.py`, sobre un trabajo sintético
  armado en el propio test.

### Medido

**1 · El peso.** `vid1` 424 MB → **14,89 MB** (×28,5); mocap `face_on` 4,8 →
2,58; `down_the_line` 4,4 → 2,40. Total en el repo **20,4 MB**. Ningún archivo
pasa de 6,51 MB. Los 14,89 dejan **0,7 % de margen** contra el objetivo de 15:
la palanca es `--crf` (hoy 23) o `--alto`. El 23 se eligió a ojo y no se midió:
el 20 midió el `crf 20` del overlay (94,1 % del laplaciano en las manos; el
borrón es el obturador, no el códec), no este recorte reescalado.

**2 · El sujeto ampliado.** Mediana de `body_height_px` en el tramo de `vid1`:
1113 px, **29,0 %** del alto original y **56,0 %** del exportado. El techo no es
el margen: la caja del sujeto mide **1655 px de alto contra 809 de ancho** (en el
top las manos suben muy por encima de la cabeza), así que el cuerpo no puede
pasar de ~60 % sin cortar el swing.

**3 · El margen sale de medir.** 0,10 del alto de la caja. En el cuadro del top
la cabeza del palo llega a **y≈1086 px** y el keypoint más alto del tramo está
en **1123**: el palo no es un keypoint. Con 0,10 el recorte arranca en 957 y
quedan **129 px de aire**. Verificado mirando el cuadro exportado.

**4 · La transformación, de punta a punta sobre datos reales.** Los 291 × 26
keypoints del tramo caen dentro del cuadro exportado (x ∈ [131,2 · 494,2] de
618; y ∈ [178,3 · 901,9] de 1080). Y el esqueleto de `pose.json` dibujado sobre
el `video.mp4` exportado usando **sólo** `transformacion.json` —lo mismo que va a
hacer el front— cae sobre el golfista en el top (722) y en el impacto (741).

**5 · Lo que no se puede salvar, se cuenta.** `puntos_fuera_del_origen`: 0 de
7566 en `vid1`, 0 de 11.102 en el mocap `face_on`, **315 de 10.972 (2,9 %)** en
el mocap `down_the_line`, donde la cámara virtual proyecta las manos del top
fuera del lienzo. Ningún recorte los puede incluir y el archivo lo dice.

**6 · El build de demo no puede hablar con un backend.** En
`web/out/_next/static/chunks/` las cadenas `api/datos` y `api/config` **no
aparecen** (rama muerta, el minificador la elimina); en el build local sí.

Suites: motor **295 en verde** (23 nuevos, 32 s), arnés **37** (7,3 s),
`pnpm lint` limpio y **los dos builds** limpios. Servido `web/out/` con un
servidor estático: los 14 archivos que el front pide responden 200 con su media
type, y `pose.npz` y `original.mp4` dan 404. **Mutación manual: 13 de 13.** Tres
tests nacieron de ahí — el más caro: con `testsrc` como video sintético los cinco
cuadros vecinos daban la misma diferencia que el correcto, así que un
`cuadro_offset` en 0 pasaba sin que nada fallara.

### Qué falta o no se probó

- **La pantalla no se abrió** (regla de trabajo). Lo que más puede fallar sin
  verla: que el reproductor arranque en el cuadro 612 y no en el 0 (la línea de
  tiempo de `vid1` va de 612 a 902, a propósito), y que los botones de evento
  salten al cuadro correcto con el offset puesto.
- **Se exportan dos videos por trabajo**, el limpio y el overlay con palitos:
  son el 87 % del peso. El overlay es lo que el reproductor muestra hasta que el
  **21** dibuje desde datos; cuando eso pase, `vid1` baja a **8,4 MB**. La
  desviación de la invariante 10 sigue abierta, igual que antes de este encargo.
- **Range/206 no se probó en Vercel**: el servidor de prueba devuelve 200. El
  cuadro a cuadro se apoya en `+faststart` y en que Chrome se baje los 6,4 MB.
- **No hay `master.mp4`** (ESPECIFICACION 4.2): el video exportado es H.264 CFR
  con `-g 12` y rotación aplicada, pero su hash no va a `analysis.json`. Es del 21.
- **`ListaTrabajos` no muestra los `avisos`** que `index.json` trae por trabajo.
  El componente es del 16 y no se tocó.
- **La demo se regenera a mano.** Si se re-sube `vid1`, el id cambia y hay que
  exportar el nuevo y borrar el viejo de `web/public/demo/`.

### Desviaciones

- **Del contrato, ninguna.** `transformacion.json`, `pose.json` e `index.json`
  no están en `CONTRATO.md` §Layout y no se agregaron: son artefactos de una
  exportación para mostrar, cada uno con su `schema` declarado adentro
  (`kinelab.transformacion/1.0.0`, `kinelab.pose2d/1.0.0`, `kinelab.demo/1.0.0`).
  Si el 21 sirve `pose.json` por la API, deja de ser un artefacto de demo.
  Pregunta para el orquestador.
- **Del prompt, dos de archivos.** `Reproductor.tsx` y `DosCuadros.tsx` reciben
  `primerCuadro` (default 0: el modo local no cambia en nada). Sin eso el
  reproductor pide el cuadro 672 en un video de 291 cuadros; la alternativa
  —renumerar los eventos— mostraría «cuadro 60» donde el análisis dice 672, que
  es exactamente lo que el resto del encargo evita. Y `layout.tsx` para el
  `noindex`, que el propio prompt pide.
- **Del prompt, una de alcance hacia arriba**: se exporta también el
  `overlay.mp4` recortado además del video limpio. Es la alternativa que el
  propio prompt prevé para el caso de que el 21 no haya cerrado.
- El `noindex` va también en modo local: una pantalla en `localhost` tampoco
  tiene nada que indexar, y un solo camino es menos que dos.

---

## 15 de septiembre de 2026 — encargo 20: el borrón es el obturador, no nuestro códec

Prompt: `docs/prompts/20-por-que-se-ve-borroso.md`. Informe:
`docs/informes/2026-09-15-20-por-que-se-ve-borroso.md`. **No se tocó ningún
archivo de código**: el punto 6 del prompt (subir la calidad del overlay en
`kinelab/explore.py`) esperaba a que cerrara el encargo 16, que toca ese mismo
archivo y sigue sin informe ni commit en `main`.

### Qué existe ahora

- **La respuesta medida a por qué las manos se ven borrosas en `vid1`**, con su
  banco reproducible en `data/incoming/borron-20/` (ignorado por git): once
  scripts en `scripts/`, seis figuras PNG y las medidas crudas en
  `medidas.json` y `fondo.csv`. Nada de esto entra al repo a propósito: es
  material de diagnóstico de un clip, no una herramienta del motor.
- **Un método de medición del barrido que sirve**, por si hace falta otra vez:
  ajuste por mínimos cuadrados de una rampa (meseta · rampa de ancho L ·
  meseta) al perfil de gris a lo largo de la dirección de viaje, sobre un borde
  del sujeto, con el cuadro rotado para que el movimiento quede horizontal. El
  mismo ajuste con el sujeto quieto da el ancho óptico del borde (2,5 px en
  este clip) y se resta.

### Medido

**1 · No es nuestra recompresión.** El `overlay.mp4` se reescribe con
`libx264 -preset veryfast -crf 20 -g 12` sin cambiar resolución. Comparado
contra el cuadro original decodificado, en el mismo tramo recodificado con la
receta exacta de `explore.py` pero **sin dibujar nada** (el esqueleto quemado
sube los indicadores de nitidez y arruina la comparación):

| caja | % del laplaciano del original que conserva | PSNR |
|---|---|---|
| manos | **94,1 %** | 34,6 dB |
| árbol (fondo quieto) | **91,0 %** | 30,6–32,8 dB |
| pasto (fondo quieto) | **93,0 %** | 33,8–36,2 dB |

La pérdida es **uniforme**: le pega tanto o más a lo que no se mueve. Control
del banco: el mismo tramo sin pérdida (`-qp 0 yuv444p`) da 53,3–53,9 dB, que es
el piso del viaje `yuv420p → bgr24 → yuv`, y los indicadores coinciden con el
original dentro del 0,1 %.

**2 · Es el obturador, y es nueve veces más grande.** Las manos vuelven casi al
mismo lugar en el impacto que en el address, así que la **misma caja de 400×400
px** mira la misma escena quieta y barrida:

| | laplaciano | alta frecuencia |
|---|---|---|
| cuadro 672 (address, manos a 3,7 px/cuadro) | 493,7 | 4,21 % |
| cuadro 741 (impacto, manos a 59,6 px/cuadro) | 231,1 | 0,68 % |
| | **−53,2 %** | **−83,9 %** |

En esos mismos dos cuadros, un borde del **fondo quieto** mide 2,0 y 2,5 px de
ancho de rampa, con el pico del gradiente en 49,5 y 50,0: la cámara no se movió
y el códec no cambió.

**3 · El obturador no está en ningún metadato y estimado da 1/100–1/140 s.**
Ni `ffprobe -show_frames`, ni el `moov` (sólo `com.android.version`,
`com.android.capture.fps` y `com.samsung.android.utc_offset`), ni el bloque
Exif de la miniatura embebida en el `udta` (seis etiquetas, ninguna es
`ExposureTime`). Del barrido, por ajuste de rampa sobre el borde del guante:

| cuadro | barrido | desplazamiento en un cuadro | fracción expuesta | obturador |
|---|---|---|---|---|
| 700 | 12,0 px | 19,7 px | 0,61 | 1/98 s |
| 710 | 11,0 px | 25,2 px | **0,44** | **1/138 s** |
| 741 | 26,8 px | 59,6 px | **0,45** | **1/134 s** |

Procedencia: `estimacion`. El 735 no es medible con este método: ahí el borde
del guante corre casi a lo largo del movimiento.

**4 · `CAPTURA.md` §Luz pide ≤ 5 px y este clip los viola por 5,4×.** Con
683,6 px/m (cadena de estatura 1196,4 px para 1,75 m), las manos en el impacto
van a 3578 px/s = 5,23 m/s, y 5 px exigirían **1/716 s**: 5 a 7 veces más corto
que lo que la cámara eligió. A 240 fps el mismo swing daría **6,7 px** con la
misma fracción, o 14,9 px con el tope duro de 1/240 s.

**5 · Qué compraría subir la calidad (medido, no aplicado).** Mismo tramo de
111 cuadros, extrapolado a los 1066 de `vid1` (hoy: 255 MB a 115,7 Mb/s, contra
93,3 MiB a 43,1 Mb/s del original):

| receta | manos | árbol | pasto | PSNR | overlay de vid1 | codificación |
|---|---|---|---|---|---|---|
| **crf 20 veryfast (hoy)** | 94,1 % | 91,0 % | 93,0 % | 34,6 dB | 255 MB | 20,3 s |
| crf 16 veryfast | 96,4 % | 93,5 % | 95,0 % | 36,7 dB | 400 MB | 21,3 s |
| crf 16 medium | 97,5 % | 95,6 % | 97,2 % | 37,2 dB | 408 MB | 46,9 s |
| crf 12 slow | 97,8 % | 96,6 % | 97,2 % | 38,9 dB | 610 MB | 154,6 s |

**El cambio, cuando `explore.py` esté libre**: en la única llamada a
`subprocess.Popen` de `render()` (`kinelab/explore.py:298`), `"-crf", "20"` →
`"-crf", "16"`. Nada más: no hay reescalado que sacar (el
`scale=trunc(iw/2)*2:trunc(ih/2)*2` es un no-op sobre 2160×3840, verificado con
`ffprobe` sobre el overlay) y el `-g 12` es del visor.

**6 · Un método que no sirve, anotado para que no se repita.** Correlacionar la
nitidez de la caja de manos contra la velocidad, cuadro por cuadro, da −0,15
sobre 109 cuadros, y los cuadros rápidos dan *más* laplaciano que los quietos
(539 contra 506): la caja se mueve con las manos y lo que domina el indicador
es qué hay detrás. Y la caja de fondo quieto no es regla fina: sobre los 1066
cuadros del clip su alta frecuencia oscila entre 24,5 % y 30,7 % por control de
tasa del teléfono y viento en las ramas. Vale como control **dentro de un mismo
cuadro**, no como serie.

Suite del motor: **272 en verde en 28,8 s** (línea de base de HEAD; no se tocó
código). El test rojo que reportó el informe del 11
(`test_datos_lista_un_ejemplo_de_otro_proceso`) ya no falla. `truth/` y `web/`
no se tocaron.

### Qué falta o no se probó

- **El punto 6 del prompt no se ejecutó** (encargo 16 abierto sobre
  `explore.py`). Aplicar el cambio y volver a medir se hace con
  `data/incoming/borron-20/scripts/recetas.py`.
- **`quality.blur_estimate` del contrato sigue en `null`** en los cuatro clips
  reales, y esta sesión fabricó exactamente el número que ese campo pide.
  `CAPTURA.md` §Luz ya tiene el umbral escrito (≤ 5 px) y hoy no lo comprueba
  ningún chequeo del gate.
- **El obturador es `estimacion`**, de tres bordes en tres cuadros de un solo
  clip. Para que fuera `medido_aqui` haría falta un objeto de velocidad
  conocida, o un clip del modo *Pro Video* con el obturador fijado.
- **No se midió cuántos grados de codo cuesta un barrido de 26,8 px** en este
  material. `banco/degrade.py` midió −2,5° con `rtmpose-m` a 21 px de
  desenfoque sintético; comparar contra qué verdad acá es otro encargo.
- **No se abrió el front** (regla de trabajo). Queda sin medir si parte de la
  blandura que ve Hernán la agrega el navegador al meter un 2160×3840 en un
  recuadro chico; se comprueba mirando el `overlay.mp4` en QuickTime a pantalla
  completa al lado del original.

### Desviaciones

- **Del contrato, ninguna.** No se escribió ningún campo nuevo ni se tocó
  ningún schema.
- **Del prompt, una**: el punto 6 (subir la calidad del overlay) quedó sin
  ejecutar por la regla de §En paralelo del propio prompt, con el cambio exacto
  y sus números escritos en el informe. No es un apartamiento: es la rama que
  el prompt previó.
- `CAPTURA.md` §Luz tiene una frase que la medición contradice —que al aire
  libre el teléfono elige ~1/2000 s y "sale gratis"— y **no se tocó**: ese
  archivo no era de este encargo. Va como pregunta al orquestador.

---

## 15 de septiembre de 2026 — encargo 19: el swing 3-D del mocap, girable en la pantalla

Prompt: `docs/prompts/19-visor-3d-del-mocap.md`. Informe:
`docs/informes/2026-09-15-19-visor-3d-del-mocap.md`. Corrió en paralelo con el
16 (`kinelab/`, contrato, `etiquetas.ts`, `TablaEventos.tsx`,
`tests/test_fase2.py`, `data/examples/`) y el 18 (`kinelab/events/`,
`sports/golf/events.py`, `tests/data/`), ninguno commiteado al cerrar.

### Qué existe ahora

- **`pose3d.json`, que lo escribe `truth/kinelab_truth/mocap.py`**: los 26
  puntos Halpe26 en **metros**, en el marco del arnés, cuadro por cuadro, con 3
  decimales. El marco, las unidades, la mano y el modelo de cámara van **como
  dato adentro del archivo** (`HARNESS_FRAME`, `PINHOLE_MODEL`,
  CONTEXTO.md §Sistemas de coordenadas), más fps, cuadros, nombres, huesos, los
  eventos del motor y los leídos en 3-D, la estatura del ASF, `APPROX_NOTES` y
  la atribución de CMU. 245 KB, 557 líneas (una por cuadro).
- **Las dos cámaras del protocolo dentro del archivo** (`camera_record`,
  `MocapPose.cameras`): `face_on` y `down_the_line` con su posición y objetivo
  en metros, su focal y la receta pinhole escrita en `modelo`. Los puntos 3-D
  son los mismos para las dos vistas, así que el visor puede ir a cualquiera de
  las dos desde cualquier trabajo.
- **Los rótulos y el indicador también son del archivo** (`rotulos()`,
  `indicador_lineas()`): las frases que la pantalla muestra las escribe quien
  produjo el dato, no la pantalla (la misma regla que `nota_fuente`, informe
  del 07).
- **`pose3d.json` en la lista blanca de `service/exploracion.py`**, con el
  comentario de por qué sólo puede tenerlo un trabajo medido en 3-D.
- **`web/src/components/Visor3D.tsx`**: esqueleto de 26 puntos y 27 huesos
  sobre grilla de suelo con escala en metros; arrastrar para girar, rueda para
  acercar; línea de tiempo, reproducir / pausa / cuadro a cuadro / cámara lenta
  / ir a address, top e impacto; botones «ver como face_on» y «ver como
  down_the_line»; y el indicador permanente del largo proyectado de la línea de
  caderas y de la de hombros. Canvas 2-D, **sin dependencias nuevas** (ADR-015).
  Aparece **sólo** si el trabajo tiene `pose3d.json`.
- **`web/src/lib/pose3d.ts`**: el tipo del archivo y la proyección, sin React y
  sin canvas, para poder correrla fuera del navegador. **`pose3d.verificar.mjs`**
  al lado: la corrida que compara el TypeScript del visor contra el `pose.npz`
  del arnés (`node --experimental-strip-types`).
- **8 tests nuevos** en `truth/tests/test_pose3d.py`, con la proyección rehecha
  a mano (sin `cv2`, sin `camera.py`): es el mismo código que hay en el visor.
- El punto de entrada en `page.tsx` son 7 líneas, entre las fotos por evento y
  «Con este archivo».

### Medido

**1 · El visor y el arnés son el mismo swing.** Proyectar el `pose3d.json` con
cada cámara del protocolo y comparar contra el `pose.npz` de esa vista, en las
cuatro combinaciones (los dos archivos × las dos cámaras), 448 × 26 puntos cada
una:

| | peor error |
|---|---|
| ver como `face_on` (f 3077,7 px) | **0,855 px** |
| ver como `down_the_line` (f 3193,5 px) | **0,922 px** |

Es el redondeo a milímetros del archivo y nada más: medio milímetro a 3 m con
esa focal vale 0,51 px. Se mide dos veces, con el mismo resultado: en Python
(`truth/tests/test_pose3d.py`, la fórmula escrita a mano) y en el TypeScript que
de verdad corre en la pantalla (`pose3d.verificar.mjs`, que además pasa por la
vuelta azimut/elevación que usan los botones).

**2 · La línea de caderas colapsa, y se ve.** Largo proyectado en porcentaje del
largo real, en el cuadro de address de cada trabajo:

| desde | caderas | hombros |
|---|---|---|
| `face_on` | **99,6–99,9 %** | 100,0 % |
| `down_the_line` | **4,2 % / 8,9 %** | 6,3 % / 3,0 % |

Los dos números de `down_the_line` son los dos trabajos (address 141 y 146: cada
vista detecta el suyo). En el **top**, con las caderas ya giradas, la misma línea
desde `down_the_line` vuelve a **75,9 %**: el colapso es del ángulo, no de la
línea. Es la misma geometría que el encargo 13 midió en °/s (3,6 px y 80× de
error), ahora sobre un humano y mirable.

**3 · El indicador no depende del zoom.** Con la focal × 0,3, 0,5, 1, 2 y 4 en un
ángulo que no es de ningún protocolo (az −37°, el 17°), la línea de caderas en el
top da **97,9 %** en las cinco, hasta 1e-9. Hay test en las dos implementaciones.

**4 · Girar no saca al sujeto del cuadro.** Barrido de 24 azimuts × 7
elevaciones con la focal del protocolo: el peor caso deja **98,2 %** de los
448 × 26 puntos dentro del cuadro (az 60°, elevación 5°; lo que sale son las
manos en el top). Con la rueda hacia abajo (0,3×) entra el **100 %** en todos.

**5 · Los dos ejemplos regenerados, con ADR-017 y con la escala del 14.**

| | `face_on` | `down_the_line` |
|---|---|---|
| address / top / impacto | 141 / 270 / 329 | 146 / **263** / 332 |
| backswing / downswing | 1075,0 / 491,7 ms | **975,0 / 575,0 ms** |

`down_the_line` tenía top 327 y downswing de 41,7 ms: son exactamente los
números que ADR-017 predijo. Y de paso, con la escala del 14,
`pelvis_sway_top_cm` del ejemplo pasa de −19,4 a **−18,0** contra una verdad
3-D de −17,69: el sesgo de la medición sola baja de −1,71 a **−0,31 cm**.

**6 · El archivo se sirve, y sólo donde tiene que estar.** `curl` al backend:
200, `application/json`, 251.649 bytes, y `GET .../archivos/pose.npz` sigue
dando 404 (la lista blanca no se ablandó). Un trabajo de celular
(`cortado.mp4`) no lista `pose3d.json` y pedirlo da 404: el visor no aparece.

Suites: arnés **37 en verde** (8 nuevos, 6,7 s), motor **272 en verde** (27 s),
`cd web && pnpm lint && pnpm build` limpios. **Mutación manual**: 5 de 5
mutaciones en `mocap.py` hacen fallar al menos un test (suelo con `argmax`,
fps + 1, x espejada al escribir, redondeo a centímetros, las dos cámaras iguales)
y 4 de 4 en el TypeScript rompen la verificación (grados por radianes,
`d = r × f`, `r = (0,1,0) × f`, focal fija en el indicador). La cuarta del
TypeScript **no se cazaba** hasta agregar el chequeo de invariancia al zoom:
está agregado en las dos implementaciones.

### Qué falta o no se probó

- **La pantalla no se abrió** (regla de trabajo). Lo que más puede fallar sin
  verla: el alto del recuadro vertical sumado a lo que ya hay arriba, y que las
  flechas del teclado sólo mueven el visor cuando el recuadro tiene el foco (se
  maneja en el propio div y con `stopPropagation`, justamente para no mover el
  reproductor de arriba a la vez).
- **El suelo del visor es el cero del trial, no el piso anatómico.** `y = 0` es
  el punto más bajo de **todo** el trial —la punta del pie izquierdo en el
  cuadro 426, ya en el acompañamiento— y en el address los pies quedan
  **8,9 cm** por encima: el esqueleto de CMU no apoya la planta. Está medido y
  declarado dentro del archivo (`suelo`), y la pantalla lo dice en «de dónde
  sale cada número». No se tocó `to_harness_frame`: ese marco es el de todas las
  métricas y moverlo movería todo.
- **No hay test permanente del lado del navegador.** `pose3d.verificar.mjs` se
  corre a mano; montar un runner en `web/` es ADR-015 (nada nuevo sin preguntar).
  El guardián permanente es el test de Python, que fija la fórmula que el
  TypeScript transcribe.
- **El visor no dibuja el palo** (el mocap no lo tiene) ni una traza de las
  manos, que es lo que haría ver el plano del swing en 3-D.
- **Nada sincroniza el visor con el reproductor de arriba**: cada uno tiene su
  línea de tiempo y su cuadro.
- El indicador se calcula en el cuadro que se está viendo. El colapso se ve en
  el address; el visor arranca ahí a propósito.

### Desviaciones

- **Del contrato, ninguna.** `pose3d.json` no está en `CONTRATO.md` §Layout y no
  se agregó: es un archivo del arnés en una carpeta de exploración, con su
  propio `schema` (`kinelab.pose3d/1.0.0`) declarado adentro. Si algún día un
  video produjera 3-D —dos cámaras calibradas— ahí sí habría que meterlo en el
  contrato. Queda como pregunta para el orquestador.
- **Del prompt, una de archivos**: además del componente, dos archivos nuevos en
  `web/src/lib/` (`pose3d.ts` con la proyección pura y `pose3d.verificar.mjs`
  con la corrida). Razón: sin ellos la matemática del visor sólo se podría
  verificar abriendo el navegador, que es lo que la regla de trabajo prohíbe.
  Ninguno pisa un archivo de otro encargo.
- `tests/test_service.py` no se tocó (`tests/` no era de este encargo): que la
  lista blanca sirva `pose3d.json` está verificado por `curl`, no por test.

---

## 15 de septiembre de 2026 — encargo 13: la ganancia muere, el sub-cuadro tiene MDC, y el encuadre no sale del ruido relativo

Prompt: `docs/prompts/13-arnes-ganancia-subcuadro-encuadre.md`. Informe:
`docs/informes/2026-09-15-13-arnes-ganancia-subcuadro-encuadre.md`. Corrió en
paralelo con el 12 (`CAPTURA.md`, `docs/filmacion-s22.md`,
`docs/checklist-captura.md`, `tests/test_service.py`), el 14
(`truth/kinelab_truth/mocap.py`, `kinelab/metrics/core.py`, `CONTRATO.md`,
`data/examples/`) y el 15 (`sports/golf/events.py`, `kinelab/events/`,
`tests/test_fase2.py`, `DECISIONES.md`), ninguno de los tres commiteado al
cerrar.

### Qué existe ahora

- **El arnés mide velocidad angular 3-D.** `truth/kinelab_truth/swing.py`:
  `segment_rate_3d` (`|dû/dt|` de una línea, en °/s), `truth_gain` (picos y
  cocientes en la misma ventana address→follow_end que usa el motor) y
  `gain_params`, que arma un swing con **cocientes 3-D pedidos** y devuelve los
  **conseguidos** — lo conseguido es la verdad que se reporta, nunca el
  objetivo. Para eso la amplitud del arco de las manos dejó de estar quemada
  (`arm_arc_top_deg` / `arm_arc_end_deg`, con los valores de siempre como
  default: nada del banco viejo se movió).
- **Tres barridos nuevos en `truth/kinelab_truth/harness.py`**: `gain_table`,
  `subframe_table` y `framing_table`, más `Condition.noise_px` (ruido absoluto
  en px, además del relativo de ESPECIFICACION 3.1) y `realize_seeds`, que
  proyecta **una vez por condición** en vez de una por semilla. El resultado por
  semilla no cambió: la tabla de las doce métricas reproduce exactamente el
  `mdc.yaml` de HEAD, y hay un test que fija el orden del sorteo (primero el
  jitter de los cuatro eventos, después el ruido).
- **`sports/golf/mdc.yaml` tiene cuatro secciones**: `metrics` (como siempre),
  `gain`, `events` y `framing`. Lo sigue escribiendo el arnés, nunca a mano.
- **`truth/kinelab_truth/__main__.py`** inyecta lo del deporte (segmentos de la
  ganancia, estimador del sub-cuadro, parámetros de evento, métricas muertas).
  El arnés no importa ningún deporte.
- **13 tests nuevos** en `truth/tests/test_gain_subframe.py`.
- **Un bug arreglado que no estaba en el prompt**: al regenerar la tabla, las
  filas de las métricas que el arnés ya mató desaparecían (el arnés itera el
  registro, y una métrica muerta no está en el registro), y la fila ausente las
  **revive** sin MDC en la corrida siguiente (`_m` sólo mata si la fila existe
  con `views: []`). `DEAD_METRICS` lleva ahora unidad y razón, y sobreviven.

### Medido

**1 · La ganancia muere en las dos vistas.** Tres bancos con cocientes 3-D
conocidos (1,5 / 1,0 / 2,0), 16 semillas, tolerancia 0,3 (ancho de rango
declarado, `estimacion`):

| vista | |sesgo| máx `pelvis_to_torso` | |sesgo| máx `torso_to_arm` |
|---|---|---|
| `face_on` | **4,796** | **3,558** |
| `down_the_line` | **1,815** | **1,286** |

El porqué, medido: las tres líneas giran alrededor del eje vertical y en el
plano de imagen eso es degenerado. Desde `down_the_line` la línea de caderas
apunta a la cámara, su proyección baja a **3,6 px** y el ángulo aparente se
dispara a **11110 °/s contra 139,6 verdaderos (80×)** — el mismo número en los
tres bancos. Desde `face_on` pasa lo contrario: la de caderas se queda
horizontal y casi no gira (86,3 contra 139,6), y la de hombros salta
**74,0 → 120,1 → 572,3** para verdades 139,6 → 209,5 → 279,3 (7,7× medido para
2,0× verdadero), porque con 90° de giro pasa por su propio colapso. **El número
de `summary.gain` no es la ganancia de velocidad angular: es el largo proyectado
del segmento.** No se borró (el prompt lo prohíbe); la lista de los ocho
archivos que la tocan está en el informe, con el aviso de que `gain()` es
también quien calcula `sequence_order`, que sí está en el contrato.

**2 · El instante sub-cuadro vive, con MDC.** Verdad: el mismo cruce geométrico
a 2400 fps (`t* = 2,359769 s` en `face_on`). 16 semillas por fila.

| | 240 fps | 120 fps | 60 fps | 30 fps |
|---|---|---|---|---|
| sesgo (ruido nominal 0,6 %) | −0,032 ms | −0,217 ms | −0,006 ms | −0,251 ms |
| **MDC** | **2,829 ms** | **2,927 ms** | **2,909 ms** | **1,974 ms** |
| MDC en cuadros | 0,679 | 0,351 | 0,175 | 0,059 |
| ±1 cuadro entero, para comparar | 4,2 ms | 8,3 ms | 16,7 ms | 33,3 ms |

- El sesgo va de **−0,42 a +0,01 ms** en todo el barrido (≤ 0,05 cuadros); sin
  ruido, ≤ 0,10 ms.
- El MDC **casi no depende del fps** (el error en tiempo es σ_px / velocidad, y
  la velocidad en px/s no cambia con la tasa), y es **invariante al tamaño**:
  811, 406, 203 y 89 px dan el mismo número exacto.
- `down_the_line` sale `null` por vista, **16 de 16** (invariante 6). Único caso
  con nulos por otra razón: 240 fps con 1,2 % de ruido, 2 de 16.
- **La banda que el motor declara por clip nunca es optimista**:
  `uncertainty_frames` contra la SD medida da **1,18× a 9,23×**.

Está en `mdc.yaml` §`events.impact.subframe`. **No llega a `analysis.json`**: el
registro es de métricas y no tiene lugar para eventos, y quien tendría que leer
la tabla es `sports/golf/events.py`, prohibido en este encargo (lo toca el 15).

**3 · El umbral de encuadre no sale del modelo de ruido de la spec.** Con σ
proporcional a la altura del cuerpo (ESPECIFICACION 3.1), **el MDC es
exactamente invariante al tamaño**: 100, 200, 400 y 800 px dan valores idénticos
hasta el último decimal en las doce métricas. Es álgebra, no semillas: el error
en cm es (σ/altura) · estatura · 100 y la altura se cancela. Ninguna métrica
cruza su tolerancia. Hay un test que lo fija.

Con σ **fijo en px** —el único modelo que puede dar un número— la métrica que
manda es `head_lift_top_cm` en los dos casos:

| σ | de dónde sale | propuesta `body_height_px_min` | rango de cruces |
|---|---|---|---|
| 4,866 px | el mismo ruido absoluto que el nominal relativo a 811 px | **717 px** | 394–717 |
| 2,3 px | mediana de lo medido en los clips reales (1,204 · 2,274 · 2,969) | **345 px** | 188–345 |

Las cuatro duraciones, `tempo_ratio` y el sub-cuadro **no cruzan nunca**: su MDC
es cuantización de cuadros, no tamaño.

**Los cuatro clips reales pasan los dos umbrales con margen**: 973 px (FHD 30
del 7/9), 1083 (vid2), 1104 (vid1), 1132 (vid3). Y eso desarma la lectura por
fracción de cuadro: esos clips ocupan 28,2–29,5 % del alto (UHD) y 41,9 % (FHD),
lejos del 80–90 % de `CAPTURA.md`, y aun así el encuadre no es lo que los
limita. **En 4K, 28 % del cuadro son 1104 px, más que el 80 % de un 1080p
(864 px).** Lo que decide es `body_height_px`; el gate hoy tiene
`body_height_frac_min`. **No se fijó nada en el gate** (decisión del
orquestador): `sports/golf/config.py` sigue con `None`.

Suites: **29 en verde** en el arnés (13 nuevos, 9,1 s), **272** en el motor
(40,4 s). El arnés corre entero en **62 s**. **Mutación manual**: de seis
mutaciones sobre el código nuevo, cinco hacen fallar al menos un test; la sexta
—quitar el giro del eje de viaje— es un no-op real (el cruce por cero de una
señal negada cae en el mismo lugar).

### Qué falta o no se probó

- **La ganancia sigue en el código y en el front.** `hip_line_rate_deg_s` y
  `shoulder_line_rate_deg_s` se muestran al entrenador como «rotación aparente
  de caderas / hombros» (`web/src/lib/etiquetas.ts:64-65`,
  `web/src/components/TablaEventos.tsx:36`) y ahora está medido que el pico es
  un artefacto. Decisión del orquestador; el informe lista los ocho archivos.
- **El MDC del sub-cuadro no viaja a `analysis.json`.** Faltan pocas líneas en
  `sports/golf/events.py`, que este encargo no podía tocar.
- **La tabla se regeneró con los encargos 12, 14 y 15 ya commiteados**, que
  cerraron mientras esta sesión corría. El 14 cambia la escala en cm y eso
  **mueve los ocho MDC en cm entre 1 y 9 %**: `pelvis_sway_top_cm` 2,870 →
  **2,841**, `pelvis_sway_impact_cm` 2,481 → **2,416**, `pelvis_lift_top_cm`
  2,822 → **2,769**, `thorax_sway_top_cm` 3,462 → **3,388**,
  `thorax_lift_top_cm` 2,889 → **2,819**, `pelvis_thrust_top_cm` 2,867 →
  **2,610**, `head_sway_top_cm` 3,824 → **3,779**, `head_lift_top_cm` 4,501 →
  **4,382**. Duraciones, veredicto de la ganancia y veredicto del sub-cuadro, sin
  moverse. **Nada avisa cuando eso pasa**: `mdc.yaml` no guarda contra qué
  versión del motor se midió. Queda como pregunta para el orquestador.
- **El barrido de tamaño no toca el estimador.** Es nivel 0: proyección y ruido
  gaussiano. Cómo depende de verdad el error de RTMPose del tamaño del sujeto lo
  mide `banco/scale_sweep.py` sobre un cuadro real, y necesita los ONNX; no se
  corrió.
- **La cámara virtual sigue con intrínsecos `sin_verificar`** (derivados del
  campo de visión nominal, `truth/cameras/iphone17pro-1080p120.yaml`): toda la
  tabla hereda esa procedencia.
- El front no se abrió ni se tocó `web/` ni `service/` (regla de trabajo).

### Desviaciones

- **Del contrato, ninguna.** `mdc.yaml` no es parte del contrato de datos: es la
  salida del arnés, y la escribe él.
- **De ESPECIFICACION 3.1, una**: la spec pide ruido gaussiano «con σ escalado
  por altura del cuerpo en px», y con ese modelo el punto 3 del encargo **no
  tiene respuesta** (el MDC no depende del tamaño, demostrado y con test). Se
  **agregó** —no se reemplazó— un modelo de σ absoluto en px, y los dos van en
  la tabla con su nombre. Sin él no hay umbral de encuadre posible.
- Del prompt, una de alcance: el MDC del sub-cuadro **no** llega a
  `datos-eventos.json` ni a `analysis.json`. El propio prompt preveía la
  alternativa («si no, en `truth/reports/` y anotado en el informe») y es la que
  aplica: el registro no tiene lugar para eventos y el archivo que habría que
  tocar es de otro encargo.
- Del prompt, otra: no se tocó `sports/golf/metrics.py` para registrar la
  ganancia, porque murió. Sí se le cambió una línea por el bug de las métricas
  muertas (`DEAD_METRICS` guarda la unidad).

---

## 15 de septiembre de 2026 — encargo 14: la escala en cm sale del cuadro más extendido

Prompt: `docs/prompts/14-escala-en-cm.md`. Informe:
`docs/informes/2026-09-15-14-escala-en-cm.md`. Commit `5991922` (datos, motor,
arnés, contrato y tests) y el de cierre con `ESTADO.md` y el informe. Corrió en
paralelo con el 12 (ya commiteado), el 13 (`truth/` salvo `mocap.py`,
`sports/golf/mdc.yaml`, `sports/golf/metrics.py`, `kinelab/metrics/` salvo
`core.py`) y el 15 (ya commiteado).

### Qué existe ahora

- **Los diez «Swing» del sujeto 64 de CMU en el repo** (`64_03`…`64_10` nuevos,
  2,7 MB), bajados a mano uno por uno, con bytes y sha256 en
  `data/examples/cmu-mocap/ATRIBUCION.md`, que dice además por qué esos diez y
  ninguno de los otros veinte.
- **`cd truth && .venv/bin/python -m kinelab_truth.mocap 64 --escala`**: la
  tabla de escala, ~30 s, reproducible desde el repo. Por trial, el cociente
  cabeza→tobillos en address / estatura y los divisores de seis candidatas; al
  final, sesgo medio y límites de acuerdo contra la verdad 3-D por métrica y
  candidata, con el veredicto del criterio del encargo. `scale_table()` acepta
  una lista de trials (los tests corren dos).
- **La escala nueva, en `kinelab/metrics/core.py`**: `stature_chain_px` y
  `MetricContext.scale_px`. El divisor de toda métrica en cm es el **máximo,
  dentro de la repetición, de la suma de largos proyectados de
  tobillo→rodilla→cadera→hombro→cabeza** (puntos medios de los dos lados), con
  una mediana móvil de 0,25 s (`SCALE_SMOOTH_S`) antes del máximo. Una escala
  por repetición. Si la cadena no se puede medir en ningún cuadro, cae a la
  altura cabeza→tobillos del cuadro cero, que es la convención anterior.
- **`CONTRATO.md` §La escala**, nueva, con la definición, la tabla de candidatas
  y el residual medido; la `definition` del ejemplo del registro actualizada; y
  §Versionado con el bump decidido (`metric_version` minor en las métricas en
  cm, `registry_version` minor) y las tres razones por las que no es major.
- `tests/test_escala.py` (8) y tres tests nuevos en `truth/tests/test_mocap.py`.
- Arreglado de paso en `mocap.py`: la tabla de `--nivel1` reventaba al imprimir
  una fila con `motor_2d` en `null` (`pelvis_thrust_top_cm` desde `face_on`,
  que volvió al registro cuando el 13 le puso vista en `mdc.yaml`).

### Medido

**Los diez trials, `face_on`.** La altura cabeza→tobillos del address —el
divisor anterior— mide **0,8907 ± 0,0062** de la estatura del ASF
(0,8817–0,9038): la escala vieja sobre-leía **×1,1227**. Un solo sujeto.

| candidata | px (media) | \|sesgo\| medio | cumple el criterio |
|---|---|---|---|
| **a** cabeza→tobillos en address (la anterior) | 1532,5 | 1,035 cm | — |
| **b** cadena de segmentos en el address | 1533,1 | 1,032 cm | no |
| **c** máxima extensión vertical de la repetición | 1584,1 | 0,777 cm | no |
| **d** **máximo de la cadena en la repetición** | **1648,4** | **0,493 cm** | **SÍ** |
| e ídem d, desde el talón (informativa) | 1740,5 | 0,407 cm | sí |
| z la escala exacta (sólo con verdad 3-D) | 1720,6 | 0,399 cm | sí |

El umbral era 0,517 (la mitad de 1,035) y ninguna métrica podía empeorar más de
1 cm: `d` da 0,493 y empeora como mucho 0,013 cm.

- **Sumar largos de segmento en el address no arregla nada** (1533,1 contra
  1532,5 px): en `face_on` el golfista se agacha **hacia la cámara**, y la
  cadena se acorta en la imagen exactamente lo mismo que la vertical. Lo que
  arregla es mirar el cuadro extendido.
- **La fila `z` es el piso: 0,399 cm** de error de **proyección**, que ninguna
  escala puede tocar. `d` cubre el 85 % de lo recuperable. Lo que sobra es casi
  todo `head_sway_top_cm`, cuyo piso ya es −1,08.
- **`d` está a 0,3 % de su techo geométrico**: el +4,4 % residual es que la
  cadena arranca en el tobillo y la estatura declarada arranca en el piso.
- Por métrica (sesgo antes → ahora, MDC): `pelvis_sway_top` −1,83 → **−0,38**
  (2,87) · `pelvis_sway_impact` +0,57 → **+0,08** (2,42) · `pelvis_lift` −0,07 →
  −0,09 (2,82) · `thorax_sway` −1,55 → **−0,75** (3,46) · `thorax_lift` −0,17 →
  +0,05 (2,89) · `head_sway` −2,35 → **−1,53** (3,82) · `head_lift` +0,69 →
  +0,57 (4,50). Todos por debajo de su MDC antes y después.

**La mediana móvil de 0,25 s, medida**: una cabeza saltada 200 px durante 1 a 15
cuadros infla el máximo crudo un **+6,6 %** (las siete métricas, −6,2 %) y la
ventana lo absorbe entero (0,0 %); una racha de 31 cuadros (0,258 s) pasa, como
debe. En datos limpios la ventana cuesta 0,3 px sobre 1649.

**Las dos corridas reales, con el cambio aislado** (misma pose, mismos eventos,
sólo el divisor):

| | `cortado.mp4` | `vid1.mp4` |
|---|---|---|
| escala vieja → nueva | 868,9 → **1089,6** px | 1052,9 → **1196,4** px |
| factor | **×1,2539** | **×1,1363** |
| cuadro del máximo | 75 (el último de la rep) | 818 (la rep termina en 842) |

`pelvis_sway_impact_cm` 7,5 → **6,0** y 14,3 → **12,6**; `pelvis_lift_top_cm`
−0,4 → −0,3 y −11,7 → **−10,3**; `head_sway_top_cm` 3,4 → 2,7 y −9,2 → **−8,1**.
El movimiento más grande es 1,7 cm, por debajo del MDC de esa métrica (2,42).

**La corrección en los clips de Hernán es el doble que en el mocap** porque su
address está mucho más escorzado: en `cortado.mp4`, del address al cuadro
extendido, cadera→hombro pasa de 320 a 386 px y hombro→cabeza de 132 a 245. Su
address mide el **79 %** del cuerpo extendido, contra el 93 % del golfista de
CMU. **No es un artefacto del recorte**: el original de 9 s del mismo swing
(265 cuadros) da ×1,2634 con el máximo en el cuadro 206, 0,8 % de diferencia.

Suites: motor **272 en verde** (39 s), arnés **29 en verde** (9 s).

### Qué falta o no se probó

- **Los bumps de versión no se pudieron escribir**: `metric_version 1.0.0 →
  1.1.0` en las ocho métricas en cm y `registry_version 0.1.0 → 0.2.0` viven en
  `sports/golf/metrics.py` y `kinelab/metrics/registry.py`, que son del 13. El
  texto exacto, incluida la `definition` nueva de `pelvis_sway_top_cm`, está en
  el punto 1 de «queda abierto» del informe, listo para pegar. `_m()` además no
  recibe `metric_version` todavía.
- **`metric_version` no viaja al `analysis.json`**: el contrato lo declara por
  métrica y el sextuplo no lo lleva, así que el bump que avisa que estos siete
  números cambiaron no se puede leer desde un análisis. Toca `analysis.py` y
  `contract/schema.json`.
- **La escala usada no queda registrada**: `quality.body_height_px` informa la
  serie vieja, que ya no es el divisor de nada. Un `quality.scale_px` con el
  cuadro del máximo haría auditable el número que multiplica a siete métricas.
- **`core.py` importa `_rolling_nanmedian`, que es privada de
  `kinelab/perception/framing.py`.** Duplicarla habría sido peor (es el caso del
  `_ascii` del encargo 07). Cuando `framing.py` esté libre: hacerla pública y
  mudar `stature_chain_px` al lado de `body_height_px`, que es su casa.
- **De los clips de Hernán no hay verdad 3-D.** El ×1,25 se apoya en la
  geometría (la cadena es cota inferior de la estatura en px y no puede
  alargarse), no en una medición contra la verdad.
- Los eventos de las dos corridas reales cambiaron respecto de `ESTADO` anterior
  (`cortado` top 39 → 33, `vid1` top 726 → 722): es el encargo 15 (`0f8f18e`),
  no éste. Por eso el antes/después del informe es el aislado.
- El ejemplo de la pantalla se regeneró con la escala nueva:
  `pelvis_sway_top_cm` pasa de −19,4 a **−18,0** contra una verdad 3-D de
  −17,69 (sesgo −1,71 → **−0,31**).
- El front no se abrió ni se tocó `web/` ni `service/` (regla de trabajo).

### Desviaciones

- Ninguna del contrato: no se renombró ningún campo ni cambió ninguna unidad, y
  `schema_version` de `analysis.json` sigue en 1.2.0. §Desviaciones no recibió
  entrada porque una candidata cumplió el criterio; si ninguna lo hubiera
  cumplido, el sesgo entraba ahí con su número.
- Del prompt, una de alcance: los bumps de versión y la `definition` de
  `sports/golf/metrics.py` quedaron escritos en el informe y no en el código,
  porque ese archivo lo toca el 13 (el prompt lo preveía para la `definition`;
  los bumps también caen ahí).
- Del prompt, otra: se midieron **seis** candidatas y no cuatro. Las dos de más
  (la cadena desde el talón y la escala exacta) no compiten: la primera mide una
  aproximación de nuestro propio mapeo y la segunda sólo existe porque hay verdad
  3-D. Están para que se lea cuánto del error es proyección y cuánto es escala.

---

## 15 de septiembre de 2026 — encargo 15: el top es el cambio de sentido más lejano (ADR-017)

Prompt: `docs/prompts/15-top-desde-down-the-line.md`. Informe:
`docs/informes/2026-09-15-15-top-desde-down-the-line.md`. Commits `0f8f18e`
(regla, tests, fixture y ADR-017) y el de cierre con `ESTADO.md` y el informe.
Corrió en paralelo con el 12 (`CAPTURA.md`, `docs/`, `tests/test_service.py`,
ya commiteado), el 13 (`truth/`, `sports/golf/mdc.yaml`) y el 14
(`truth/kinelab_truth/mocap.py`, `kinelab/metrics/core.py`).

### Qué existe ahora

- **ADR-017 en `DECISIONES.md`**, citando ADR-008: entre address e impacto, el
  top es el cambio de sentido de la velocidad proyectada de las manos en el que
  **están más lejos** de su posición de address (distancia en el plano de
  imagen), no el último.
- **`kinelab/events/primitives.py`**: `direction_change` (el último) se parte en
  `direction_changes`, que enumera, y `direction_change_farthest`, que elige. La
  vieja **no queda en el motor**. El primer segmento —de `after` a `after + 1`—
  no cuenta como cambio de sentido: devolvía el propio cuadro del address.
- **`sports/golf/events.py`**: el top usa el selector nuevo con la excursión =
  la distancia de las manos al address, **la misma señal cuyo mínimo ya elegía
  el impacto**. El `method` del evento dice `direction_change_farthest`.
- **`tests/data/`** (nuevo, 184 KB): el `pose.npz` del mocap CMU 64_01 en las
  dos vistas, con `README.md` (sha256, la atribución textual de CMU y el comando
  para regenerarlo). Es un archivo y no se genera en el test porque
  `kinelab_truth` vive en `truth/`, con su propio entorno a propósito
  (invariante 14).
- Tres tests nuevos en `tests/test_fase2.py`: el mocap desde las dos vistas, un
  caso construido con tres cambios de sentido donde el último no es el más
  lejano, y el borde del primer cuadro.

### Medido

**Mocap CMU, 120 fps, contra la verdad 3-D del propio mocap** (`events_3d`,
criterio `top_far`, que no pasa por la cámara):

| trial · vista | address | top antes | **después** | verdad 3-D | impacto | backswing (ms) | downswing (ms) |
|---|---|---|---|---|---|---|---|
| 64_01 `face_on` | 141 | 270 | **270** | 269 | 329 | 1075,0 | 491,7 |
| 64_01 `down_the_line` | 146 | 327 | **263** | 269 | 332 | 1508,3 → **975,0** | 41,7 → **575,0** |
| 64_02 `face_on` | 172 | 305 | **305** | 306 | 373 | 1108,3 | 566,7 |
| 64_02 `down_the_line` | 196 | 373 | **304** | 306 | 376 | 1475,0 → **900,0** | 25,0 → **600,0** |

Verdad 3-D de las duraciones: 1033,3 / 508,3 ms (64_01) y 1033,3 / 558,3
(64_02). **Desde `down_the_line` el error del top pasa de +58 y +67 cuadros a
−6 y −2**; desde `face_on` no se mueve ni un cuadro.

**Los cuatro clips reales del S22, todos `face_on`**: `cortado.mp4` 39 → **33**,
`20260907_170638.mp4` 141 → **137**, `vid1.mp4` 726 → **722**, `vid2.mp4` 115 →
**115**; `vid3.mp4` sigue con 0 repeticiones. Address e impacto, iguales.

**Tres de los cuatro se movieron y la causa no es la regla**: la señal es el
centro de las dos muñecas y en el top la izquierda se pierde (confianza
0,34–0,54, saltos de hasta 300 px entre cuadros). Con la muñeca **derecha**
sola —limpia, confianza ≥ 0,53— hay **un solo** cambio de sentido y las dos
reglas dan el mismo cuadro en los cuatro clips: 36, 139, 722, 114. Contra esa
referencia, la regla vieja erraba +3 / +2 / +4 / +1 y la nueva −3 / −2 / **0** /
+1.

**Lo anclado al top se mueve con él** (altura declarada 1,75 m en los cuatro):
`pelvis_sway_top_cm` 0,7 → −5,2 en `cortado` (5,9 cm, contra un MDC de 2,87),
−0,7 → −4,6 en el original, −1,5 → −3,5 en vid1; `tempo_ratio` de vid1, 3,6 →
2,63. Las duraciones siguen en `null` en los cuatro (`fps_min` 120) y ninguna
métrica quedó con `judgment_allowed` verdadero.

**Suite del motor: 264 en verde** al commitear la regla (261 + 3 nuevos) y
**272** al cerrar, con el trabajo sin commitear del 12, 13 y 14 adentro; arnés
**29** (lo amplía el 13, no se tocó acá). Los tres bugs inyectados —elegir el
más cercano, elegir el último, incluir el primer segmento— ponen en rojo 2, 2 y
1 test.

**De punta a punta con el CLI**, `datos` sobre los cuatro clips, con su camino
declarado: `cortado.mp4` top 1,100 s (cuadro 33, backswing 866,7 / downswing
366,7 ms, tempo 2,36); `20260907_170638.mp4` top 4,567 s (137, 866,7 / 333,4,
tempo 2,6); `vid1.mp4` top 12,028 s (722, 833,0 / 316,5, tempo 2,63, **una sola
repetición**); `vid2.mp4` top 1,916 s (115, sin cambios). Correr el modelo de
nuevo sobre cada clip devuelve exactamente los mismos cuadros que el
re-análisis desde el `pose.npz` guardado.

**En vid1 la elección es frágil**: los tres cambios de sentido están a 590,3 /
587,0 / 587,7 px del address —3,3 px entre el primero y el último— y el ruido
por cuadro que el propio motor estima en ese clip es **2,27 px**. Gana el 722
por 2,6 px. No hay regla de empate para el top; queda como pregunta en el
informe.

### Qué falta o no se probó

- **La señal de manos es lo que limita el top en `face_on`, no la regla**
  (arriba). Un `hands_center` pesado por confianza cambiaría los cuatro clips
  reales — y también el address y el impacto, que salen de la misma señal. El
  prompt prohibía tocarlos: **decisión del orquestador**.
- **ADR-008 dice "inflexión de la segunda derivada"; el código detecta el cambio
  de sentido** (cero de la velocidad proyectada), que es lo que dice la
  definición de GolfDB. Anotado en ADR-017, sin resolver. `d2_inflection` existe
  en el motor y hoy no la usa ningún evento.
- **El error del top sigue sin medirse contra GolfDB** (ESPECIFICACION 2.5).
- **`data/examples/analysis.example.json` quedó con `"method":
  "direction_change"`** en sus tres eventos top. Es de `data/examples/`, que
  toca el encargo 14: no se editó. El schema no valida el contenido de `method`,
  así que no rompe ningún test.
- **Las tomas ya analizadas conservan su top viejo** hasta que se re-analicen
  (invariante 18): las nueve subidas de `data/exploracion/` del 12 al 14/9 y los
  dos ejemplos de mocap del encargo 07 — el de `down_the_line` con el top en
  327, justo el caso que este encargo arregla. No se rehicieron porque el
  ejemplo lo escribe `kinelab_truth.mocap`, que está editando el encargo 14. Los
  cuatro clips reales sí se rehicieron.
- El front no se abrió ni se tocó `web/` ni `service/` (regla de trabajo).

### Desviaciones

- Ninguna del contrato: `events[].top` conserva su forma y `method` es un
  string libre en el schema.
- Del prompt, una: además de la regla hubo que fijar el **borde del primer
  segmento**, que no estaba en el pedido. Lo destapó la corrida real (`vid1.mp4`
  inventaba una repetición con top = address). Está en ADR-017 y tiene test.

---

## 15 de septiembre de 2026 — encargo 12: lo medido entra a los documentos de captura

Prompt: `docs/prompts/12-captura-docs.md`. Informe:
`docs/informes/2026-09-15-12-captura-docs.md`. Encargo de documentos: el único
código que cambió es una fecha en un test. Corrió en paralelo con el 13
(`truth/` salvo `mocap.py`, `sports/golf/mdc.yaml`, `sports/golf/metrics.py`),
el 14 (`truth/kinelab_truth/mocap.py`, `kinelab/metrics/core.py`, `CONTRATO.md`,
`data/examples/`) y el 15 (`sports/golf/events.py`, `kinelab/events/`,
`tests/test_fase2.py`, `DECISIONES.md`), que al cerrar esta sesión todavía
tenían trabajo sin commitear en el árbol.

### Qué existe ahora

- **`CAPTURA.md` con lo del 07 y lo del 11 adentro**, en cuatro secciones:
  - **§Presupuesto de datos** tiene columna `Procedencia` y dos filas medidas:
    **UHD 60 HEVC del S22 — desaconsejado**, 165 MB por 30 s (~3,3 GB la sesión
    de 20 clips), y Video FHD 30 H.264, 68 MB (~1,4 GB). Debajo, la subsección
    «UHD 60 está desaconsejado, y está medido por qué», con los tres números:
    no agrega precisión (el recorte entra a `rtmpose-m` a 192×256 y el bbox ya
    se reducía 5,24× en FHD, 5,7–6,0× en UHD), cuesta 2,15× por cuadro y 4,29×
    por segundo de movimiento real, y cuesta **2,4×** de disco.
  - **§Encuadre**: el 80–90 % queda como **objetivo**, con la nota medida del
    07 —3078 px de focal para el 80 % a 3 m, ~2,1× la lente principal de un
    celular; con esa lente habría que estar a ~0,8 m— y los cuatro valores
    reales del 11: **28,2 / 28,7 / 29,5 %** en UHD y **41,9 %** en FHD. La
    regla operativa es acercar el trípode todo lo que permita tener pies y palo
    del top adentro. **Ningún umbral fijado**: el número sale del barrido de
    tamaño de sujeto del arnés (encargo 13), y lo que el motor mide es
    `body_height_px`, no la fracción del cuadro.
  - **§Transferencia**: el encabezado ahora dice un camino de referencia **por
    dispositivo** (iPhone → AirDrop; S22 → cable desde `DCIM/Camera`); la fila
    de la tabla de terceros pasa a «WhatsApp **como video**»; y hay una tabla
    nueva medida sobre el S22 con tres filas y su procedencia — cable
    (referencia), **WhatsApp como documento: intacto** (HEVC a 43–47 Mb/s,
    `udta` de 1,02–1,10 MB, mismo orden de hijos del `moov`), WhatsApp como
    video: recomprimido, **no medido acá**.
  - **§Lo que queda por verificar** se parte en dos: «Con el Galaxy S22 Ultra,
    que es el teléfono que hay» y «Con el iPhone, si alguna vez hay uno». El
    bloque nuevo deja escrito que **ningún modo Video del S22 llega a 100 fps**
    (tope 60, medido 60,026 en UHD y 29,998 en FHD) y que **el cronómetro en
    Slow motion FHD 240 es lo único que puede dar un clip que pase el gate**.
- **`docs/filmacion-s22.md` reescrita entera.** El cronómetro en Cámara lenta
  FHD 240 es el paso 1 con su lista (10–15 s, sin editar ni recortar en
  Galería, archivo entero, por el mismo camino que después van los swings) y el
  de Video FHD 60 el paso 2. FHD 60 y no 4K, con el porqué en una línea.
  Encuadre sin metros: «lo más cerca que permita tener los pies y el palo en el
  top adentro», con el dato de que los tres clips salieron al 28 %. Sección
  nueva de transferencia: cable primero, **WhatsApp como documento sí**,
  **como video nunca**.
- **`docs/checklist-captura.md`** sincronizado con `CAPTURA.md` en los tres
  puntos donde había quedado contradiciéndolo (encuadre, WhatsApp, el `~3,5 m`
  fijo) y con una cabecera que aclara que es la hoja del protocolo **iPhone** y
  que la del S22 es `docs/filmacion-s22.md`.
- **El test que caducaba por fecha, arreglado.**
  `tests/test_service.py::test_datos_lista_un_ejemplo_de_otro_proceso` escribe
  la fecha del ejemplo como `now + 1 min` en vez de
  `"2026-09-14T12:00:00+00:00"`.
- **Un segundo test del mismo archivo, con la misma clase de bug, arreglado
  mientras corría la sesión.** `test_datos_analysis_trae_las_metricas_con_su_razon`
  quemaba `assert len(metricas) == 12`; cuando la sesión del 13 le dio vistas a
  las dos métricas de rodilla en `sports/golf/mdc.yaml`, el registro pasó a 14 y
  el test de `service/` se puso rojo sin que `service/` cambiara. Ahora compara
  `set(metricas) == set(REGISTRY.ids())`, que es lo que el test quería afirmar
  —están todas, con valor o con razón— y no depende de cuántas haya.

### Medido

- **`tests/test_service.py`: 55 en verde** (25,7 s). Al empezar: 54 verdes y 1
  rojo (el de la fecha), reproducido primero en rojo. **Motor entero: 272 en
  verde** (53,2 s; eran 264 una hora antes — las sesiones en paralelo agregaron
  tests mientras tanto). **Arnés: 13 en verde.** Los dos últimos números
  incluyen trabajo sin commitear de las sesiones 13, 14 y 15; el único archivo
  de código que toqué es `tests/test_service.py`, y nadie más lo tocó.
- **Los tamaños del presupuesto, medidos acá con `ffprobe`**: `vid1.mp4` (UHD 60
  HEVC) 43,9 Mb/s de contenedor → 165 MB por 30 s; `20260907_170638.mp4`
  (FHD 30 H.264) 18,2 Mb/s → 68 MB.
- **El 3,4× de disco del informe del 11 no se reproduce: son 2,4×**
  (97.860.899 B / 17,852 s contra 20.455.993 B / 9,002 s = 2,41×; por tasa de
  video sola, 43,10 contra 17,42 Mb/s = 2,47×). `CAPTURA.md` lleva 2,4× con la
  aclaración de que no es una comparación a igualdad de todo —HEVC a 60 contra
  H.264 a 30— y una línea diciendo que el 11 había reportado 3,4×. **El resto
  de los números del 11 y del 07 se reprodujo sin cambio.**

### Qué falta o no se probó

- **La decisión del fps sigue abierta y no era de este encargo.** Los documentos
  dicen el hecho (ningún modo Video del S22 llega a 100; Slow motion FHD 240 es
  la única llave) y no deciden nada: no se tocó `sports/golf/` ni ningún umbral.
- **Tres lugares fuera de los cuatro archivos asignados siguen citando el
  80–90 % o los 3,5 m sin la nota medida**, y no se tocaron por la regla de
  sesiones en paralelo: `DECISIONES.md:42` (ADR-002, lo toca el 15),
  `ARRANQUE.md:80`, y `truth/kinelab_truth/harness.py:32` (lo toca el 13).
- **El checklist sigue siendo el del iPhone** —1080p120 + AirDrop, que en esta
  Mac no existe—; sólo se le sincronizaron las tres contradicciones y se le puso
  la cabecera que manda a la guía del S22. Reescribirlo depende de en qué modo
  se termine filmando, que depende del cronómetro de 240.
- El camino de menú de WhatsApp («Adjuntar → Documento») no se verificó en un
  teléfono: lo dijo Hernán y lo confirmó la medición del archivo.
- El front no se abrió ni se tocó `web/` ni `service/` (regla de trabajo).

### Desviaciones

- Ninguna del contrato: no se tocó `CONTRATO.md` ni ningún schema.
- Del prompt, una de alcance, hacia arriba: se arreglaron tres contradicciones
  que el prompt no pedía pero que la relectura de punta a punta dejó a la vista,
  todas dentro de los cuatro archivos asignados — el `~3,5 m` fijo de
  `down_the_line` (que choca con la regla nueva de acercar el trípode), el
  encabezado de §Transferencia que decía «un solo camino: AirDrop del iPhone»
  justo arriba de la tabla del S22, y el «Nunca: … WhatsApp» del checklist sin
  distinguir los dos modos.
- Del informe del 11, una corrección numérica: **3,4× → 2,4× de disco**, con la
  cuenta escrita en el informe de esta sesión. Los informes ajenos no se tocan.

---

## 15 de septiembre de 2026 — encargo 11: los tres clips nuevos son swings, no cronómetro

Prompt: `docs/prompts/11-diagnostico-vid123.md`. Informe:
`docs/informes/2026-09-15-11-diagnostico-vid123.md`. Encargo de diagnóstico y
medición: **no se tocó código**. El único archivo del repo que cambió es
`data/capture-paths.yaml`.

### Qué existe ahora

- **Un camino declarado nuevo** en `data/capture-paths.yaml`:
  `s22ultra-video-uhd60-whatsapp-doc` — Galaxy S22 Ultra, `mode: video`,
  `transfer: whatsapp-documento`, `calibrated: false`, `nominal_fps` 60,
  `codec_expected` hevc (medido), los seis campos del cronómetro en `null`.
  El transporte lo confirmó Hernán: **WhatsApp en modo documento**, no por
  cable. Es un transporte distinto, así que es un camino distinto.
- **Los tres clips en `data/incoming/`** (ignorado por git), con sha256 idéntico
  a los originales de `~/Downloads`, que no se tocaron:
  `vid1` `f4d19a56db13…`, `vid2` `331d4c860689…`, `vid3` `22ffea6acb40…`.
- **Exploraciones** en `data/incoming/vid1.kinelab/`, `vid2.kinelab/` y
  `vid3.kinelab/` (ignorado; se rehacen con un comando de ~18–76 s).

### Medido

**Los tres son el mismo teléfono, modo y tanda**: Video UHD 3840×2160 a 60 fps,
HEVC `hvc1` Main a 43–47 Mb/s, rot −90, `com.android.capture.fps` 60,
grabados el 14/9 entre 16:50:41 y 16:52:59. Reproducción efectiva **60,025–60,026
fps** en los tres; ratio VFR efectivo 1,0007 (bruto 4,36–6,58).

**No hubo recompresión.** El `udta` de Samsung sigue adentro (1,02–1,10 MB,
contra 557.940 B del original FHD del 7/9) y el orden de hijos del `moov` es
idéntico al de ese original. WhatsApp **en modo documento** no toca el archivo.

**El delta de arranque de este modo es 0,073–0,110 s** (4,4–6,6 cuadros a
60 fps), contra 0,2015 s en FHD 30. En los tres el primer delta es el **único**
fuera de lugar: el criterio "el primero y sólo el primero" aguanta también acá.

**Ninguno es el cronómetro** — Hernán confirmó que no se filmó. **No se escribió
ningún camino calibrado** y sigue sin haber un `fps_real` medido de este
teléfono en ningún modo.

**Gate**, con ese camino: los tres `reject`, **una sola razón**,
`fps_min_for_gesture` (60,03 contra 100). Siete chequeos pasan,
`fps_matches_path` queda en `null` (el camino declarado no tiene reproducción
contra la que comparar), y `capture_path_known` pasa **diciendo** que es
declarado. Declarar no ablandó ningún umbral. vid3 pasa `duration_plausible`
por 0,149 s (3,149 s contra el mínimo de 3 s).

| | vid1 | vid2 | vid3 | FHD 7/9 |
|---|---|---|---|---|
| cuadros · fps | 1066 · 60,026 | 292 · 60,026 | 189 · 60,025 | 265 · 29,998 |
| calidad | `confiable` | `confiable` | **`no_usar`** | `confiable` |
| multi-sujeto | 0,0000 | 0,0000 | 0,0000 | 0,3132 |
| cuerpo / alto | 28,7 % | 28,2 % | 29,5 % | 41,9 % |
| plausibilidad rechazada | 1,0 % | 1,7 % | **23,8 %** | 0,8 % |
| address·top·impacto·follow_end | 672·726·**741**·842 | 58·115·134·— | — | 111·141·147·219 |
| backswing / downswing | 899,6 / 249,9 ms | 949,6 / 316,5 ms | — | 1000,1 / 200,0 ms |
| repeticiones | 1 | 1 | **0** | 1 |

- **vid1 es el único con contacto real, y el sub-cuadro del impacto está
  verificado contra la pelota**: el motor da impacto 741 y cruce 741→742 a
  `fraction` 0,2144 (±0,0991 cuadros); mirando los cuadros a resolución nativa,
  la pelota está quieta en el 741 y ya salió en el 742. **Primera vez que el
  detector se compara contra un contacto real a 60 fps, y acierta.**
- **vid2 es un swing de práctica**: la pelota no se mueve en ningún cuadro. Su
  "impacto" (134) es el punto bajo del palo, no un contacto.
- **vid3 arranca con el palo ya arriba**: no hay address ni backswing en el
  archivo, 0 repeticiones, calidad `no_usar`.
- **Los 60 fps compran exactamente una métrica** respecto de los 30 del clip del
  7/9: `tempo_ratio` (3,6 en vid1, 3,0 en vid2). Las tres duraciones siguen en
  `null` porque piden `fps_min` 120. Ninguna métrica con `judgment_allowed`
  verdadero: procedencia `sin_verificar`.

**Lo que cuesta 4K**, con cinco corridas de `datos` (`load average` 3,4–6,5):
FHD **5,46 s fijos + 30,8 ms/cuadro**; UHD **5,82 s + 66,2 ms/cuadro** →
**2,15× por cuadro**, y **4,29×** por segundo de movimiento real (UHD60 contra
FHD30). vid1: 17,76 s de video en 76,38 s.

**Y los píxeles de más se tiran.** El recorte entra a `rtmpose-m` a 192×256. El
bbox mide 1340 px de alto en el FHD del 7/9 (**5,24×** de reducción) y
1466–1550 px en los UHD (5,7–6,0×). **En FHD ya entraba 5,2× sobredimensionado:
UHD no agrega precisión, sólo peso.**

### Qué falta o no se probó

- **Un test rojo que no es de esta sesión y que se rompió solo al pasar la
  medianoche**: `tests/test_service.py::test_datos_lista_un_ejemplo_de_otro_proceso`
  quema `"creado": "2026-09-14T12:00:00+00:00"` y afirma que ese ejemplo es más
  nuevo que una subida recién creada. Hoy es 15/9 y el orden se da vuelta. Es
  del encargo 09 (`service/`) y **no se tocó**; falla igual con el YAML de HEAD,
  o sea que no lo causó el cambio de esta sesión (verificado). El resto del
  motor: **260 en verde** con ese test deseleccionado; `tests/test_capture_paths.py`
  solo: 47 en verde; arnés: 13 en verde.
- **Ningún camino calibrado todavía.** La pregunta 3 del informe del 03 (cuánto
  mide el primer delta en cada modo) queda contestada para UHD 60 y FHD 30;
  falta Slow motion FHD 240.
- **`hip_line_rate_deg_s` llega a 3662–3979 °/s** en los tres clips: la misma
  geometría que ya anotó el encargo 07 (la línea de caderas se acorta en
  proyección al girar). Alimenta `summary.gain`, que en vid1 da ganancias
  menores a 1 (`pelvis_to_torso` 0,608, `torso_to_arm` 0,461) y
  `sequence_order` `arm>pelvis>torso`. No es una medición todavía.
- **vid3 tiene 23,8 % de cuadros rechazados por `ELBOW_RANGE`** (45 de 189)
  contra 1,0–1,7 % en los otros dos. Es casi todo finish con los brazos detrás
  de la cabeza. Sólo se contó; no se investigó.
- **La decisión grande queda para el orquestador:** ningún modo *Video* del S22
  Ultra llega a 100 fps, así que el gate va a rechazar todo lo que se filme en
  Video, calibrado o no. El único camino a ≥100 es Slow motion FHD 240, que
  llega horneado y que ADR-016 rechaza sin cronómetro. Las cuatro preguntas
  están al pie del informe.
- El front no se abrió ni se tocó `web/` ni `service/` (regla de trabajo).

### Desviaciones

- Ninguna del contrato. `capture-paths.yaml` sigue en `schema_version` 1.1.0 y
  el camino nuevo usa sólo campos que ya existían.
- Del prompt, una: el id quedó `s22ultra-video-uhd60-whatsapp-doc` y no
  `…-cable`, porque el transporte que dijo Hernán fue WhatsApp en modo
  documento. El prompt lo preveía ("o el transporte que Hernán diga").
- Del prompt, otra: los puntos 4 (leer el cronómetro, escribir el camino
  calibrado) y la parte del 6 sobre varios swings por clip **no se ejecutaron
  porque el material no los tiene**: ninguno de los tres clips es un cronómetro
  y ninguno tiene más de un swing. Está dicho con su evidencia en el informe.

---

## 14 de septiembre de 2026 — encargo 07: un swing de mocap real (CMU) y el primer número de nivel 1

Prompt: `docs/prompts/07-ejemplo-mocap.md`. Informe:
`docs/informes/2026-09-14-07-ejemplo-mocap.md`. Commit `313acd5`. Corrió en
paralelo con el 09 (`service/`, `web/`, `tests/conftest.py`,
`tests/test_service.py`) y el 10 (`kinelab/metrics/`, `tests/test_fase2.py`),
que ya commitearon.

### Qué existe ahora

- **Datos de mocap real en el repo**: `data/examples/cmu-mocap/` con `64.asf`,
  `64_01.amc`, `64_02.amc` (1,5 MB) y `ATRIBUCION.md` — el texto que CMU pide,
  la licencia como la declara el sitio, el sha256 de cada archivo, por qué el
  sujeto 64 (es el único de golf: tomas 1–10 «Swing», 11–15 «Putt», 16–30 poner
  el tee y la bola) y por qué esos dos trials. Las tres preguntas de ADR-010
  contestadas por separado.
- **`truth/kinelab_truth/mocap.py`**: parser propio ASF/AMC en numpy (**sin
  dependencia nueva**), cinemática directa, mapeo a los 26 puntos Halpe26 con
  sus diez aproximaciones escritas en `APPROX_NOTES` (que viaja dentro del
  `pose.npz`), traslado al marco del arnés y proyección con su cámara virtual a
  1080×1920 con el sujeto al 80 % exacto del alto. Escribe un `pose.npz` con
  `source: cmu-mocap`, trial, sha256 de los dos archivos, fps 120, cámara
  `sin_verificar`, `scores` en 1,0 y `model`/`detector` en `null`.

  ```bash
  cd truth && .venv/bin/python -m kinelab_truth.mocap 64_01 --vista face_on \
      --out ../data/exploracion/ejemplo-cmu-64_01-face_on --nivel1 --etiqueta "…"
  ```

- **`explore()` puede arrancar de un `pose.npz` ya calculado**
  (`prepare_take_from_pose`): sin video, sin estimador, con el `capture.json`
  armado desde la `provenance` del `.npz`. Cuando la toma no tiene
  `original.<ext>`, el overlay se dibuja sobre **fondo liso** (`_frames`,
  `FONDO_LISO`). La línea que se quema en cada cuadro y el aviso de dónde sale
  el eje del tiempo los pone quien llama (`banner`, `nota_fuente`).
- **El aviso del camino declarado se reemplaza, no se agrega.** Con una pose que
  no vino de un video, la frase de ADR-016 («el archivo reproduce a la velocidad
  de captura», «filmá el cronómetro») es falsa. `nota_fuente` la reemplaza y
  sigue yendo primero en `warnings[]`, y es también el `fps_aviso` de
  `datos-eventos.json`. **La procedencia sigue siendo `sin_verificar`**: el enum
  tiene dos valores y sólo el cronómetro da `medido_aqui`. Ningún
  `judgment_allowed` verdadero en el ejemplo.
- **Camino de captura: el default `desconocido-video`**, no se inventó ninguno
  para el mocap.
- **El ejemplo**, en las dos vistas, en `data/exploracion/ejemplo-cmu-64_01-face_on/`
  y `…-down_the_line/`, con `trabajo.json` en `estado: listo`, `origen: ejemplo`
  y su etiqueta. **No se commitea** (`data/exploracion/` está ignorado y el
  prompt prohibía el `overlay.mp4`): se rehace con el comando de arriba en ~7 s.
  El ejemplo de mentira del 08 (`ejemplo-a-mano-cortado-face_on`) está borrado.
- **`--nivel1`**: compara lo que el motor mide desde la proyección 2-D contra la
  verdad 3-D del mocap en los mismos instantes, y deja `nivel1-mocap.json` en la
  toma. Los eventos 3-D salen de `events_3d()`, con su criterio geométrico
  escrito.
- `_ascii` de `kinelab/tools/interpolar.py` pasa a `ascii_para_quemar`, pública:
  dos módulos queman texto en un cuadro y la tabla de transliteración tiene que
  ser una sola.

### Medido

**El ejemplo** (448 cuadros a 120 fps, cuerpo 1536 px = 80,0 % del alto,
estatura declarada 1,6405 m sacada de los largos de hueso del ASF):

| | `face_on` | `down_the_line` |
|---|---|---|
| address · top · impacto | **141 · 270 · 329** | **146 · 327 · 332** |
| backswing / downswing | 1075,0 / 491,7 ms (tempo 2,19 : 1) | 1508,3 / 41,7 ms |
| sub-cuadro del impacto | 329→330, 0,1419, ±0,089 cuadros | `null` por vista |
| focal de la cámara virtual | 3077,7 px | 3193,5 px |
| calidad | `confiable`, detección 1,0 | `confiable` |

**Nivel 1, trial 64_01, `face_on`.** Eventos leídos sobre las curvas 3-D:
145 / 269 / 330. Sesgo partido en dos — con los cuadros del motor sale el error
de la medición sola; con los 3-D, el total:

| métrica | motor 2-D | verdad 3-D | sesgo (medición) | sesgo total | MDC |
|---|---|---|---|---|---|
| `pelvis_sway_top_cm` | −19,4 | −17,69 | **−1,71** | −1,89 | 2,87 |
| `pelvis_sway_impact_cm` | 6,9 | 6,29 | +0,61 | −0,03 | 2,48 |
| `thorax_sway_top_cm` | −10,9 | −9,37 | −1,53 | −1,34 | 3,46 |
| `head_sway_top_cm` | −10,7 | −8,45 | −2,25 | −2,01 | 3,82 |
| `backswing_duration_ms` | 1075,0 | 1075,0 | 0,0 | **+41,7** | 12,6 |
| `downswing_duration_ms` | 491,7 | 491,7 | 0,0 | **−16,6** | 13,0 |

**Todos los desplazamientos caen bajo su MDC; ninguna duración lo hace cuando
entra el error de eventos** (+41,7 ms son 3,3 × el MDC del backswing). Todo el
error de las duraciones es error de EVENTOS, no de medición. Se repite en 64_02
(sway top −19,5 contra −17,61, sesgo −1,89). **Es un solo sujeto: primera
lectura, no tabla. De acá no sale ningún MDC ni ninguna referencia.**

El sway está sobre-leído **+10,0 %**, y se descompone: **+12,7 % de la
convención de `px_to_cm`** (divide por la altura cabeza→tobillos en px —1,4554 m
en un golfista inclinado— y multiplica por la estatura declarada, 1,6405 m) y
−2,4 % de la proyección.

Lo que el mocap dice de este golfista: la pelvis se corre **17,7 cm** al lado
trasero entre address y top y vuelve +6,3 cm al impacto, con 46,8° de giro de
caderas y sin dar un paso. El pico de velocidad de las manos (3,79 m/s) cae **en
el acompañamiento, cuadro 359, no en el impacto** — el cementerio 7 de
`HERENCIA.md`, ahora sobre un humano real.

Suites: **261 en verde** en el motor (~40 s), **13** en el arnés. Nuevos: 9 en
`truth/tests/test_mocap.py`, 1 en `tests/test_perception.py`.

### Qué falta o no se probó

- **Desde `down_the_line` el detector de top falla, y está medido por qué.** El
  motor pone el top en 327 y el impacto en 332: 5 cuadros de downswing. ADR-008
  toma el **último** cambio de signo de la velocidad de las manos proyectada
  sobre el eje principal address→impact. En `face_on` ese eje está a 63° de la
  vertical y hay dos cambios (145 y **270**): el último es el top. En
  `down_the_line` el eje queda casi vertical —el movimiento hacia el objetivo
  cae sobre el eje óptico— y hay tres (158, **263** que es el top de verdad, y
  **328**, el fondo del arco antes del impacto): gana el 328. **El top está en
  la señal; lo pierde la regla del "último".** No se tocó: mover eso es reabrir
  ADR-008, no ajustar un umbral. Address e impacto desde esa vista salen bien.
- **La convención de `px_to_cm` mete +12,7 % en toda métrica en cm de un gesto
  agachado.** El arnés no puede verlo: su verdad y su medición comparten la
  convención. Decisión del orquestador; toca `kinelab/metrics/core.py`.
- `hip_line_rate_deg_s` llega a **3244 °/s** en el ejemplo (la de hombros, 453,
  es plausible): la línea de caderas mide 15,2 cm y al girar 90° su proyección
  se acorta hasta casi cero. Es columna descriptiva, no métrica registrada, pero
  es la misma geometría que alimenta `summary.gain`.
- **`follow_end` queda en `null`** en los dos trials: cortan antes del finish
  quieto. No es un error, es el material.
- **El rótulo quemado cae sobre la cabeza.** Con el cuerpo al 80 % del alto los
  keypoints van de y=14 a y=1917 en 1920: no hay margen. Es consecuencia del
  encuadre de `CAPTURA.md`.
- **La cámara virtual es un teleobjetivo**: 3078 px de focal para el 80 % del
  alto a 3 m, ~2,1 × la principal de un teléfono. Con un celular real habría que
  estar a ~0,8 m, o filmar horizontal. **El 80 % del alto en vertical no es
  alcanzable con un celular a una distancia usable.**
- El swing de este sujeto es lento (downswing ~500 ms, pico de manos 3,8 m/s):
  un golfista real de laboratorio, no un profesional.
- **El front no se abrió** (regla de trabajo) ni se tocó `web/` ni `service/`.
  Lo verificado acá es que `service/exploracion.py` lista los dos ejemplos con
  su `origen`, su etiqueta y sus ocho archivos servibles, llamándolo desde
  Python.

### Desviaciones

- Ninguna del contrato: `pose.npz` y `capture.json` conservan su forma; los
  campos nuevos del `provenance` son libres por contrato.
- Del prompt, una que el código obligó: el aviso del eje del tiempo **reemplaza**
  al de camino declarado en vez de sumarse, porque con mocap esa frase es falsa
  de punta a punta. La procedencia queda igual en `sin_verificar`.
- Del prompt, otra de alcance: se guardaron **dos** trials (64_01 y 64_02) de los
  tres que se miraron; 64_03 se descargó, se midió y no se commiteó.
- El ejemplo **no se commitea**: `data/exploracion/` está en `.gitignore` y el
  prompt prohibía el `overlay.mp4`. Se rehace con un comando.

---

## 14 de septiembre de 2026 — encargo 09: ficha del archivo, selector de camino y los avisos primero

Prompt: `docs/prompts/09-ficha-y-selector.md`. Informe:
`docs/informes/2026-09-14-09-ficha-y-selector.md`. Commits `b0b46c9` (código,
tests y front) y el de cierre con `ESTADO.md` y el informe. Corrió en paralelo
con el 07 (`kinelab/explore.py`, `kinelab/tools/interpolar.py`,
`tests/test_perception.py`, `truth/`, `data/examples/cmu-mocap/`, sin commitear
al cerrar) y con el 10, que commiteó mientras esta sesión corría.

### Qué existe ahora

- **`PUT /api/datos?camino=ID`.** El id sale de `capture-paths.yaml`; el default
  es `desconocido-video`. Va a `explore(camino=…)` y queda en `trabajo.json`.
  Se valida **antes** de recibir el archivo: un id inexistente da 400 con la
  lista de los que hay, y un `slomo` sin calibrar da 400 con la misma frase que
  da el gate (`slomo_declared_reason`) — no se arranca un trabajo cuyo eje de
  tiempo no se conoce (ADR-016).
- **La cola resuelve los caminos del mismo `data/` que los trabajos.** Antes
  `explore()` caía en `default_capture_paths_file()`, que en los tests leía el
  YAML **del repo** y no el del `tmp_path`. De ahí el octavo camino del fixture
  (`tests/conftest.py`) y el `7 → 8` de `test_load_fixture`.
- **El bloque `archivo` en `GET /api/datos/{id}`**, del `capture.json` que
  `prepare_take` escribe **antes** de correr el modelo: codec, tamaño, rotación,
  cuadros, duración real y de reproducción, fps efectivo y bruto, tasa variable
  sí/no con su ratio y el umbral, primer delta, `fps_note`, camino, si está
  calibrado y la procedencia. `service/exploracion.py:ficha_de_captura`. No se
  copia al `trabajo.json`: vive en `capture.json` y se relee.
- **`GET /api/datos` (la lista) lleva `camino` y `fps_provenance`** en cada
  fila, siempre, incluso mientras el trabajo corre: un fps sin procedencia al
  lado no se puede leer. Los trabajos del 12/9 (anteriores a ADR-016) muestran
  `camino: exploracion` y `sin_verificar`, que es lo que dice su `capture.json`.
- **En la pantalla**, de arriba hacia abajo: el selector «¿con qué se filmó?»
  al lado de la altura (recordado en `localStorage`, confirmado contra la lista
  del backend, con los `slomo` sin calibrar listados y deshabilitados); los
  **avisos** (`Avisos.tsx`: aviso de exploración, `fps_aviso` del camino
  declarado y `fps_note` si el fps corregido difiere del bruto); la **ficha del
  archivo** (`FichaArchivo.tsx`), que aparece con la pose todavía corriendo; y,
  abajo del reproductor y las fotos, **«Con este archivo»** (`Metricas.tsx`):
  las 12 métricas de `analysis.json`, cada una con valor + unidad + banda de
  ±1 cuadro, o con su `null_reason` textual.
- El orden de la página es la regla de ADR-016 hecha layout: el aviso antes de
  cualquier número derivado.

### Medido

Backend de esta sesión en el 8765, con `curl` directo (no hay `next dev`
corriendo; ver Desviaciones).

**`~/Desktop/20260907_170638.mp4` con `s22ultra-video-fhd30-cable`** (265
cuadros, 17,3 s de proceso): la ficha aparece a los ~4,8 s del final, junto con
`detectando_pose` y con `resumen` todavía en `null`. Ficha: h264 · 1080×2320 ·
rot 90° · 265 cuadros · 8,834 s (reproducción 8,969 s) · **29,998 fps efectivo,
29,436 bruto** · tasa variable **no** (ratio 1,000; bruto 6,044) · **primer
delta 0,201478 s** · `fps_note` con la frase del arranque de la cámara ·
`sin_verificar`. Eventos 111 / 141 / 147 / 219, los de siempre.

**`~/Desktop/cortado.mp4` con "No sé"** (`desconocido-video`, 4,2 s): ficha a
los ~3 s del final; 76 cuadros, 2,533 s, 29,999 fps, primer delta 0,0333 s,
`fps_note` en `null` (no hay nada que corregir). Eventos 7 / 39 / 44.

**Las 12 métricas, con el `fps_min` tolerante del encargo 10 ya commiteado**
(`e2204ee`): **7 con número y 5 con razón** en los dos clips. Con número, las
de cm: en `cortado.mp4`, pelvis sway top 0,8 cm · sway impacto 7,6 · lift top
−4,2 · tórax sway 1,7 · lift −5,3 · cabeza sway 4,7 · lift −5,1. Sin número:
las cuatro de tiempo (`fps_min` 120 y 60 contra 29,999) y `pelvis_thrust_top_cm`
por vista. **Ningún `judgment_allowed` verdadero.** Antes del 10 las 12 estaban
en `null`.

400 verificados contra el `capture-paths.yaml` real: camino inexistente →
`"camino de captura desconocido: 'iphone-que-no-tengo'. Los que hay: …"`, sin
dejar carpeta. `GET /api/datos`: 10 filas, 4182 bytes, 11 ms.

Suites: **261 en verde** en el motor (`tests/test_service.py` pasa de 47 a 55),
39 s, con el trabajo sin commitear del 07 adentro — que sigue creciendo: al
empezar este informe eran 260. Arnés: **4**.
`cd web && pnpm lint && pnpm build`, limpios.

### Qué falta o no se probó

- **La pantalla no se abrió** (regla de trabajo). Lo que más puede fallar sin
  verlo: el ancho del selector con etiquetas largas, y que la ficha y los
  avisos no empujen demasiado al reproductor hacia abajo.
- **No se probó por el proxy de `next dev`**, que es lo que pedía el prompt: no
  había ninguno corriendo y levantarlo es justo lo que la regla de trabajo
  prohíbe. Todo se midió contra el backend en el 8765. Lo que el proxy agrega
  y acá no se ejercitó es el límite de cuerpo de 2 GB (`web/next.config.ts`).
- **El 400 del `slomo` declarado sólo está probado en tests**: los tres caminos
  del `capture-paths.yaml` del repo son `video`. En la pantalla, hasta que haya
  un `slomo` declarado, esa opción no aparece.
- El bloque de métricas muestra la **primera** repetición; con más de una lo
  dice en una línea y no muestra las otras. En exploración hoy siempre hay una.
- `confidence` sigue en `null` en todo el registro de golf (lo llena la Fase 3);
  la pantalla lo aguanta y no inventa nada, pero la columna no existe.
- Sin paginado en la lista, igual que antes. Cada corrida deja ~20 MB.

### Desviaciones

- Ninguna del contrato: no se tocó `analysis.json`, `capture.json`, `pose.npz`
  ni `capture-paths.yaml`. El bloque `archivo` es de `service/`, es una
  proyección de sólo lectura del `capture.json` y no agrega ningún número nuevo.
- **No se tocó `kinelab/` en absoluto**, ni siquiera la etapa de la ficha que el
  prompt autorizaba: `prepare_take` ya escribía el `capture.json` antes de la
  pose, así que alcanzó con que el servicio lo releyera. Evita además chocar con
  el 07, que tiene `explore.py` abierto.
- Del prompt, una cosa que no se hizo como estaba escrita: probar «por el proxy
  con `curl`». Ver arriba.
- **El octavo camino del fixture y el test en rojo que el informe del 10 le
  atribuye al 07 son de este encargo**, no del 07. Quedaron arreglados en
  `b0b46c9` (`tests/conftest.py` + `test_load_fixture` 7 → 8).
- Se mató el backend del 8765 (PID 52416, arrancado 12:07, con código anterior
  a este encargo) y quedó corriendo el de esta sesión. Nada más se tocó.

---

## 14 de septiembre de 2026 — encargo 10: `fps_min` con tolerancia del 0,5 %

Prompt: `docs/prompts/10-fps-min-tolerancia.md`. Informe:
`docs/informes/2026-09-14-10-fps-min-tolerancia.md`. Commit `e2204ee`. Cierra la
pregunta 1 del informe del 06. Corrió en paralelo con el 07 (`truth/`,
`data/examples/`, `kinelab/explore.py`) y el 09 (`service/`, `web/`), que
todavía no commitearon.

### Qué existe ahora

- **`FPS_MIN_TOL = 0.005` en `kinelab/metrics/registry.py`**, y una función
  `fps_min_met(metric, fps_real)` = `fps_real >= fps_min · (1 − FPS_MIN_TOL)`.
  Es el **único** lugar donde se compara la tasa de la toma contra el mínimo de
  la métrica: la llaman `judgment_allowed`, `null_metric` y
  `metrics.core.evaluate`, que antes tenían cada uno su propio `>=`.
- **El porqué está escrito** en el comentario de la constante y en `CONTRATO.md`
  §El sextuplo de toda métrica: el arnés barre en fps nominales enteros
  (240 · 120 · 60 · 30), las tasas de video reales son NTSC
  (239,76 · 119,88 · 59,94 · 29,97) y el S22 Ultra entrega además 29,998.
- **`null_reason` no cambió**: sigue diciendo los dos números sin redondear
  (`"fps_real 29.998 por debajo de fps_min 120"`).
- **El gate no se tocó.** `fps_min_for_gesture` compara contra el umbral del
  deporte (golf: 100) **sin** tolerancia, y así queda; está aclarado en
  `CONTRATO.md`. Tampoco se tocaron `CAPTURA.md`, `sports/golf/mdc.yaml` ni
  `truth/` — que además no se ve afectado: `harness.py:84` evalúa con
  `fps_min=1.0`.

### Medido

**Original del S22 con `s22ultra-video-fhd30-cable`** (265 cuadros, 29,998 fps,
`sin_verificar`): **7 de las 12 métricas pasan de `null` a tener valor** —
`pelvis_sway_top_cm` −0,8 · `pelvis_sway_impact_cm` 7,7 · `pelvis_lift_top_cm`
−2,6 · `thorax_sway_top_cm` 0,7 · `thorax_lift_top_cm` −3,0 · `head_sway_top_cm`
5,2 · `head_lift_top_cm` −5,7, todas en cm. Siguen en `null` las tres duraciones
(`fps_min` 120), el tempo (60) y `pelvis_thrust_top_cm` (por **vista**, no por
fps: su `fps_min_met` ya es `true`). **Ningún `judgment_allowed` en `true`**: el
camino es declarado. La tolerancia habilita medición, no juicio.

**`cortado.mp4` con `desconocido-video`** (76 cuadros, 29,999 fps): las mismas 7
con valor y las mismas 5 en `null`, cada una con su banda de ±1 cuadro
(`pelvis_sway_impact_cm` 7,6 [7,6 · 8,6], `head_lift_top_cm` −5,1 [−6,2 · −5,1]).

**Ninguna medición se movió.** Eventos y tiempos idénticos a los del 04 y el 06:
S22 address 3,7 s · top 4,7 · impacto 4,9 · fin 7,3, backswing 1000,1 ms,
downswing 200,0; `cortado.mp4` address 7 · top 39 · impacto 44, 1066,7 y
166,7 ms. Lo único que cambió es cuáles métricas se muestran.

Suites: **252 en verde** en el motor (26 s; eran 240 al cerrar el 06, y los 12
de diferencia son exactamente los casos nuevos de este encargo), **4** en el
arnés. Los 12 tests no son decorativos: con `FPS_MIN_TOL = 0.0` fallan 7, y con
`0.05` fallan los 3 que exigen que 29,8 contra 30 **no** pase.

### Qué falta o no se probó

- **Los 7 números son los primeros que el motor muestra sobre video real y no
  están validados contra nada.** Su MDC sale del nivel 0 del arnés (proyección +
  ruido, sin estimador) y su procedencia es `sin_verificar`. Que se vean no los
  vuelve defendibles.
- `follow_duration_ms` en `cortado.mp4` está doblemente en `null` (fps 120 y
  falta `follow_end`); gana el fps por el orden de chequeos de `evaluate`.
- La tolerancia **no acerca nada al gate**: golf sigue pidiendo 100 fps y
  29,998 no se le acerca. Esto sólo cambia qué muestra el modo exploración de un
  clip que el gate rechaza.
- El 0,5 % es una decisión, no una medición: cubre NTSC (0,1 %) con margen de 5×
  y deja afuera la tasa de abajo entera. Un teléfono que declare 30 y entregue
  29,7 no lo salva la tolerancia, y está bien: ése necesita cronómetro.
- **El front no se abrió** (regla de trabajo) ni se tocó `web/` ni `service/`.
  Hoy nadie consume `fps_min_met` fuera del motor.
- **Un test en rojo que no es de este encargo, para la sesión del 07:** su
  `tests/conftest.py` sin commitear agregó un octavo camino
  (`desconocido-video`) al fixture `capture_paths_yaml` y
  `tests/test_capture_paths.py::test_load_fixture` sigue afirmando
  `len(cp.paths) == 7` (`assert 8 == 7`). Se arregla con ese 7 → 8 en el commit
  del 07. Sobre HEAD limpio la suite da **252 en verde** (verificado con un
  `git archive HEAD` extraído aparte).

### Desviaciones

Ninguna: el prompt se implementó tal cual, y la decisión ya estaba en
`docs/PLAN.md`. No hay preguntas para el orquestador.

---

## 14 de septiembre de 2026 — encargo 06: caminos de captura declarados (ADR-016)

Prompt: `docs/prompts/06-camino-declarado.md`. Informe:
`docs/informes/2026-09-14-06-camino-declarado.md`. Corrió en paralelo con el 08
(`service/`, `web/`, `tests/test_service.py`), que ya commiteó.

### Qué existe ahora

- **`data/capture-paths.yaml` dejó de estar vacío** y va en **1.1.0**. Campo
  `calibrated` (default `true`): con `true` los seis campos del cronómetro más
  `nominal_fps` y `codec_expected` son obligatorios; con `false` los seis van en
  `null` —declarar no es medir, y el validador lo hace cumplir— y
  `nominal_fps` / `codec_expected` son opcionales. Los tres declarados que pide
  ADR-016: `desconocido-video` (el genérico, default de exploración),
  `s22ultra-video-fhd60-cable` y `s22ultra-video-fhd30-cable`.
- **El gate acepta un camino declarado y dice bajo qué supuesto.**
  `capture_path_known` pasa con su `reason` (que no entra en `gate.reasons`);
  `fps_matches_path` queda en `null` (no hay reproducción medida contra la que
  comparar); `codec_matches_path` queda en `null` si el camino no declara codec;
  `fps_min_for_gesture` y `duration_plausible` usan la tasa de captura
  **asumida** (= reproducción efectiva) y lo dicen. Un `slomo` sin calibrar →
  `reject`, con la frase del factor de estiramiento desconocido, y los chequeos
  que necesitan tasa de captura quedan sin evaluar.
- **`capture.json` en 1.2.0**: `capture_path_calibrated` y `fps_provenance`
  (`medido_aqui` | `sin_verificar`), opcionales con default conservador;
  `fps_source` = `declarado:<id>` en un camino declarado. Un 1.0.0 sigue
  validando.
- **`analysis.json` en 1.2.0**: `header.source.fps_provenance` y
  `fps_provenance` en **cada** métrica del sextuplo, los dos **obligatorios**
  (desviación anotada en `CONTRATO.md`). `judgment_allowed` exige
  `fps_provenance == "medido_aqui"`: con la tasa sin verificar el número se
  muestra y no se juzga. `warnings[0]` lleva el aviso.
- **`python -m kinelab datos VIDEO --camino ID`**, default `desconocido-video`.
  `datos-eventos.json` agrega `camino`, `camino_calibrado`, `fps_provenance` y
  `fps_aviso`; el overlay quema una cuarta línea `camino <id> | fps <n> |
  <procedencia>` (ASCII, escala propia, no encoge las tres de arriba).
- **En exploración la procedencia es siempre `sin_verificar`**, incluso con un
  camino calibrado: ahí el gate no corre y nadie verificó que el archivo vino
  por ese camino. Los números del cronómetro sí se usan si el camino los tiene.
  Está escrito en ADR-016.
- Documentado: ADR-016 en `DECISIONES.md`; invariante 2 y glosario en
  `CONTEXTO.md`; `CAPTURA.md` §Caminos declarados sin calibrar + tabla del gate;
  `CONTRATO.md` §capture-paths.yaml, §capture.json, §sextuplo, §Versionado,
  §Desviaciones.

### Medido

**Ingesta real del original del S22 con `s22ultra-video-fhd30-cable`** (en un
`data/` del scratchpad; nada de eso se commiteó): veredicto `reject` con **una**
razón, `fps_min_for_gesture` (29,9983 contra 100). **Ocho de nueve chequeos
pasan, `capture_path_known` entre ellos por primera vez.** `capture.json`:
`capture_path_calibrated` false · `fps_provenance` `sin_verificar` · `fps_real`
29,9983 · `stretch_factor` 1,0 · `fps_source` `declarado:s22ultra-video-fhd30-cable`.

**Percepción sobre ese take no corre**, por diseño anterior a este encargo:
`run_perception` se niega con una toma rechazada (`kinelab/perception/run.py:74`).
Los números del análisis salieron del mismo clip por exploración con el mismo
camino: las **12 métricas en `null`** (11 por `fps_min`, `pelvis_thrust_top_cm`
por vista) y **ningún `judgment_allowed` verdadero**; eventos y tiempos
idénticos a los del encargo 04 (address 111, top 141, impacto 147, sub-cuadro
0,4181, backswing 1000,1 ms, downswing 200,0 ms). ADR-016 no movió ninguna
medición.

Sobre `~/Desktop/cortado.mp4` con el camino por defecto:
`datos-por-cuadro.csv` **byte a byte idéntico** al de antes y
`datos-eventos.json` con **sólo** los cuatro campos nuevos de diferencia.

Suites: **240 en verde** en el motor (26 s), **4** en el arnés. Los tres
archivos de test que se tocaron pasan de 103 a 131 casos.

### Qué falta o no se probó

- **A 29,998 fps mueren también las métricas de `fps_min: 30.0`**, por dos
  milésimas, y con un camino declarado el `fps_real` es siempre el medido del
  archivo: va a pasar con todo clip de 30 fps. Decisión del orquestador
  (tolerancia en la comparación, o `29.9` en `sports/golf/mdc.yaml`, que lo
  escribe el arnés). No se tocó.
- El `fps_note` del primer delta **sigue sin subir a la pantalla** (pregunta 1
  del informe del 04). Ahora el mecanismo existe: es una línea en el mismo
  lugar donde se arma el aviso del camino declarado.
- `s22ultra-video-fhd60-cable` no declara codec: sin medir en ese modo.
- Nada de esto acerca el S22 al gate de golf: 30 y 60 fps están debajo de 100.
  Lo decide el cronómetro sobre FHD 240, y un `slomo` declarado está rechazado
  a propósito.
- **El front no se abrió** (regla de trabajo) ni se tocó `web/` ni `service/`.
  Los campos que necesita el 07 ya están en `datos-eventos.json`, y
  `GET /api/config` ya lista los caminos con su `calibrated`.

### Desviaciones

- **Una, anotada en `CONTRATO.md` §Desviaciones:** `fps_provenance` es un campo
  **obligatorio** nuevo en un bump **minor** de `analysis.json` (1.1.0 → 1.2.0).
  En rigor un campo requerido nuevo es major. Se hizo minor con tres razones:
  opcional permitiría escribir un análisis que esconda el supuesto del eje de
  tiempo (que es justo lo que ADR-016 impide), el validador sólo corre al
  **escribir** (`contract/write.py`), y no hay `analysis.json` viejo fuera de lo
  que se regenera. El ejemplo del repo se actualizó a mano.
- Del prompt, tres precisiones que el código obligó y que quedaron escritas en
  ADR-016: `nominal_fps` y `codec_expected` pasan a ser opcionales (un camino
  declarado puede no saberlos); el YAML **acepta** un `slomo` declarado a
  propósito, para que la frase la diga el gate y no un error de parseo; y en
  exploración la procedencia es siempre `sin_verificar`.
- Del prompt, una cosa que no se pudo hacer como estaba escrita: "percepción y
  análisis sobre ese take" es imposible mientras el veredicto sea `reject`
  (`run_perception` lo prohíbe, y está bien). Se hizo por exploración, con el
  mismo clip y el mismo camino.
- Choque de sesiones paralelas: el cambio de 4 líneas en
  `tests/test_service.py` (la lista de caminos del fixture creció) quedó
  commiteado por la sesión del 08 en `cee7585`.

---

## 14 de septiembre de 2026 — encargo 08: lista de trabajos y ejemplos en la pantalla

Prompt: `docs/prompts/08-lista-de-trabajos.md`. Informe:
`docs/informes/2026-09-14-08-lista-de-trabajos.md`. Commits `cee7585` (backend)
y `d5aebbc` (front). Corrió en paralelo con el 06, que tiene tocado
`kinelab/` y `tests/conftest.py` sin commitear.

### Qué existe ahora

- **`GET /api/datos`**: una fila por trabajo, del más nuevo al más viejo, con
  `id`, `video`, `creado`, `terminado`, `estado`, `origen`, `etiqueta`,
  `altura_m`, `vista`, `segundos`, `error` y —sólo si está listo— `fps_archivo`,
  `cuadros` y `eventos_frame`. Sin el resumen entero (son ~20 KB por trabajo).
- **El disco manda.** `listar()` y `get()` releen los `trabajo.json` de
  `data/exploracion/` en cada llamada. La única excepción es el trabajo que
  está corriendo en este proceso: ahí manda la memoria, que lleva el progreso
  por cuadro (a disco sólo va al cambiar de etapa). Por eso aparecen los
  trabajos de sesiones anteriores y las carpetas que deje otro proceso, sin
  reiniciar el servidor.
- **El id de un trabajo es el nombre de su carpeta**, no el campo `id` del
  JSON: es lo que resuelve la URL. `JOB_ID` acepta ahora también un slug
  (`ejemplo-cmu-64_01-face_on`), sin barras y sin empezar con punto.
- **La forma de un ejemplo, para el encargo 07** (está en el encabezado de
  `service/exploracion.py`): una carpeta más en `data/exploracion/`, con los
  mismos archivos, y un `trabajo.json` con `"estado": "listo"`,
  `"origen": "ejemplo"` y `"etiqueta"` (el rótulo que muestra la pantalla; acá
  no se inventa ninguno). `estado` es lo único obligatorio: `video` cae en el
  nombre de la carpeta y `creado` en la fecha del archivo si faltan. Sin
  `origen`, el trabajo es `subida`.
- **En la pantalla**, debajo de «Subir video», la lista «Trabajos anteriores y
  ejemplos» (`web/src/components/ListaTrabajos.tsx`): nombre, fecha, vista,
  estado, fps, cuadros y los cuadros de cada evento; los ejemplos con su
  rótulo, en la lista y arriba del resultado. Clic → se abre ese trabajo como
  si acabara de terminar, sin volver a subir el video.
- **`?trabajo=<id>`** abre ese trabajo al cargar; al elegir uno de la lista (o
  al terminar una subida) la URL se actualiza con `history.replaceState` —la
  forma que documenta Next 16— sin recargar. Un id que ya no existe se olvida
  (localStorage incluido), se avisa en una línea y la página sigue.
- Lo ilegible se saltea **y se registra**: un `trabajo.json` roto o sin
  `estado` deja una línea por lectura; una carpeta sin `trabajo.json`, una sola
  vez por carpeta (puede ser una subida a medio recibir).

### Medido

Backend nuevo en el 8765 y el `next dev` que ya corría en el 3000; todo por el
proxy con `curl`, sin abrir el navegador.

| | |
|---|---|
| trabajos listados | 8 (5 de sesiones anteriores + 2 subidas de `cortado.mp4` + 1 ejemplo); quedan **7** en disco |
| orden | por `creado`, del más nuevo al más viejo |
| `cortado.mp4` en la fila | 29,999 fps · 76 cuadros · address 7 · top 39 · impacto 44 |
| `20260907_170638.mp4` (12/9) | 29,436 fps · 265 cuadros · address 111 · top 141 · impacto 147 · fin 219 |
| `GET /api/datos` | 2504 bytes · 3,0–3,3 ms en el backend · 4,4–5,3 ms por el proxy |
| ejemplo armado a mano | se abre por su slug: `origen: ejemplo`, etiqueta, 8 archivos, `overlay.mp4` con 206, PNG 200 |
| trabajo borrado del disco | una de las dos subidas: desaparece de la lista, y su `GET` y el de sus archivos dan 404 |

Los dos trabajos del 12/9 sobre el original del S22 conservan su
`fps_archivo` 29,436, el **bruto**: se calcularon antes del encargo 04. Nada
recalcula un trabajo viejo, y está bien que sea así.

Suites: **239 en verde** en el motor (233 + 6 nuevos en `tests/test_service.py`,
que pasa de 41 a 47), ~25 s — con el trabajo sin commitear del 06 adentro.
`cd web && pnpm lint && pnpm build`, limpios.

### Qué falta o no se probó

- **La pantalla no se abrió en un navegador** (regla de trabajo). Lo que más
  puede fallar sin haberlo visto: el alto de la lista (`max-h-72` con scroll)
  cuando hay muchos trabajos, y que `?trabajo=` conviva bien con el router de
  Next al recargar.
- **El ejemplo que hay es armado a mano y no es mocap**: una copia de
  `cortado.mp4` con su `trabajo.json` escrito aparte, para probar la lista. Su
  etiqueta lo dice con todas las letras. Se borra con
  `rm -rf data/exploracion/ejemplo-a-mano-cortado-face_on`; el del encargo 07
  lo reemplaza.
- Sin paginado: la lista devuelve todos los trabajos. Con 8 son 2,5 KB y 3 ms;
  con cientos habría que cortar.
- No se borra nada desde la pantalla, por encargo. `rm -rf
  data/exploracion/<id>` y listo: la lista se entera sola.
- Un trabajo a medio correr de **otro** proceso se lista con su estado tal
  cual; sólo el arranque del propio servidor marca como `error` lo que quedó a
  medias. No se escribe sobre el `trabajo.json` de otro.

### Desviaciones

- Ninguna del contrato: `trabajo.json` es de `service/`, no del contrato de
  datos; no se tocó `analysis.json`, `capture.json` ni `pose.npz`.
- **Se mató el backend viejo del 8765** (PID 16524, del 12/9 17:28, con código
  anterior a los encargos 02–06) para poder probar por el proxy: Next 16 no
  deja levantar un segundo `next dev` sobre el mismo directorio, así que había
  que usar el que ya corría en el 3000, y ése habla con el 8765. En su lugar
  quedó corriendo el backend de hoy. El `next dev` de Hernán (PID 16850) no se
  tocó.

---

## 14 de septiembre de 2026 — encargo 05: la lámina interpolada (para mirar)

Prompt: `docs/prompts/05-lamina-interpolada.md`. Informe:
`docs/informes/2026-09-14-05-lamina-interpolada.md`. Es el paso 3 —y último— de
los tres que quedaron definidos en la quinta sesión (más abajo).

### Qué existe ahora

- `kinelab/tools/interpolar.py`: fabrica con `minterpolate` de ffmpeg los
  cuadros que nunca se grabaron entre dos cuadros medidos, los **etiqueta como
  no medidos** y los deja en dos archivos aparte. Es un experimento etiquetado,
  no una medición.

  ```bash
  .venv/bin/python -m kinelab.tools.interpolar VIDEO --entre A B [--factor 4] \
      [--contexto 2] [--marca 44.44] [--marca-texto "…"] [--marca-mas-menos 0.11] \
      [--recorte persona|completo|x0,y0,x1,y1] [--filtro …] [--fps-reproduccion N] [--out DIR]
  ```

- Agnóstica al deporte: recibe **índices de cuadro**, no "impacto", y el texto
  de la marca lo pone quien la llama.
- En `<video>.kinelab/` deja `interpolado-A-B-x<factor>.mp4` (el tramo
  `[A−contexto, B+contexto]`, H.264 con `-g 12`, cada cuadro con su rótulo
  quemado: verde `medido | 44`, naranja `cuadro interpolado, no medido | 44,25`)
  y `lamina-A-B-x<factor>.png` (A, los intermedios y B en fila, recortados al
  bbox de la persona, con la marca vertical y su banda de ±).
- **Nada lo lee**, verificado con `grep` sobre `service/`, `web/src/`,
  `kinelab/explore.py` y `sports/`: cero apariciones. La lista blanca de
  `service/exploracion.py` sigue con sus 9 nombres.
- Dos cosas que hubo que resolver y conviene no volver a descubrir:
  - **Los índices de ffmpeg no son los del motor.** `select=between(n,…)` cuenta
    después de la edit list; la de `cortado.mp4` esconde 13 muestras. Los
    cuadros se leen con el mismo `iter_frames` de la percepción.
  - **`minterpolate` emite `(n−1)·factor` cuadros y se queda sin el último.** Se
    le entrega el último duplicado y la salida da `(n−1)·factor + 1`, el tramo
    entero. Y se le entra a **1 fps** pidiéndole `fps=factor`, para que el
    cuadro de salida `k` caiga en el índice `k/factor` sin redondeo de time base
    (verificado: PSNR 52,4 dB en los múltiplos de `factor`, que es sólo el ida y
    vuelta BGR↔YUV del filtro).
- `tests/test_interpolar.py`: 9 tests con el clip sintético de `conftest.py`.
  Suite entera: **206 en verde, 17,5 s** (incluye lo del encargo 04, que corrió
  en paralelo).

### Medido

Corridas sobre `~/Desktop/cortado.mp4`, cuadros 42–47, 1080×2320:

| | factor 4 | factor 8 |
|---|---|---|
| cuadros de salida | 21 | 41 |
| tiempo | 7,6 s | 14,5 s |
| mp4 | 954 KB · 120,00 fps · 0,175 s | 1787 KB · 239,99 fps · 0,171 s |
| lámina | 6783 KB · 3215×1693 | 12212 KB · 5775×1856 |

**El techo de `minterpolate` sobre este material**, medido dejando fuera los
cuadros impares de 38 a 50 y pidiéndole que los reconstruya desde los pares
(error RMS en una caja de 600×850 px sobre las manos y el palo): congelar el
cuadro 33,5 niveles · crossfade 27,6 · `mci`+`bidir` **22,2**. La compensación
de movimiento se lleva 34 % del error de congelar y 20 % del de un crossfade;
lo que queda es dos tercios del cambio que tenía que explicar (44 contra 45
difieren 36,3 niveles RMS sobre esa caja).

De las cuatro opciones que sugería el prompt, **`mc_mode` y `vsbmc` no hacen
nada**: con `obmc`/`vsbmc=0` la salida es byte a byte idéntica en ffmpeg 9.0.1.
La única que mueve la aguja es `me_mode`, y `bidir` (que no es el default del
filtro) gana. `search_param` 64–128 aporta 0,1 dB; `me=umh` cuesta 46 s en vez
de 3,4 s y sale peor; y **`me=esa` (búsqueda exhaustiva) tardó 53 minutos para
empatar con el default de 3,4 s**. El problema no es que la estimación de
movimiento busque poco: es que un palo delgado que barre más de lo que mide,
contra un fondo con textura, no es un bloque que se pueda seguir.

**Lo que se ve:** el shaft sale fantasma. En los intermedios no hay un palo en
posición intermedia: hay dos palos translúcidos a la vez, el de 44
desvaneciéndose y el de 45 apareciendo, y en el medio del hueco ninguno se lee.
El pantalón sale con la raya duplicada. Los extremos, 44 y 45, intactos. **Lo
decide Hernán mirando**; acá no hay veredicto.

### Qué falta o no se probó

- **Si sirve o no es de Hernán.** La sesión mide y describe; no hay criterio
  numérico de "sirve para mirar".
- El mp4 a `fps × factor` dura 0,17 s: no se mira reproduciéndolo, hay que ir
  cuadro a cuadro. `--fps-reproduccion` existe y está probado (6 fps → 6,8 s),
  pero el default es el que pedía el prompt.
- El recorte por defecto (bbox de la persona, 615×1326 px por panel) obliga a
  zoom al 100 % para juzgar el palo. Un recorte fijo alrededor de las manos se
  lee mucho mejor: `--recorte 300,1150,900,2000`, probado, no es el que quedó en
  los dos archivos entregados.
- No se corre pose sobre los cuadros interpolados, a propósito.

### Desviaciones

- Ninguna del contrato: no toca `analysis.json`, `capture.json` ni `pose.npz`.
- Del prompt, una: **`Pillow` no está en el entorno**, contra lo que el prompt
  suponía ("Pillow o OpenCV, que ya están"). Se dibuja todo con `cv2.putText`,
  que sólo tiene ASCII, y el texto se translitera **al quemarlo** (`é`→`e`,
  `·`→`|`, `±`→`+/-`); en el código y en la consola el español queda entero. No
  se agregó la dependencia (ADR-015).
- Del prompt, otra de forma: el test de "PSNR alto fuera de la franja del
  rótulo" se hace sobre los cuadros **antes** de codificar (y por separado, que
  `rotular` no toca un píxel debajo de la franja, byte a byte); sobre el mp4 ya
  codificado el número mediría el H.264, no la interpolación.

---

## 14 de septiembre de 2026 — encargo 04: el gate y `explore` con el fps efectivo

Prompt: `docs/prompts/04-gate-fps-efectivo.md`. Informe:
`docs/informes/2026-09-14-04-gate-fps-efectivo.md`. Cierra lo que el 03 dejó
abierto: quién consume los números corregidos.

### Qué existe ahora

- **`capture.json` en 1.1.0.** `fps_playback` y `vfr_ratio` son ahora los
  **efectivos** (sin el primer delta de PTS cuando el arranque de la cámara es
  la única anomalía). Los brutos viajan al lado en `fps_playback_raw` y
  `vfr_ratio_raw`, el delta de arranque en `first_delta_s`, y `fps_note` dice
  en una frase por qué difieren (`null` cuando coinciden). Los cuatro campos
  son opcionales: un `capture.json` 1.0.0 sigue validando, con `null`, y hay
  test.
- **El gate evalúa los efectivos** en `vfr_ratio_le_1_10` y `fps_matches_path`.
  Cuando el efectivo difiere del bruto, el chequeo lo dice en su propio
  `reason` **aunque pase** — *"ratio 1.000 sin el primer delta de 0.201 s
  (arranque de la cámara); bruto 6.044."* Ese `reason` no entra en
  `gate.reasons`, que sigue llevando sólo lo que falló.
- **`explore.py`**: `prepare_take` usa `fps_playback_effective` para `fps_real`,
  `fps_playback` y `duration_s`, y el ratio efectivo para `vfr_ratio`; también
  escribe los cuatro campos nuevos.
- `fps_truth.first_delta_note()` extraída (misma frase, misma lógica) para que
  la redacción viva en un solo lugar: la usan `analyze()` y el `fps_note` del
  gate.
- Documentado: `CONTRATO.md` §capture.json (con §El fps efectivo y el bruto),
  §Versionado y §Desviaciones; `CAPTURA.md` §Por qué el archivo no puede decir
  su propio fps y la tabla del gate.

### Medido

| | `cortado.mp4` | original `20260907_170638.mp4` |
|---|---|---|
| `fps_archivo` | 29,999 → **29,999** (sin cambio) | 29,436 → **29,998** |
| `impact.t_s` | 1,467 → 1,467 | 4,994 → **4,900** |
| `t_sub_s` | 1,481396 → 1,481396 | 5,008089 → **4,914264** |
| `fraction` del impacto | 0,4404 → 0,4404 | 0,4181 → 0,4181 (va en cuadros) |
| `address_to_top_ms` | 1066,7 → 1066,7 | 1019,2 → **1000,1** |
| `top_to_impact_ms` | 166,7 → 166,7 | 203,8 → **200,0** |

Sobre `cortado.mp4`, `datos-eventos.json` es **idéntico byte a byte** al de
antes del cambio (diff vacío). En el original, 30 cuadros de backswing dan
1000,1 ms y 6 de downswing 200,0 ms: los números redondos que se esperan a
30 fps, y que con el bruto no salían.

Ingesta del original del S22 contra un camino de prueba (h264, 30 fps,
**sin cronómetro**, en un `data/` aparte del scratchpad; no se commiteó):

```
vfr_ratio_le_1_10 | passed True | value 1.0004 | expected <= 1.1
   → ratio 1.000 sin el primer delta de 0.201 s (arranque de la cámara); bruto 6.044.
fps_matches_path  | passed True | value 29.998 | expected 30.0
   → reproducción 29.998 fps sin el primer delta de 0.201 s (arranque de la cámara); bruto 29.436 fps.
```

Veredicto `reject`, con una sola razón: `fps_min_for_gesture` (30 fps de
captura contra los 100 que pide golf). Es lo correcto. `capture.json`:
`fps_playback` 29,9983 · `fps_playback_raw` 29,4359 · `vfr_ratio` 1,0004 ·
`vfr_ratio_raw` 6,0444 · `first_delta_s` 0,201478 · `duration_s` 8,8333 ·
`duration_playback_s` 8,9686.

Suites: **197 tests en verde** en el motor (193 + 4), ~18 s; 4 en el arnés.

### Qué falta o no se probó

- **`duration_playback_s` sigue siendo el span de PTS medido**, con el hueco
  del arranque adentro: en el original, 8,969 s contra los 8,834 de
  `frames_decoded / fps_playback`. Es a propósito (el archivo de verdad dura
  eso) y está escrito en `CONTRATO.md`, pero significa que ese campo y
  `fps_playback` ya no son consistentes entre sí en un clip con arranque
  largo.
- **La exploración no avisa en pantalla que corrigió el fps.** El `fps_note`
  queda en `capture.json` (descargable) pero no entra en `warnings` ni en
  `datos-eventos.json`: el prompt acotaba `explore.py` a `prepare_take`. La
  ficha del archivo del encargo 07 es el lugar natural para mostrarlo.
- El criterio sigue siendo "el primero y sólo el primero". Medido en **un**
  teléfono y **un** modo. Cuando Hernán filme el cronómetro hay que anotar
  cuánto mide el primer delta en cada modo: si a 240 fps el arranque dura
  varios cuadros, el criterio queda corto (ya anotado por el 03).
- `data/capture-paths.yaml` sigue **vacío**: el camino del S22 que se usó para
  probar la ingesta es de prueba, sin cronómetro, y vivió sólo en el
  scratchpad. Queda para el encargo 06 (ADR-016, caminos declarados).
- El front no se abrió (regla de trabajo). No cambió nada suyo: `web/` sólo
  ofrece `capture.json` como descarga.

### Desviaciones

- **Una, anotada en `CONTRATO.md` §Desviaciones:** el bump de `capture.json` a
  **1.1.0** es minor aunque `fps_playback` y `vfr_ratio` cambien de qué número
  hablan (bruto → efectivo). §Versionado dice que renombrar un campo o cambiar
  una unidad es major, y esto está en el mismo espíritu. Se hizo minor por
  decisión del orquestador, con el valor viejo preservado en los `*_raw` y la
  diferencia explicada en `fps_note`.
- Del prompt, dos cosas menores: se agregó una función
  (`fps_truth.first_delta_note`) en un archivo que el prompt marcaba como
  intocable — pero sólo se extrajo texto ya existente, sin cambiar la lógica ni
  una letra de la frase, para no tener dos redacciones; y en `explore.py` se
  escriben además los cuatro campos nuevos en el mismo constructor, no sólo las
  dos líneas del fps.

---

## 14 de septiembre de 2026 — encargo 02: el impacto entre dos cuadros

Prompt: `docs/prompts/02-impacto-subcuadro.md`. Informe:
`docs/informes/2026-09-14-02-impacto-subcuadro.md`. Es el paso 2 de los tres que
quedaron definidos en la quinta sesión (abajo).

### Qué existe ahora

- **El cuadro entero del impacto no cambió** y ningún umbral de detección se
  tocó. Lo nuevo es el campo `subframe` del evento: el instante estimado ENTRE
  dos cuadros, con `frame_before`, `frame_after`, `fraction` (0–1), `t_sub_s`,
  su incertidumbre y los sumandos a la vista.
- Primitiva genérica en `kinelab/events/primitives.py`: `subframe_crossing`
  (cruce de una señal 1-D por un nivel, interpolado entre los dos cuadros) y
  `still_run_start`. El motor no sabe qué señal es: eso lo pone el deporte.
- En `sports/golf/events.py`, la definición: la señal es el centro de las dos
  muñecas **crudo** (huecos ≤ 5 rellenados, sin filtrar) proyectado sobre su
  dirección de viaje alrededor del impacto; el nivel es la misma proyección en
  el cuadro de address. El cero de esa señal es el instante de máximo
  acercamiento a la posición de address: la versión continua del criterio del
  cuadro entero, que es el de mínima distancia.
- Incertidumbre, invariante 8 aplicada acá: en vez de ±1 cuadro entero, el
  cruce recalculado extrapolando **cada segmento vecino** con su velocidad local
  (`curvature_frames`), más el ruido del clip propagado por la pendiente
  (`noise_frames`), sumados en cuadratura. El ruido sale de los residuos de la
  recta ajustada a la racha de quietud del address, en px.
- Sólo `face_on` (invariante 6): desde `down_the_line` la dirección de viaje de
  las manos en el impacto apunta al objetivo, casi sobre el eje óptico, y en la
  imagen queda escorzada. Desde ahí sale `null` con razón.
- Sin cruce claro no hay número: `fraction` es `null` y `null_reason` dice cuál
  de los cuatro casos fue (no cruza, cruza más de una vez, el cruce no es
  contiguo al cuadro del evento, o la vista no vale).
- Contrato: `subframe` es opcional en cada evento y `schema_version` pasa a
  **1.1.0** (campo nuevo y opcional = minor); un `analysis.json` 1.0.0 sigue
  validando. Documentado en `CONTRATO.md` §events[].
- `datos-eventos.json` lo lleva en `eventos_subcuadro`.
- Front, lo mínimo pedido: el texto «entre el cuadro 44 y el 45 (0,44 ± 0,11)»
  en la tabla por evento, en la foto del impacto y debajo del reproductor; y un
  botón que muestra los cuadros 44 y 45 lado a lado
  (`web/src/components/DosCuadros.tsx`), con la misma convención de seek que el
  reproductor —`(n + 0,5) / fps`— y el mismo aviso si el navegador muestra otro.

### Medido

| | `cortado.mp4` | original `20260907_170638.mp4` |
|---|---|---|
| cuadros / fps del archivo | 76 · 29,999 | 265 · 29,436 |
| impacto, cuadro entero | 44 | 147 |
| cruce | **44,4404** | **147,4181** (= 44,418 del recorte) |
| `t_sub_s` | 1,481396 s | 5,008089 s |
| incertidumbre | 0,111 cuadros · 3,7 ms | 0,136 cuadros · 4,6 ms |
| curvatura / ruido | 0,110 / 0,013 cuadros | 0,115 / 0,072 cuadros |
| pendiente · ruido de la señal | 115,4 px/cuadro · 1,2 px | 118,3 px/cuadro · 6,9 px |

Los dos clips comparten cuadros bit a bit y la pose se estimó por separado en
cada uno: **0,022 cuadros (0,74 ms) de diferencia**, dentro de la banda de los
dos. El instante cae 14,7 ms después del cuadro 44. Entre el 44 y el 45 las
manos recorren 118 px, el 13,6 % de la altura del cuerpo.

### Qué falta o no se probó

- **Esto no mide la bola.** Mide cuándo las manos pasan por su posición de
  address, que es el mismo proxy del cuadro entero. Con el shaft adelantado, el
  contacto real no cae exactamente ahí. Para medir el contacto hace falta el
  palo, que en golf sí se puede detectar (está en la Fase 3 como geometría del
  shaft, sin hacer). El front lo dice con todas las letras.
- **Sin MDC.** Es descriptivo, procedencia `estimacion`. El arnés (`truth/`)
  puede medirle sesgo y MDC con el swing paramétrico: hoy la única verdad
  contra la que se comparó es sintética.
- El cruce se calcula sobre la pose con huecos rellenados y **no distingue** un
  cuadro interpolado de uno medido. Con las muñecas perdidas justo en el
  impacto el número saldría igual, sin aviso.
- El front **no se abrió en un navegador** (regla de trabajo). Lo verificado
  acá: `pnpm lint` y `pnpm build` limpios, y que el cuadro 44 del `overlay.mp4`
  es el que lleva el rótulo `IMPACT` (MSE 24 contra 842–875 de sus vecinos).
- `explore.py` sigue usando `fps_playback` **bruto** y no el efectivo del
  encargo 03 (`kinelab/explore.py:59` y `:61`): por eso el original de 9 s
  reproduce a 29,436 fps y sus segundos quedan 1,9 % largos. **La `fraction` no
  se ve afectada** (va en cuadros); `t_sub_s` sí. No se tocó porque ese cambio
  es del otro encargo; queda como decisión de una línea para el orquestador.

### Desviaciones

- Ninguna del contrato: el campo es nuevo y opcional, y está documentado.
- Del prompt, una de nombre: el campo se llama `fraction`, no `fraccion`.
  `AGENTS.md` fija identificadores de código en inglés, y el resto del contrato
  lo está. La clave de `datos-eventos.json` sí es española (`eventos_subcuadro`),
  como sus vecinas `eventos_frame` y `eventos_t_s`.
- El prompt dejaba elegir entre poner el campo sólo en exploración o también en
  `analysis.json`: está en los dos, porque el que lo calcula es el detector de
  eventos y `datos-eventos.json` lo copia de ahí. Con su test de validador.

---

## 14 de septiembre de 2026 — encargo 03: `fps_truth` y el primer delta de PTS

Prompt: `docs/prompts/03-fps-truth-primer-delta.md`. Informe:
`docs/informes/2026-09-14-03-fps-truth-primer-delta.md`.

### Qué existe ahora

- `kinelab/tools/fps_truth.py` reporta, además de los números brutos que no
  cambiaron, `delta_first_s`, `vfr_ratio_excl_first` y
  `fps_playback_excl_first`, más tres propiedades derivadas:
  `first_delta_is_the_only_outlier`, `vfr_ratio_effective` y
  `fps_playback_effective`. Los seis viajan en el JSON de `to_dict()`, así que
  `PUT /api/fps-truth` los devuelve sin tocar `service/`.
- El corregido se usa **sólo** si el primer delta es el único fuera de lugar
  (ratio bruto > 1,10 y sin el primero ≤ 1,10). Un clip realmente VFR sigue
  dando `VFR` y su efectivo es el bruto.
- Método: span sin el primer delta, `(n−2)/(pts_último − pts_segundo)`, no la
  mediana de deltas: el span promedia el error de cuantización del time base
  sobre todos los deltas; la mediana lo hereda de uno solo.
- El veredicto, el `stretch_factor` y el contraste con `r_frame_rate` se
  calculan con el fps efectivo. Hay nota legible en los dos sentidos: cuando
  el arranque explica todo, y cuando excluirlo no alcanza.
- Fixture `first_delta30_h264` en `tests/conftest.py`: 120 cuadros a 30 fps con
  el primer delta de 0,2 s exactos, hecho con `setpts` (conserva los cuadros).
- **Medido, original del S22 (`~/Desktop/20260907_170638.mp4`, 265 cuadros):**
  primer delta 0,20148 s; ratio 6,044 → 1,000; reproducción 29,436 → 29,998 fps
  (**1,91 % de corrección**); veredicto `VFR` → `SIN_DURACION_REAL`.
  `~/Desktop/cortado.mp4` no cambia en nada (su primer delta ya era normal:
  el recorte arranca en el cuadro 103). Suite: **180 tests en verde** (173 + 7).

### Qué falta o no se probó

- **El gate no se tocó**, por encargo, y sigue leyendo `vfr_ratio` y
  `fps_playback` **brutos**. Medido: el original del S22 lo rechazaría hoy por
  `vfr_ratio_le_1_10` con 6,044 (con el efectivo pasaría), y `fps_matches_path`
  contra un camino de 30,000 fps da 1,88 % de desvío con el bruto contra 0,01 %
  con el efectivo — pasa raspando la tolerancia del 2 %.
- **`explore.py` no toma el corregido solo:** usa `c.fps_playback` en
  `prepare_take()` (`kinelab/explore.py:59` y `:61`). Es reemplazarlo por
  `c.fps_playback_effective`; **no se hizo** porque el encargo 02 está en ese
  archivo. Mientras tanto, los `t_s` y duraciones del original de 9 s siguen
  1,9 % largos; sobre `cortado.mp4` no cambia nada.
- El delta de arranque se midió en un solo teléfono y un solo modo. Cuando se
  filme el cronómetro conviene anotar cuánto mide el primer delta en cada modo:
  si a 240 fps el arranque dura varios cuadros, "el primero y sólo el primero"
  puede quedar corto.

### Desviaciones

Ninguna del contrato: `capture.json` no cambió de forma ni de significado. La
decisión de qué número usa el gate queda planteada en el informe como pregunta
para el orquestador, con los números de los dos chequeos afectados; es un
cambio a `CAPTURA.md` y entra como encargo propio.

---

## 12 de septiembre de 2026 — quinta sesión (en curso): el impacto entre dos cuadros

Pedido de Hernán: en `cortado.mp4` (30 fps) el cuadro marcado como impacto (44)
es anterior al contacto y el 45 ya pasó la bola. Tres pasos en orden, parando
entre cada uno: (1) diagnóstico de captura, (2) impacto sub-cuadro desde la
señal, (3) experimento etiquetado con `minterpolate` de ffmpeg para MIRAR.
Paso 1 hecho; 2 y 3 sin empezar.

### Paso 1 — diagnóstico (hecho)

- `~/Desktop/cortado.mp4`: H.264, 1080×2320 (rot 90), 76 cuadros CFR a
  30,00 fps (deltas 0,03333–0,03335). Sin duración real no hay tasa de
  captura; pero el original está y cierra la pregunta.
- **Original: `~/Desktop/20260907_170638.mp4`, Samsung Galaxy S22 Ultra, modo
  Video 30 fps** (`com.android.capture.fps: 30`, `handler_name: VideoHandle`,
  `com.android.version: 16`). 2320×1080 es la relación "Full" (19,3:9) de la
  cámara de Samsung, no un recorte. 265 cuadros en 8,97 s.
- **`cortado.mp4` es una copia bit a bit de los cuadros 103–178 del original**
  (PSNR infinito cuadro a cuadro; `cortado i = original i + 103`). El recorte en
  la Mac fue *passthrough*: re-envolvió con `Core Media Video`, dejó 89
  muestras con una edit list que esconde las 13 primeras, y conservó intacto
  el `udta` de Samsung (557.940 bytes). Ninguna de las "señales de
  re-compresión" que se listaron antes de ver el original lo era: H.264,
  `mp42`, 2320×1080 y ~16 Mb/s son la cámara de Samsung tal cual.
- Conclusión: entre el 44 y el 45 (original 147 y 148, donde el motor también
  puso el impacto) **nunca hubo cuadros**. No hay nada que recuperar de este
  material; sólo estimar el instante (paso 2) o interpolar para mirar (paso 3).
- **Falsa alarma de VFR en Android, medida:** el original tiene 263 deltas de
  0,0333 s y UNO de 0,2015 s, el primero (arranque de la cámara). `fps_truth`
  lo declara `VFR` (ratio 6,04) y calcula `fps_playback = 29,436` con
  `(n−1)/span`; `explore` usa ese número como fps y todos los `t_s` y
  duraciones del original quedan 1,9 % largos. Propuesta, sin hacer: que
  `fps_truth` reporte el ratio excluyendo el primer delta y lo diga en una
  nota; qué hace el gate con eso es una decisión (CAPTURA.md
  `vfr_ratio_le_1_10`), no un arreglo.
- Overlay de exploración: la fuente se escala también por el ancho
  (`45809a2`); en vertical la tercera línea se cortaba.

### Lo que le toca filmar a Hernán (S22 Ultra)

Android está fuera del POC por ADR-003 ("hornea la ralentización"). Usarlo
en serio exige reabrir ese ADR con evidencia del cronómetro, no rodearlo. Lo
que se pidió: cronómetro de 10 s en cada modo con más de 30 fps que ofrezca la
cámara (Video FHD 60 y Slow motion FHD 240; verificar en la app si hay
FHD 120), transferido **por cable** (archivo crudo de `DCIM/Camera`) y, aparte,
el mismo clip compartido desde Galería, para medir qué hace cada camino.
`Auto FPS` apagado. Después un swing `face_on` en el modo que el cronómetro
apruebe. Con eso se llena `data/capture-paths.yaml` (vacío) o se descarta el
teléfono con números.

### Pasos 2 y 3 (pendientes, definidos)

- **2.** En `sports/golf/events.py`, además del cuadro entero (que no cambia):
  instante en que la trayectoria de las manos cruza su posición de address,
  interpolando entre el cuadro anterior y el posterior; en el evento como
  `t_sub_s` y `fraccion` (0–1 entre `frame` y `frame + 1`) con incertidumbre.
  Test con swing sintético de cruce conocido. En `datos-eventos.json` y en la
  pantalla: "impacto entre el cuadro 44 y el 45 (0,6)" y un botón para ver
  los dos cuadros lado a lado en el reproductor.
- **3.** Sólo con 1 y 2 hechos: `minterpolate` de ffmpeg a 120 fps, rótulo
  "cuadros interpolados, no medidos" quemado en cada cuadro sintético,
  archivo aparte que ninguna métrica lee; lámina de los cuadros entre 44 y 45
  para decidir si sirve o si el shaft sale fantasma. Sin RIFE ni FILM
  (ADR-010).

---

## 12 de septiembre de 2026 — cuarta sesión: interfaz de exploración (`web/` + `/api/datos`)

Una pantalla: subir un video → el `overlay.mp4` con los palitos en un
reproductor con cámara lenta, cuadro a cuadro y zoom, las fotos por evento y
toda la data en tablas. Prompt de origen: `docs/prompts/01-interfaz-exploracion.md`.
Los comandos y qué esperar están en `README.md`.

### Qué existe

| Pieza | Dónde | Probado con |
|---|---|---|
| Cola de exploración: un trabajo por vez, estimador CoreML creado una vez y compartido, `trabajo.json` por trabajo en `data/exploracion/<id>/` (sobrevive al reinicio) | `service/exploracion.py` | 7 tests nuevos en `tests/test_service.py` con estimador falso (173 en total, ~40 s) |
| `PUT /api/datos?filename=&altura_m=` (cuerpo crudo → 202 con id) · `GET /api/datos/{id}` (estado, progreso, `datos-eventos.json` cuando está listo, URLs de archivos) · `GET /api/datos/{id}/archivos/{nombre}` (lista blanca; `?descargar=true` → attachment) | `service/app.py` | TestClient + estimador real con `~/Desktop/cortado.mp4`: listo en 9,6 s |
| `Range`/206 para arrastrar el video | `FileResponse` de Starlette 1.6.0 lo hace solo (verificado: 206, `Content-Range`, bytes correctos). **No se portó** el `route.ts` de `padel-coach` | test + curl |
| `explore()` avisa la etapa (`stage`) y el progreso también al dibujar; el overlay sale con `-g 12` (GOP corto: retroceder un cuadro no decodifica 250) | `kinelab/explore.py` | test de explore + corrida real |
| App Next.js 16.3.4 (`--webpack`, ADR-015), React 19, Tailwind 4, pnpm. Una página. Proxy `/api/*` → 8765 (`KINELAB_API` para cambiarlo), `proxyTimeout` 600 s | `web/` | `pnpm lint` y `pnpm build` limpios; el flujo entero por el proxy con `curl` (202, etapas, 206 byte a byte igual al backend, CSV, attachment, PNGs) |
| Reproductor propio: `<video>` + `requestVideoFrameCallback`, seek a `(n + 0,5) / fps`, verificación del cuadro llegado por `mediaTime` (aviso si no coincide), 0,1×–1×, ◀ ▶ y flechas (shift = 10), marcas de evento en la línea de tiempo, **zoom 1–4× con la rueda o botones y paneo arrastrando** (pedido de Hernán durante la sesión) | `web/src/components/Reproductor.tsx` | **nunca abierto en un navegador** |
| Subida con progreso (XHR), sondeo cada 0,5 s, el último trabajo vuelve al recargar (localStorage) | `web/src/app/page.tsx`, `lib/api.ts` | idem |
| Tabla por evento (codos, rodillas, caderas, hombros, líneas, tronco, brazos, altura de manos, pelvis/tórax/cabeza/manos vs address en cm y %, velocidades, rotaciones aparentes), duraciones y tempo, picos, diferencias vs address, TODAS las columnas por evento, calidad del motor | `web/src/components/TablaEventos.tsx` | idem |
| Tabla por cuadro entera (118 columnas), virtualizada, filtro de columnas, clic en fila → cuadro, fila actual resaltada, descargas de CSV/JSON/analysis/capture/overlay | `web/src/components/TablaCuadros.tsx` | idem |

### Reproductor: lo evaluado y por qué no hay librería

Datos del registro de npm (`pnpm view`, 12/9/2026):

| Candidata | Versión | Licencia | Peso (unpacked) | Cuadro a cuadro | H.264 en Chrome |
|---|---|---|---|---|---|
| Video.js | 8.24.0 | Apache-2.0 | 18 MB | no; seek a `(n+0,5)/fps` a mano | sí |
| Plyr | 3.8.4 | MIT | 5,3 MB | no; idem | sí |
| Vidstack / `@vidstack/react` | 0.6.15 (tag `latest`) | MIT | 2 MB / 125 kB | no; idem | sí |
| react-player | 3.4.0 | MIT | 40 kB | no; idem (envuelve `<video>`) | sí |
| Propio: `<video>` + `requestVideoFrameCallback` | — | — | 0 | seek a `(n+0,5)/fps` **con verificación del cuadro presentado** | sí |

Ninguna da cuadro a cuadro real: el navegador no tiene API para eso, todas
terminan en un seek, y la única forma de saber **qué cuadro se mostró** es el
`mediaTime` de `requestVideoFrameCallback`, que ninguna expone. Como ADR-014
ya fija ese enfoque para el visor definitivo, se escribió propio: cero
dependencias y nada que tirar después. Supuestos de Chrome: `playbackRate`
0,1 anda (mínimo 0,0625); Firefox lo limita a 0,25 y no tenía rVFC hasta
hace poco (hay caída a `timeupdate`, un cuadro desfasado posible).

### Desviación anotada: invariante 10 de `CONTEXTO.md`

Esta pantalla reproduce `overlay.mp4` **pre-renderizado como única vista**, lo
que la invariante 10 prohíbe ("se dibuja desde datos, en vivo, sobre el
master"). Es un paso provisorio a pedido, para mirar el resultado del motor
hoy. El visor definitivo (Fase 4.4) dibuja el esqueleto desde `pose.npz` en un
canvas dentro del mismo div que se transforma para el zoom (`marcoRef` en
`Reproductor.tsx`), sobre `master.mp4`; el reproductor de acá es la base de
eso, no un segundo visor. Mientras dure: no se puede apagar el dibujo, ni
ampliarlo sin pixelar, ni cambiar un evento sin volver a renderizar.

### Lo que falta o no está probado

- **Primera prueba de Hernán (17:28):** el video cargaba al 100 % y no pasaba
  nada. Causa medida: el proxy de `next dev` trunca el cuerpo a los 10 MiB de
  `experimental.proxyClientMaxBodySize` y deja la conexión colgada sin error;
  el `.mp4` pesaba 20 MB. Subido a 2 GB en `web/next.config.ts` y verificado
  por su propio front: 202, archivo idéntico byte a byte, 265 cuadros
  procesados en 11,5 s. Anotado en `AGENTS.md` §Cosas que muerden.
- **El resto del front sigue sin verse en un navegador** (regla de trabajo):
  lo prueba Hernán con la lista de abajo. Lo que más puede fallar sin haberlo visto: el
  tamaño del recuadro del video (vertical 1080×2320: alto 78 % de la ventana),
  el aviso "pedí el cuadro n y mostró m" si el `mediaTime` no cae en `n/fps`,
  y el ancho de la tabla de 118 columnas.
- Un trabajo por vez, sin cancelación, sin borrar trabajos viejos:
  `data/exploracion/` crece ~20 MB por clip de 3 s (las tres fotos PNG pesan
  3,7 MB cada una; se podrían escribir como JPEG).
- El estimador se carga con el primer trabajo (3–4 s); no se precalienta al
  arrancar el servidor.
- La página vieja del gate sigue en `http://127.0.0.1:8765/` y no se usa.
- Al cerrar el servidor con Ctrl-C puede aparecer `recursive_mutex lock
  failed` de CoreML: es el teardown al salir del intérprete, ya con todo
  escrito; no afecta a los trabajos.

### Para que pruebes vos

0. En esta Mac el **8765 tiene un `python -m service` viejo** (PID 9363, de
   las 15:59, anterior a estos cambios) y el **3000 lo ocupa `work-hunter/web`**.
   Matá el viejo (`kill 9363` o `lsof -nP -iTCP:8765`) y levantá el nuevo:
   `.venv/bin/python -m service`. Después `cd web && pnpm install && pnpm dev`:
   si el 3000 está ocupado Next avisa y usa el 3001.
1. Subir `~/Desktop/cortado.mp4` con altura 1,75. Debería verse: barra de
   subida → "cargando el modelo" → "detectando la pose 40 / 76" →
   "dibujando 30 / 76" → resultado en ~10 s. Aviso amarillo arriba con "el gate
   diría: hay más de una persona en cuadro (59 %)".
2. Reproductor: el video vertical con los palitos; eventos en la línea de
   tiempo: address 7, top 39, impacto 44. Probar ◀ ▶ y las flechas (el
   contador y la imagen tienen que cambiar juntos, sin aviso amarillo),
   shift + flecha (10 cuadros), espacio y clic en el video (reproducir /
   pausar), velocidad 0,1× y 0,25×, arrastrar la línea de tiempo, los botones
   "ir a address / top / impacto", **zoom con la rueda sobre el video y con
   + − 1:1, y mover con arrastre**.
3. Fotos: clic en la de impacto → el reproductor salta al cuadro 44 y la
   página sube.
4. Tablas: en address codo izq/der 168° / 171°, rodillas 176° / 180°; tempo
   6,4 : 1 (backswing 1066,7 ms, downswing 166,7 ms). Filtrar columnas por
   "codo"; clic en una fila → ese cuadro; "ir al cuadro actual"; las cinco
   descargas.
5. Recargar la página: vuelve el último resultado sin subir de nuevo.
6. Subir un archivo que no es video: tiene que mostrar "No salió. …" con el
   error del motor, no colgarse.

### Siguiente

Con lo que digas del front: ajustes. Después, lo pendiente de las sesiones
anteriores (abajo): clips reales por percepción y análisis, umbral de
encuadre, calibración de cámara, y la Fase 4 propiamente dicha (`master.mp4`,
visor desde `pose.npz` sobre este reproductor, corrección de eventos).

---

## 12 de septiembre de 2026 — tercera sesión: Fases 1, 2 y 3 construidas sin material real

### Desviación de proceso, anotada

A pedido explícito del entrenador ("avanzá full en las fases"), se construyó
código de las Fases 1, 2 y 3 **sin clips reales que hayan pasado el gate**, contra
lo que fija `ESPECIFICACION.md` ("una fase por vez", "material antes que
código"). Se hizo con datos sintéticos y con un clip heredado de pádel para
probar la cadena de percepción. Todo criterio de aceptación que necesita
material real sigue **abierto** y está listado abajo. Regla de trabajo:
el agente trabaja normal (pruebas de funcionalidad con corridas reales, tests,
subagentes y workflows cuando convengan); lo único que NO hace es levantar el
front y verlo en el navegador con capturas, salvo pedido explícito. El front
lo prueba el entrenador.

### Commits de esta sesión

- `8ede11a` Fase 0 de agente cerrada (94 tests, fps_truth, gate, checklist).
- `e1b4b89` `service/`: página HTML local para pasar clips por el gate
  (adelanto de 4.3 a pedido). `python -m service` → http://127.0.0.1:8765.
- `ed2b865` Fase 1: `kinelab/perception/` completo, `python -m kinelab.perception`.
- `5f7efaa` Fase 2: `kinelab/events/`, `kinelab/contract/`,
  `kinelab/metrics/registry.py`, `sports/golf/events.py`, `python -m kinelab analyze|adjust`.
- Fase 3: `kinelab/metrics/` (sextuplo, ±1 cuadro, repetibilidad, ganancia),
  `sports/golf/metrics.py` + `sports/golf/mdc.yaml`, `truth/` (arnés con su venv),
  `truth/reports/mdc-2026-09-12.json`.

### Qué hay, qué prueba cada cosa

| Pieza | Comando | Probado con |
|---|---|---|
| Verdad del fps | `.venv/bin/python -m kinelab.tools.fps_truth CLIP --duracion-real S --nominal 120` | clips sintéticos (tests) |
| Gate de ingesta | `.venv/bin/python -m kinelab.ingest CLIP --atleta a --gesto driver --vista face_on --camino ID` | clips sintéticos (tests) |
| Página del gate | `.venv/bin/python -m service` (opcional `--data DIR --port N`) | TestClient (34 tests); **nunca abierta en un navegador** |
| Modelos | `.venv/bin/python -m kinelab.perception.models [--download]` | los dos verifican por hash en `models/` |
| Percepción | `.venv/bin/python -m kinelab.perception TAKE_DIR [--cpu] [--overwrite]` | estimador falso (tests) + **una corrida real** sobre `padel-coach/samples/demo_h264.mp4`: 230 cuadros en 10 s con CoreML, 82 % de detección, gate rechaza por varias personas (correcto) |
| Análisis | `.venv/bin/python -m kinelab analyze TAKE_DIR` | swing sintético (`tests/helpers/synth_swing.py`) |
| Corrección manual | `.venv/bin/python -m kinelab adjust TAKE_DIR --rep 1 --event top --frame F` | sintético; round-trip y colisión |
| Arnés de verdad | `cd truth && .venv/bin/python -m kinelab_truth` (12 s) | escribe `sports/golf/mdc.yaml` y `truth/reports/`; tests: `cd truth && .venv/bin/pytest -q` (4) |
| Calibrar la cámara real | `cd truth && .venv/bin/python -m kinelab_truth.calibrate FOTOS --cols 9 --rows 6 --square-mm 25 --id iphone17pro-1080p120 --out cameras/iphone17pro-1080p120.yaml` | sin correr: necesita fotos de un tablero con el teléfono |
| Modo exploración | `.venv/bin/python -m kinelab datos VIDEO --altura-m 1.75` | probado con dos clips reales de Hernán (WhatsApp 29 fps y un vertical de iPhone 30 fps): overlay, fotos por evento, CSV por cuadro y JSON por evento |
| Suite | `.venv/bin/pytest -q` | 166 tests en verde, ~9 s |

### Decisiones tomadas al codificar (no estaban en los documentos)

- **Señal maestra del swing: el centro de las dos muñecas** (las manos van
  juntas en el grip): independiente de la lateralidad, más estable que una
  muñeca sola. `sports/golf/events.py` lo documenta.
- **Impact** = cuadro más cercano a la posición de las manos en address, dentro
  de ±0,25 s del pico de velocidad de las manos (el palo vuelve a la pelota).
  **Top** = último cambio de signo de la velocidad de las manos proyectada
  sobre el eje principal de la trayectoria address→impact. **Address** =
  último cuadro de la ventana de quietud (< 0,15 alturas/s durante ≥ 0,5 s)
  antes del pico, refinado hacia atrás hasta donde la velocidad deja de bajar.
  Todos los umbrales son `estimacion` y viven en `GolfEventParams`.
- Ventana de agudeza de la segmentación en golf: 3 s (con 1 s, heredado de
  pádel, un swing continuo de ~2 s parece "sostenido" y se descarta).
- `pose.npz` guarda la pose CRUDA del sujeto elegido; relleno de huecos,
  filtrado y máscaras son derivados que se aplican al leer.
- `rotation_deg` horario; `iter_frames` no rota dos veces si OpenCV ya aplicó
  la rotación de metadatos (regla por tamaño y `CAP_PROP_ORIENTATION_AUTO`).
- Umbral de encuadre `body_height_frac_min = None` hasta medirlo: el chequeo
  se reporta `passed: null` con razón "umbral sin medir".
- Modelos: `rtmpose-m-halpe26` (OpenMMLab, sha256 `26f3a19e…`) y `yolox_m`
  0.1.1rc0 de Megvii entrenado en COCO (sha256 `21ff6cfd…`). Los YOLOX de
  Human-Art que rtmlib trae por defecto quedan fuera (ADR-010). **Pendiente de
  licencia:** los datos de entrenamiento "body7" de RTMPose incluyen Halpe;
  su licencia figura como `sin_verificar` en `models.py`.
- OpenCV: `opencv-python` y `opencv-contrib-python` fijados a 4.14.0.94 los
  dos (rtmlib exige ambos; instalan el mismo `cv2`).
- Medido: CoreML compila la sesión en 3,6 s y después tarda 4,7 ms por
  recorte (CPU: 15 ms). Con CoreML, una entrada sin normalizar da scores todos
  NaN: por eso `estimator.py` asierta el rango de entrada y chequea NaN.
- ffmpeg 9: aun con `-fps_mode passthrough`, redondea los PTS al time base del
  encoder (1/fps); `-enc_time_base 1/90000` los conserva. Importa para la
  Fase 4 (master.mp4) y para cualquier retiming.
- **Métricas en cm** necesitan la altura declarada del atleta
  (`data/athletes/<slug>.yaml` con `altura_m`, o `--altura-m`); sin ella
  quedan en `null` con razón. La conversión usa la altura del cuerpo en px del
  cuadro de address.
- **Tabla del arnés (nivel 0, cámara `sin_verificar`, ruido 0,6 % de la altura
  del cuerpo, 16 semillas):** duraciones MDC ≈ 13 ms a 240 fps y `fps_min`
  120; sway/lift/thrust MDC 2,5–4,5 cm por repetición; sway sólo `face_on`,
  thrust sólo `down_the_line`, lifts ambas; **las deltas de flexión de rodilla
  mueren** (declaradas en `face_on`, la flexión ocurre en profundidad). Las
  tolerancias de sesgo (2 cm, 25 ms, 5°) y de MDC (5 cm, 30 ms, 15°) son
  estimaciones declaradas en `truth/kinelab_truth/harness.py`. El arnés sólo
  puede quitar vistas de las que el deporte declara, nunca agregar.
- La ganancia de velocidad angular (pelvis→tórax→brazo) se calcula desde el
  giro aparente de las líneas de cadera/hombros en el plano de imagen; NO está
  validada por el arnés (no es una métrica registrada) y desde `face_on` la
  rotación axial se ve como escorzo, no como giro: sospechosa. Queda en
  `summary.gain` como descriptiva hasta que el arnés la evalúe.

### Lo que sólo material real puede cerrar (abierto)

- Fase 0: filmar cronómetro y sesión; `capture-paths.yaml` sigue vacío.
- Fase 1: umbral de encuadre medido; que la convención de rotación dé 90 en
  un `.MOV` real en vertical; `creation_time` de QuickTime; el determinismo
  CoreML sobre un clip de golf; reporte SynthPose vs RTMPose (1.5, no hecho:
  SynthPose necesita torch, fuera de ADR-015 salvo en `truth/`).
- Fase 2: error contra GolfDB (2.5): la herramienta existe
  (`kinelab.tools.golfdb_eval`), el dataset no está descargado; todos los
  parámetros de `GolfEventParams` y `GOLF_SEGMENTATION` son estimaciones.
- La página `service/` no se abrió en un navegador: **probarla vos** (abajo).
- Fase 3: intrínsecos reales del teléfono (tablero); nivel 1 de validación
  (movimiento humano real) y SynthPose; oclusión y desenfoque no están en el
  barrido; mutation manual de la invariante 15 no hecha sistemáticamente.

### Para que pruebes vos (cuando quieras)

1. `.venv/bin/python -m service` y abrir http://127.0.0.1:8765. Sección 1:
   subir cualquier `.mov`/`.mp4` y ver la tabla de fps; sección 2 se habilita
   cuando `data/capture-paths.yaml` tenga un camino.
2. Con un clip de golf real ingestado (`gate: OK`):
   `.venv/bin/python -m kinelab.perception data/sessions/.../take-01` y después
   `.venv/bin/python -m kinelab analyze data/sessions/.../take-01`. Mirar
   `analysis.json`: `events[]` por repetición y `quality.verdict`.
3. Si un evento está mal: `python -m kinelab adjust TAKE --rep N --event top --frame F`.

### Entorno verificado

`python3.12` = 3.12.14 · ffmpeg / ffprobe 9.0.1 · onnxruntime 1.30.0
(CoreMLExecutionProvider) · rtmlib 0.0.16 · OpenCV 4.14.0.94 · numpy 2.5.3 ·
scipy 1.18.1 · pydantic 2.13.5 · fastapi 0.141.1 · Mac Apple M3 Pro.

### Siguiente

**Interfaz de exploración** (pedido de Hernán): una pantalla con un botón para
subir un video, que corra `python -m kinelab datos` y muestre el `overlay.mp4`
con un reproductor con cámara lenta y cuadro a cuadro, las fotos por evento y
toda la data en tablas. El prompt completo para esa sesión está en
`docs/prompts/01-interfaz-exploracion.md`. La página actual de `service/` no le
sirve y se reemplaza por una app Next.js en `web/`.

Con clips reales: pasarlos por percepción y análisis, medir el umbral de
encuadre, calibrar la cámara con tablero y re-correr el arnés. Sin clips: Fase 4
(servicio con jobs, `master.mp4` H.264 CFR, visor desde datos sobre
`service/`), y evaluar la ganancia en el arnés.

---

## Mensaje de arranque para la próxima sesión

> Estás en `/Users/heralc/Desktop/HDDev/kinelab`. Leé `AGENTS.md`, `CONTEXTO.md`,
> `DECISIONES.md`, `ESPECIFICACION.md`, `CONTRATO.md`, `CAPTURA.md`,
> `HERENCIA.md` y por último `ESTADO.md`. Regla de trabajo: trabajá normal
> (probá la funcionalidad, usá subagentes y workflows si convienen); lo único
> que no hacés es levantar el front y verlo en el navegador con capturas,
> salvo que yo lo pida: el front lo pruebo yo. La interfaz de exploración
> (`web/` + `service/`) está hecha y sin ver en un navegador: empezá por lo que
> yo te diga de ella. Si hay clips reales en `data/sessions/`, pasalos por
> percepción y análisis y decime qué sale. Commit al cerrar cada bloque;
> `ESTADO.md` al cerrar.
