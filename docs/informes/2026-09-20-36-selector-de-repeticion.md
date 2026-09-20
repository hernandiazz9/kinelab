# selector-de-repeticion — 2026-09-20

Resumen: la pantalla deja elegir la repetición y **toda** cambia con ella —las métricas,
las dos tablas, el reproductor, los dos cuadros del impacto, la barra de sub-cuadro y las
fotos—. Verificado en el navegador con `cortado3-lento` re-analizado: al pasar de la 1 a la
2, la escala va de **783,9 px (cuadro 1594) a 831,3 px (cuadro 2970)**, `pelvis_sway_top_cm`
de **+3,7 a −7,1 cm** y su fila cruda de la tabla por evento de −2,21 a **−7,05** —los
**4,84 cm** que el 35 midió contra un MDC de 2,42, ahora en pantalla—, los eventos de
1052/1284/1364 a **2322/2548/2624**, las fotos a `evento-r2-*.png`, el reproductor salta al
cuadro 2322 y las **tres** frases dicen «repetición 2 de 2». Un trabajo viejo (`vid1`,
contrato 1.2.0) no muestra selector y se ve como antes: el respaldo está en un solo lugar,
`web/src/lib/repeticiones.ts`. `analysis.json` va a **2.2.0** con `reps[].scale_frame`
—minor: campo nuevo, opcional, nullable, ningún valor se mueve— que es lo que hace que
`escala_cuadro` deje de salir en `null` con más de una repetición. Suites: motor **462
pasados, 0 fallados, exit 0** (eran 458 con los pesos presentes; **+4 tests**), arnés
**43/0 exit 0**, `pnpm lint` y `pnpm build` exit 0, verificador de retirados **exit 0, 0
fallas, 13 bordes**. **Para decidir: los campos de primer nivel siguen sin retirarse (es
R10, como pidió el prompt) y el `picos` de primer nivel sigue siendo el del clip.**

Para Hernán: probalo vos si querés — `.venv/bin/python -m service` y `cd web && pnpm dev`,
abrí el trabajo `b84c7b2679bf470097e52d5b8a3fdc08` (ya está analizado en
`data/exploracion/`) y tocá el botón «2»; la lista de qué mirar está abajo.

Encargo: `docs/prompts/36-selector-de-repeticion.md` — el selector de repetición, con
respaldo para los trabajos que ya existen, y `reps[].scale_frame` en el contrato.

Hecho:
- `196e3a4` — **`analysis.json` 2.2.0 con `reps[].scale_frame`**: el cuadro del máximo de la
  cadena de la estatura en ESA repetición, que es de donde salió su `scale_px`. El dato ya
  existía en `MetricContext.scale_detail()` y `analysis.py` lo tiraba. Campo nuevo, opcional
  y **nullable** (con el fallback de escala no hay máximo que mirar, y un `null` se escribe).
  `explore.py` lo copia a `escala_cuadro` de cada entrada del detalle en vez de calcularlo
  una vez fuera del bucle. En el mismo commit, las cuatro cosas que arrastra el bump: el
  ejemplo del repo regenerado con `tests/helpers/gen_analysis_example.py`, los tres asserts
  de `tests/test_fase2.py`, el de `tests/test_una_sola_escala.py`, `CONTRATO_VIGENTE` del
  front y los bordes de versión de su verificador (11 → 13). Más `CONTRATO.md` §Versionado y
  §La escala.
- `e9e2f6e` — **el selector** (`web/src/components/SelectorRepeticion.tsx`) y **el respaldo
  en un solo lugar** (`web/src/lib/repeticiones.ts`). Ahí viven las cinco cosas que antes
  estaban repartidas: qué repeticiones tiene un trabajo (`repeticiones_detalle`, o el primer
  nivel como repetición única), la frase «Repetición N de M» que decían tres componentes
  desde dos fuentes, los nombres de las fotos (`evento-<id>` para la 1 y `evento-r<N>-<id>`
  para las demás, en PNG y en JPG), y la búsqueda de la repetición en `analysis.reps` **por
  número, no por índice** —en un trabajo viejo la pantalla publica una y el `analysis.json`
  puede tener tres, y ahí el índice mentiría—.
