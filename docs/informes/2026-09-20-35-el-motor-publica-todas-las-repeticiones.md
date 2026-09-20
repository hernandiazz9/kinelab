# el-motor-publica-todas-las-repeticiones — 2026-09-20

Resumen: `datos-eventos.json` publica ahora **todas** las repeticiones en
`repeticiones_detalle` —eventos, tolerancias, sub-cuadro, escala, duraciones, picos,
la tabla por evento y las diferencias contra **su** address—, el overlay rotula los
eventos de todas (`R2 IMPACT`) y las fotos de la 2 en adelante salen como
`evento-r<N>-<id>.png`. **Los campos de primer nivel no se movieron: medido sobre el
`pose.npz` guardado de `cortado3-lento`, las 27 claves de antes valen exactamente lo
mismo y la única nueva es `repeticiones_detalle`** (comparación contra el código de
`f95875c` extraído con `git archive`, la misma pose en los dos). El número que este
encargo destapa: la repetición 2 tiene escala **831,3 px** contra 783,9 de la 1
(6,0 %), y sus desplazamientos estaban medidos contra el address **de la 1** —
`pelvis_dx_vs_address_cm` en su top daba **−2,21 cm** crudo y da **−7,05** bien
medido, **4,84 cm de diferencia contra un MDC de 2,42**, y ahora coincide con la
métrica (−7,1). También el pico de manos del clip (4,85 bh/s) resultó ser el de la
repetición **2**, publicado en una pantalla que dice «repetición 1». Suite motor
**457 pasados, 0 fallados, 1 salteado, exit 0** (eran 448; +9 tests); arnés **43/0,
exit 0**; `pnpm lint` y `pnpm build` exit 0; verificador de retirados exit 0, 0
fallas. Mutación manual: **7 bugs inyectados, 7 en rojo**. **Para decidir (no era de
esta sesión): el 36 —el selector— y cuándo se retiran los campos de primer nivel.**

Para Hernán: no hay nada que probar a mano en el front (este encargo no lo toca);
si querés ver el dato nuevo, `.venv/bin/python -m kinelab datos data/incoming/cortado3-lento.mp4 --altura-m 1.75`
y mirá `repeticiones_detalle` en su `datos-eventos.json` y las tres fotos `evento-r2-*.png`.

Encargo: `docs/prompts/35-el-motor-publica-todas-las-repeticiones.md` — la mitad del
motor del selector de repetición: publicar todo por repetición, sin tocar el front.

Hecho:
- `4cb85a5` — `kinelab/explore.py`: `repeticiones_detalle` en `datos-eventos.json`,
  una entrada por repetición con los 16 campos que pedía el prompt y con los nombres
  que ya existían. Las funciones que armaban la tabla por evento, las diferencias, las
  duraciones y los picos se extrajeron a `_en_cada_evento`, `_diferencias_vs_address`,
  `_duraciones` y `_picos`, y las usan el primer nivel y cada repetición: una sola
  fuente, no dos que se pueden separar.
- `4cb85a5` — **`_rebasar`, que es el corazón del encargo.** Las columnas
  `*_vs_address_*` de la tabla por cuadro se calculan todas contra **un** cuadro (el
  address de la repetición 1). Para otra repetición se le resta la fila de su propio
  address: la referencia se cancela y queda `pt[evento] − pt[address_de_esta_rep]`,
  que es lo que la columna dice medir. Las dos filas caen en la misma repetición —el
  address es su primer cuadro— así que se dividieron por la misma escala. La
  repetición cuyo address **es** ese cuadro pasa con `base=None` y **no se le toca un
  solo float**: por eso el primer nivel no se mueve por construcción, no por suerte.
- `4cb85a5` — el overlay: `render` recibe `[(rep, eventos)]` y rotula `R2 IMPACT`.
  **Un solo `overlay.mp4`.** `_TEXT_TEMPLATES` suma el `R99` para que el tamaño de la
  fuente siga fijándose con la línea más ancha posible y no cambie entre cuadros.
  `foto_de_evento(rep, evento)` nombra las fotos: la 1 conserva `evento-top.png`.
- `4cb85a5` — `service/exploracion.py`: la lista blanca acepta las fotos por
  repetición **por forma** (`evento-r<N>-<evento>.png`, expresión anclada, N de 1 a 3
  cifras, el evento uno de los cuatro que ya estaban), porque cuántas hay lo decide el
  material y no hay máximo razonable que quemar. `archivos_servibles()` las lista en
  orden de repetición y de evento.
- `3114f86` — `tests/test_todas_las_repeticiones.py` (8 tests) y uno nuevo en
  `tests/test_service.py`.
- `5730219` — `CONTRATO.md` §Versionado: **`datos-eventos.json` no es parte del
  contrato y no lleva `schema_version`** (es la salida del modo exploración), así que
  agregarle un campo no bumpea nada; y §La escala anota que ahora la escala de cada
  repetición llega a la pantalla. Más el docstring de `exportar_demo` y su test.

