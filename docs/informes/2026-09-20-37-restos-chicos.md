# restos-chicos — 20 de septiembre de 2026

Resumen: los cinco restos están hechos y commiteados uno por uno. Ninguno mueve un
valor publicado: motor **462 pasados / 0 fallados / exit 0** (el mismo 462 de antes de
empezar, sin agregar ni sacar tests), arnés **43 / 0 / exit 0**, `pnpm lint` y
`pnpm build` exit 0. La prueba fuerte es la del punto 5: las tablas por cuadro de los
**20 `pose.npz`** guardados (12.756 cuadros, 116 columnas, 24,7 MB) salen **byte a byte
idénticas, 20 de 20**, antes y después. `hands_speed_curve_top_to_impact` salió del
summary sin tocar el contrato —`summary.metrics` es objeto libre en el schema— así que
`schema_version` sigue en 2.2.0, `registry_version` en 0.3.0 y ningún `metric_version`
se movió; `repeatability_curves` queda donde está, con su test como único uso, como
pedía el prompt. Dos apartamientos, los dos por defecto (abajo), y **una premisa del
prompt confirmada falsa**: el bug de `--data` en `explore()` no existe, que es el
segundo pendiente fantasma en dos encargos seguidos. Nada quedó abierto.
Para Hernán: nada que probar a mano; si querés ver el efecto del punto 2, el próximo
trabajo que subas ya no trae `hands_speed_curve_top_to_impact` en `summary.metrics`.
Encargo: cinco restos de limpieza verificados contra el código, sin mover valores, sin
subir versiones y sin tocar `kinelab/metrics/` ni umbrales.

Hecho:

- `cee5ee7` — **la lista blanca del servicio, como estaba previsto**. `_Servibles` (el
  `dict` con `get` e `in` extendidos que el 35 dejó porque `service/app.py` no estaba en
  su lista) → `media_type(nombre)` en `service/exploracion.py` más `ARCHIVOS_FIJOS`, la
  tupla que enumera el 404, y las dos líneas de `app.py`. El `__contains__` extendido no
  lo usaba nadie. Ningún test cambió (62 en `test_service.py`, todos por HTTP).
- `4d9610a` — **`hands_speed_curve_top_to_impact` sale del summary**. Inyectada a mano
  después del bucle del registro, sin las seis cosas y con `mdc: null`. Se fueron con
  ella la lista `curves` y el import de `repeatability_curves` en `analysis.py`. Los dos
  asserts autorizados del punto 2 pasaron a afirmar contra la fuente que cambia:
  `set(summary.metrics) == {ids del registro}`. Ejemplo del repo regenerado con
  `tests/helpers/gen_analysis_example.py`: 14 líneas menos, nada más.
- `df5e794` — **los dos comentarios que mienten**. `kinelab/explore.py` (docstring y
  comentario de `TRANSITORIOS`) ya no dice que los campos de primer nivel «los retira el
  encargo 36»: los retira R10. Y la línea de `ESTADO.md` del bug de `--data` queda
  tachada con su corrección al lado.
- `a4dd478` — **`CAPTURE_PATHS_FILE`** en `service/app.py` en vez del literal. Una línea.
- `08e8d8b` — **el código muerto**. `trunk_lean_deg` se calculaba dos veces; el cálculo
  bueno subió a antes del dict y ocupa el lugar exacto del muerto.

Probado:

- **Motor**: `462 passed`, 0 fallados, **exit 0**, con `KINELAB_MODELS` a los pesos del
  checkout principal (sin esa variable, 461 + 1 salteado, que es el de `models/`). Mismo
  conteo que la corrida de partida antes de tocar nada: este encargo no agrega ni saca
  tests.
- **Arnés**: `43 passed`, 0 fallados, **exit 0**.
- **Front**: `pnpm lint` **exit 0**, `pnpm build` **exit 0**. No se abrió el navegador.
- **Punto 5, la comparación que pedía el prompt**: `per_frame_table` sobre los **20**
  `pose.npz` de `data/exploracion/` (de 76 a 2977 cuadros, 12.756 en total, 116 columnas,
  24,7 MB de CSV) volcada a CSV antes y después. `cmp` byte a byte: **20 idénticas, 0
  distintas**. Por eso el cálculo se movió para arriba en vez de borrarse la clave:
  borrarla habría dejado los valores iguales pero `trunk_lean_deg` al final de las 116
  columnas.
- **Punto 1, la lista blanca**: `media_type` devuelve `video/mp4` para `overlay.mp4`,
  `image/png` para `evento-r2-top.png` y `evento-r999-impact.png`, y `None` (404) para
  `evento-r2-rodilla.png`, `evento-r-top.png`, `evento-r2-top.png.txt`, `pose.npz` y
  `../trabajo.json`. El mensaje del 404 enumera los mismos 10 nombres en el mismo orden.

Queda abierto: nada de este encargo. Lo que sigue pendiente y no era suyo: los 20
trabajos de `data/exploracion/` siguen en disco con el `summary.metrics` viejo (traen
`hands_speed_curve_top_to_impact`) hasta que **R10** los regenere, y los campos de primer
nivel de `datos-eventos.json` siguen ahí, también hasta R10. `repeatability_curves` queda
en `kinelab/metrics/generic.py` con su test (`tests/test_fase2.py:528`) como **único**
uso: es código de métricas y borrarlo no era de este encargo — lo decide el orquestador.

Para que pruebe Hernán: nada manual. Las tres suites están en verde acá y el front no se
tocó. Si querés verificarlo vos:
`cd /Users/heralc/Desktop/HDDev/kinelab && .venv/bin/pytest -q` (462, exit 0),
`cd truth && .venv/bin/pytest -q` (43, exit 0),
`cd web && pnpm lint && pnpm build` (exit 0 los dos).

Preguntas para el orquestador:

1. **`repeatability_curves` queda sin uso salvo su test.** El prompt decía dejarla y
   avisar: avisado. Sacarla es borrar código de métricas y una entrada del contrato
   (`CONTRATO.md` §summary la nombra al lado de `repeatability_scalar`); es un encargo
   propio, chico, o se queda como está.
2. **Segundo pendiente fantasma en dos encargos seguidos.** El 34 encontró que el bug de
   `__main__.py:103` no existía; el 37, que el de `--data` en `explore()` tampoco. Los
   dos venían de `ESTADO.md`. Puede valer la pena que cada pendiente que se anote ahí
   diga cómo se comprueba que sigue abierto, o se vuelven trabajo de verificación para el
   que los hereda.
3. **El punto 5 casi se hace mal.** «Borrá el primero» era correcto para los valores y
   habría cambiado el orden de las 116 columnas del CSV, que nadie estaba mirando. Si
   hay más limpiezas de este tipo, conviene que el prompt diga «sin mover el orden de
   columnas» junto a «sin mover valores».