- `e9e2f6e` — `Metricas` cambia de firma: recibe la repetición, no el análisis entero (el
  `reps[0]` estaba quemado en tres líneas). `TablaEventos` y `TablaCuadros` reciben la
  repetición en vez del resumen. La tabla por cuadro marca el tramo `frame_start`–`frame_end`
  con fondo más claro y lo dice arriba, porque son las únicas filas con cm.
- `e9e2f6e` — **el estado que se quedaba pegado**: al elegir otra repetición el reproductor
  salta a su address, los dos cuadros del impacto se cierran y la tabla por cuadro se lleva a
  su primer cuadro. El **filtro de columnas NO se resetea a propósito**: es una preferencia
  de quien mira («mostrame las rodillas») y no dice nada de ninguna repetición.
- `a2cded3` — el rótulo de los picos, corregido **por lo que se vio en el navegador**: con el
  respaldo, `picos` es el máximo del clip entero y el encabezado decía «máximo en esta
  repetición». Ahora dice cuál de los dos es.

Probado:
- **Corrida real de punta a punta**: `cortado3-lento.mp4` subido por la API al backend del
  worktree (pose de 2977 cuadros, 240,15 fps), trabajo
  `b84c7b2679bf470097e52d5b8a3fdc08`. `analysis.json` **2.2.0**, 2 repeticiones.

  | | rep 1 | rep 2 |
  |---|---|---|
  | cuadros | 1052–1765 | 2322–2970 |
  | eventos | 1052 · 1284 · 1364 | 2322 · 2548 · 2624 |
  | `scale_px` / `scale_frame` | **783,9 px · cuadro 1594** | **831,3 px · cuadro 2970** |
  | duraciones · tempo | 966,1 / 333,1 ms · 2,90 | 941,1 / 316,5 ms · 2,97 |
  | pico de manos | 4,76 bh/s | **4,85 bh/s** |
  | `pelvis_sway_top_cm` | +3,7 cm | **−7,1 cm** |
  | `pelvis_sway_impact_cm` | 22,6 cm | **7,7 cm** |
  | fila cruda `pelvis_dx_vs_address_cm` en el top | 3,684 | **−7,053** |

  `quality.scale_px` publica `{value: 783.9, frame: 1594}`: el cuadro de la **1**. Ésa es la
  demostración de por qué hacía falta `scale_frame` — hasta hoy era el único cuadro que la
  pantalla tenía, y con dos repeticiones no es el de las dos.
- **En el navegador, con capturas** (excepción que pidió Hernán; `pnpm dev` y
  `python -m service` levantados desde el worktree, con `KINELAB_DATA` y `KINELAB_MODELS`
  apuntando al checkout principal). Con la repetición **1**: selector con dos botones
  («1 desde el cuadro 1052» / «2 desde el cuadro 2322»), métricas 966,1 / 333,1 ms, tempo
  2,90, escala «783,9 px · máximo de la cadena de la estatura en la repetición (cuadro
  1594)» en los tres lugares, fotos `evento-address/top/impact.png`. Tocando **2**: las tres
  frases pasan a «repetición 2 de 2», la escala a «831,3 px (cuadro 2970)» en los tres, los
  «vs address» a «contra el address (cuadro 2322)», las fotos a
  `evento-r2-address/top/impact.png`, la cabecera del reproductor a «cuadro 2322 / 2976 ·
  9,669 s · ADDRESS», la tabla por cuadro a «esta repetición: 2322–2970» con `escala usada en
  esta fila` en `—` hasta el 2321 y **831,3** desde el 2322, y en la tabla por evento
  `pelvis vs address` da **0,0 / 0,0 cm en el address** —la prueba de que cada repetición se
  mide contra el suyo— y **−7,1 / −5,5** en el top. Volviendo a **1**, la escala vuelve a
  783,9 y las fotos a `evento-*.png`.