Probado:
- **Corrida real, `cortado3-lento` (2977 cuadros, 240,15 fps), desde el `pose.npz`
  guardado a un directorio temporal** (invariante 1: el modelo no se volvió a correr;
  no se pisó ningún trabajo). El «antes» es `f95875c` extraído con `git archive` y
  corrido con el mismo script sobre la misma pose.

  | | rep 1 | rep 2 |
  |---|---|---|
  | cuadros | 1052–1765 | 2322–2970 |
  | eventos | address 1052 · top 1284 · impact 1364 | address 2322 · top 2548 · impact 2624 |
  | `follow_end` | ausente | ausente |
  | escala | **783,9 px** | **831,3 px** (+6,0 %) |
  | duraciones | 966,1 / 333,1 ms · tempo 2,90 | 941,1 / 316,5 ms · tempo 2,97 |
  | pico manos | 4,76 bh/s · 700,9 cm/s | **4,85 bh/s** · 654,58 cm/s |
  | sub-cuadro del impacto | 1364 + 0,1468 | 2624 + 0,0884 |

  `repeticiones_detalle` salió con **2 entradas**. El pico de primer nivel es
  **4,85 bh/s**, que resulta ser el de la repetición **2** aunque la pantalla diga
  «repetición 1»: es otro número que era de otra repetición sin decirlo.
- **Primer nivel: 27 claves antes, 28 después, la nueva es `repeticiones_detalle`, y
  NINGUNA de las 27 cambió de valor.** Era la condición de parada del prompt.
- **Lo que arregla el rebase, en material real** (repetición 2, contra un MDC de
  **2,416** en `pelvis_sway_impact_cm`):

  | | fila cruda (contra el address de la rep 1) | rebasada | métrica de `analysis.json` |
  |---|---|---|---|
  | `pelvis_dx_vs_address_cm` en el top | −2,21 | **−7,05** | −7,1 |
  | `pelvis_dx_vs_address_cm` en el impacto | 12,54 | **7,69** | 7,7 |

  **4,84 cm de error**, dos veces el MDC. En la repetición 1 los tres números
  coinciden hasta el redondeo del sextuplo (3,684 / 3,684 / 3,7 en el top;
  22,581 / 22,581 / 22,6 en el impacto).
- **Archivos `evento-*` que quedaron** (6, contra 3 antes): `evento-address.png`,
  `evento-top.png`, `evento-impact.png`, `evento-r2-address.png`, `evento-r2-top.png`,
  `evento-r2-impact.png`. Tres por repetición porque a este clip le falta el
  `follow_end` en las dos. **Un solo `overlay.mp4`** (16,47 → 16,48 MB: lo que pesan
  los rótulos).
- **Suites.** Motor `.venv/bin/pytest -q`: **457 pasados, 0 fallados, 1 salteado,
  exit 0** (eran 448 + 1 salteado; **+9 tests**). El salteado es el de los pesos de
  `models/`, que git ignora y por eso no están en el worktree. Arnés desde `truth/`:
  **43 pasados, 0 fallados, exit 0**. `cd web && pnpm lint` exit 0 · `pnpm build`
  exit 0 · verificador de retirados **exit 0, 0 fallas, 11 bordes de versión**.
- **Mutación manual: 7 bugs inyectados, 7 en rojo, control en verde.** (1) `_rebasar`
  devolviendo la fila cruda → 1 en rojo; (2) `repeticiones_detalle` con sólo la primera
  → 3; (3) las fotos sin el prefijo de repetición → 2; (4) el rótulo del overlay sin la
  repetición → 1; (5) los picos de cada repetición calculados sobre el clip entero → 1;
  (6) el `escala_px` de primer nivel tomado de `quality` en vez de la repetición 1 → 1
  (lo agarra `test_una_sola_escala.py`, del encargo 33); (7) el detalle usando los
  eventos de la repetición 1 para todas → 3.
  Las mutaciones **4 y 5 no las agarraba nada al principio** y por eso el test cambió:
  el clip sintético dejó de ser `synth_swing(n_reps=3)` —tres repeticiones **idénticas**,
  donde el pico de una es el del clip y dos rótulos distintos no se pueden distinguir—
  y pasó a ser la concatenación de tres swings con downswing de 0,27 / 0,33 / 0,40 s,
  con el golfista **corrido 120 px** (13,7 cm) después del primero. El rótulo se prueba
  renderizando dos cuadros idénticos marcados como el top de dos repeticiones: si el
  rótulo no dijera cuál es, las dos fotos serían la misma imagen.

Queda abierto:
- **Los campos de primer nivel son transitorios y siguen ahí**, duplicando
  `repeticiones_detalle[0]`. Es el corte que pidió el prompt y es el correcto; los
  retira el 36. Hay un test que los ata (`test_los_campos_de_primer_nivel_...`): si
  alguna vez dejaran de coincidir, la pantalla mostraría dos cosas distintas de la
  misma repetición.