- **El trabajo viejo, en el navegador**: `vid1` (`1d23b1d37d46…`, `analysis.json` **1.2.0**).
  **Cero botones de selector**, «Repetición 1 de 1.» como antes, sin línea de escala —no
  trae `escala_px` y no se le inventa una—, las cuatro fotos `evento-address/top/impact/
  follow_end.png`, «Picos (máximo en todo el clip)» y el aviso «su analysis.json es 1.2.0 y
  el vigente es 2.2.0».
- **Suites**: motor `.venv/bin/pytest -q` con `KINELAB_MODELS` apuntando a los pesos del
  checkout principal: **462 pasados, 0 fallados, exit 0** (eran 458 en la misma condición;
  **+4 tests**). Sin esa variable son 461 + 1 salteado, que es el de los pesos de `models/`
  que git ignora. Arnés desde `truth/`: **43 pasados, 0 fallados, exit 0**.
  `cd web && pnpm lint` exit 0 · `pnpm build` exit 0.
- **Verificador de retirados**: **exit 0, 0 fallas**, los 3 trabajos de la demo intactos (3
  columnas sacadas en cada uno, las de ADR-018 y ninguna otra), el ejemplo del repo en
  **2.2.0** sin aviso de contrato anterior, y **13 bordes de versión** (2.1.0 y 2.1.1 pasaron
  a `true`: un trabajo suyo no trae `scale_frame`).
- **Los cuatro tests nuevos** (`tests/test_una_sola_escala.py`): el cuadro por repetición y
  **dentro** de ella, con los tres distintos entre sí; el `null` del fallback escrito y no
  omitido; que un 2.1.0 **sin** el campo siga validando y que un `scale_frame` que no es
  entero **no**; y que `datos-eventos.json` publique el de cada repetición. El ejemplo del
  repo, con tres repeticiones, sale con **118 / 811 / 1503** y el `quality` publica 118.

Queda abierto:
- **Los campos de primer nivel de `datos-eventos.json` NO se retiraron**, como pedía el
  prompt: es R10. Siguen duplicando `repeticiones_detalle[0]` y el test que los ata sigue en
  pie. Lo que sí cambió de ellos: `escala_cuadro` de primer nivel pasa de `null` a **1594**
  con dos repeticiones, porque ahora es el de la repetición 1, igual que su `escala_px`. Con
  una sola repetición vale exactamente lo mismo que antes (`quality.scale_px.frame` **es** el
  de la única).
- **El `picos` de primer nivel sigue siendo el del clip entero**, y por eso un trabajo viejo
  lee «máximo en todo el clip». No se tocó: cambiarlo sería mover un valor publicado.
- **El verificador de retirados no corre en un worktree limpio.** Lee `web/public/demo/`, que
  git ignora. Para correrlo con el código de esta rama hubo que **copiar** los cuatro
  archivos que mira de cada trabajo (`datos-eventos.json`, `datos-por-cuadro.csv`,
  `analysis.json`, `index.json`) más `data/incoming/vid1.kinelab/datos-eventos.json` al
  worktree; con la carpeta incompleta muere con ENOENT y **exit 1** (el `exit 0` que anotó el
  35 es cuando falta entera). Los archivos copiados están en `.gitignore` y no entraron a
  ningún commit.
- **No se regeneró `data/exploracion/` ni la demo**, como pedía el prompt. Los 19 trabajos
  viejos y los 3 de la demo siguen en 1.0.0 / 1.2.0 y entran por el respaldo. El trabajo
  nuevo de `cortado3-lento` (`b84c7b26…`) es el único al día y **queda en disco**: es con el
  que se probó y sirve para volver a mirarlo.
- **No se tocó** `kinelab/metrics/`, `sports/`, `truth/`, `service/app.py`, la lista blanca
  `_Servibles` del 35, ningún umbral, el 717, ningún `metric_version` ni el
  `registry_version`. No se agregó infraestructura de tests a `web/` (ADR-015): el selector y
  el respaldo se probaron en el navegador y con el verificador, que es lo que hay.