- **`escala_cuadro` sigue publicándose sólo con UNA repetición**, y ahora también por
  repetición con la misma regla (o sea, `null` en las dos de `cortado3-lento`). El
  cuadro del máximo de la cadena por repetición **no está en `analysis.json`**:
  `reps[]` lleva `scale_px` y `scale_source` pero no el cuadro, y agregarlo es un bump
  de contrato que este encargo tenía prohibido. Es la misma limitación que anotó el
  encargo 33.
- **`datos-eventos.json` crece ~19 KB por repetición**: en `cortado3-lento` pasó de
  **21,4 a 60,3 KB** con dos. Casi todo es `en_cada_evento`, que es una fila de ~115
  columnas por evento y por repetición. Con diez swings serían ~210 KB, que sigue
  entrando, pero si alguna vez molesta la salida es que el front pida la repetición
  que muestra en vez de recibirlas todas — decisión del 36, no de acá.
- **`follow_end` falta en las dos repeticiones de `cortado3-lento`**, así que cada una
  tiene tres fotos y no cuatro. Viene del encargo 31 y no se tocó.
- **`picos` por repetición es el máximo de SU tramo**, y el de primer nivel sigue
  siendo el del clip entero. Es la única de las 16 claves del detalle que no vale «lo
  que hoy es de la rep 1», porque lo que hoy hay no es de ninguna repetición en
  particular. Queda anotado por si el 36 quiere el otro criterio.
- **No se tocó** `web/` (ni `retirados.verificar.mjs`: no se puso en rojo),
  `kinelab/contract/schema.json`, `analysis.json` (sigue en 2.1.0), `kinelab/analysis.py`,
  `kinelab/metrics/`, `sports/`, `truth/`, ningún umbral, ningún `metric_version` ni el
  `registry_version`. **No se regeneró `data/exploracion/` ni la demo** y no se corrió
  pose sobre ningún clip.
- **El verificador de retirados hay que correrlo desde `$KLAB/web`, no desde el
  worktree**: lee `web/public/demo/`, que git ignora, y en el worktree no existe (el
  script muere con ENOENT y **exit 0**, que es otra cosa que muerde: el error no llega
  al código de salida). Los tres archivos que compara —`retirados.ts`, la demo y
  `analysis.example.json`— son idénticos en los dos lados y esta sesión no tocó
  ninguno.

Para que pruebe Hernán:
- **Nada del front**: este encargo no lo toca y el prompt lo dejó explícito. El front
  sigue pidiendo `evento-<evento>.png` por nombre (`web/src/app/page.tsx:305`), o sea
  las de la repetición 1, y nunca recorre la lista de archivos: las claves nuevas no
  lo rozan.
- Si querés ver el dato nuevo con tus propios ojos, sin navegador:
  `.venv/bin/python -m kinelab datos data/incoming/cortado3-lento.mp4 --altura-m 1.75`
  (~5 min de pose) y después
  `python -c "import json;d=json.load(open('data/incoming/cortado3-lento.kinelab/datos-eventos.json'));[print(r['rep'], r['eventos_frame'], r['escala_px']) for r in d['repeticiones_detalle']]"`.
  Tiene que decir `1 {...1052, 1284, 1364} 783.9` y `2 {...2322, 2548, 2624} 831.3`, y
  en la carpeta tienen que aparecer `evento-r2-address.png`, `evento-r2-top.png` y
  `evento-r2-impact.png`. En el overlay, el impacto del segundo swing dice **R2 IMPACT**.

Preguntas para el orquestador:
- **Cuándo se retiran los campos de primer nivel.** El 36 los puede dejar o sacar; si
  los saca, es un cambio que rompe cualquier lector viejo de `datos-eventos.json`
  (hoy: sólo el front y el exportador de demo). El test que los ata está escrito y hay
  que borrarlo en el mismo movimiento.
- **Si el pico de primer nivel se queda como el del clip.** Medido acá: en
  `cortado3-lento` el pico publicado arriba (4,85 bh/s) es el de la repetición **2** y
  la pantalla dice «repetición 1». Hoy no miente —no dice de quién es— pero se lee como
  si fuera de la que se muestra. El detalle ya trae el de cada una.
- **El cuadro de la escala por repetición pide un campo en `reps[]`** de
  `analysis.json` (y con él, otro bump minor). Es lo único de `repeticiones_detalle`
  que sale en `null` teniendo dato adentro del motor (`MetricContext.scale_detail()` lo
  conoce y `analysis.py` lo tira). Lo anotó también el 33.
- **`service/app.py` no estaba en la lista de archivos de este encargo** y es donde
  vive `ARCHIVOS.get(nombre)`. Para no tocarlo, la lista blanca pasó a ser un `dict`
  con `get` y `in` extendidos a la familia `evento-r<N>-…` (`_Servibles`, en
  `service/exploracion.py`). Anda y está testeado, pero lo natural sería una función
  `media_type(nombre)` y dos líneas en `app.py`: si se quiere, es un encargo de cinco
  minutos.