- **Del contrato, ninguna desviación**: 2.1.0 → 2.2.0 es minor por §Versionado tal como está
  escrita —campo nuevo, opcional, ningún valor publicado se mueve— y no hace falta la excusa
  que necesitó el bump de `fps_provenance`. Por eso no hay entrada en §Desviaciones.
- **Del prompt, una diferencia y una cosa que agrega.** (1) El prompt decía que las tres
  frases «repetición N de M» tienen que decir lo mismo; se cumple en un trabajo **nuevo**,
  donde salen de una sola fuente. En uno **viejo** la tabla por evento y la tabla por cuadro
  siguen sin decirla —es lo que hacían hoy, porque el resumen no declara
  `repeticion_mostrada`— y sólo la dicen las métricas, con el total de `analysis.reps`. Se
  dejó así a propósito: el prompt pedía que un trabajo viejo se viera **exactamente** como
  hoy, y las dos cosas no se pueden cumplir a la vez. (2) El rótulo de los picos no estaba en
  el prompt y se corrigió igual, porque el respaldo lo volvía falso.

Para que pruebe Hernán:
```bash
cd /Users/heralc/Desktop/HDDev/kinelab && .venv/bin/python -m service     # una terminal
cd /Users/heralc/Desktop/HDDev/kinelab/web && pnpm dev                    # otra
```
Después, en `http://localhost:3000/?trabajo=b84c7b2679bf470097e52d5b8a3fdc08`:
1. **Arriba de «Con este archivo» tiene que haber un selector con dos botones**, «1 desde el
   cuadro 1052» y «2 desde el cuadro 2322», con el 1 marcado.
2. **Tocá el «2».** El reproductor tiene que saltar al **cuadro 2322** y decir `ADDRESS`; las
   tres fotos de abajo tienen que cambiar de swing (son `evento-r2-*`, se ve en el rótulo
   quemado del overlay: `R2 ADDRESS`).
3. **Las métricas** tienen que pasar de 966,1 / 333,1 ms a **941,1 / 316,5**, y
   `pelvis_sway_top_cm` de **+3,7 a −7,1 cm**. La línea de arriba, de «783,9 px … (cuadro
   1594)» a «**831,3 px** … (cuadro **2970**)».
4. **En «En cada evento»**, la fila «pelvis vs address» tiene que dar **0,0 / 0,0 cm en el
   address** (si diera otra cosa, la repetición se estaría midiendo contra el address de la
   otra, que es el bug que arregló el 35) y **−7,1 / −5,5 en el top**.
5. **En «Todos los cuadros»** la tabla se lleva sola al 2322, el contador dice «esta
   repetición: **2322–2970**» y la columna `escala usada en esta fila` está **vacía** hasta el
   2321 y vale **831,3** desde el 2322. Las filas de la repetición van con fondo más claro.
6. **Abrí un trabajo viejo de la lista** (por ejemplo `vid1.mp4`): **no tiene que haber
   selector**, tiene que decir «Repetición 1 de 1.» y verse igual que siempre.

Preguntas para el orquestador:
- **Cuándo entra R10 y qué se lleva.** Hoy los campos de primer nivel son lo único que hace
  visible a los 19 trabajos de `data/exploracion/` y a los 3 de la demo, y el respaldo del
  front existe por eso. Si R10 regenera todo, el respaldo se puede borrar y son 30 líneas
  menos; si no, se queda para siempre y conviene que quede escrito que es permanente.
- **Si el `picos` de primer nivel se cambia al de la repetición 1.** Hoy es el del clip, y por
  eso el rótulo tiene dos versiones. Es un valor publicado: moverlo es decisión de dominio, no
  de esta sesión. Medido: en `cortado3-lento` el de primer nivel (4,85 bh/s) es el de la
  repetición **2**.
- **El selector no está en la URL.** Se resetea al abrir otro trabajo y al recargar, así que
  un enlace `?trabajo=<id>` siempre abre la repetición 1. Agregarle `&rep=2` es media hora y
  no estaba pedido; si los enlaces a una repetición concreta importan, es un encargo chico.
