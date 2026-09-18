# pantalla-sin-falsedades — 2026-09-18

Encargo: sacar de la pantalla las cosas falsas que sí se ven — el rótulo «±1
cuadro» fijo, la promesa de «se puede comparar», las tres columnas que ADR-018
retiró y el ± del sub-cuadro leído como el error del instante —, más los avisos
sin repetir y el aviso de contrato anterior. Sólo `web/`; sin regenerar datos y
sin desplegar.

Hecho:

- `web/src/lib/retirados.ts` (nuevo): las claves de ADR-018 en **un solo lugar**
  —`hip_line_rate_deg_s`, `shoulder_line_rate_deg_s`, `arm_left_rate_deg_s`, más
  `gain` y `sequence_order`, que hoy no están en ningún dato—, con `esRetirado`,
  `sinRetirados`, `retiradosEn`, y `contratoAnterior` / `CONTRATO_VIGENTE`
  ("2.0.0").
- Se aplica en los tres lugares: picos y «Todas las variables en cada evento»
  (`TablaEventos.tsx`), y las columnas del CSV (`TablaCuadros.tsx`, que además
  cuenta las que muestra). Lo desconocido no se oculta: sigue saliendo con su id.
- `Metricas.tsx`: la banda es `uncertainty.method` tal cual lo escribe el motor
  (sin `method`, el rango sin rótulo); y `judgment_allowed: true` se lee «juicio
  habilitado (judgment_allowed)». «se puede comparar» no existe más.
- `Avisos.tsx`: con `analysis.json`, muestra `analysis.warnings` **entero, en
  orden y tal cual**, en lugar de `aviso` / `fps_aviso` / `gate_diria`, que son
  copias suyas. `fps_note` queda como estaba. Sin `analysis.json`, lo de hoy.
- `page.tsx`: baja `analysis.json` a nivel de página (lo necesitan los avisos de
  arriba y `Metricas` abajo), agrega las dos líneas nuevas —contrato anterior y
  campos retirados— y rotula el ± del impacto como **precisión interna del
  cruce**, con una línea sin números que dice que no incluye el sesgo contra el
  contacto con la pelota. Lo mismo en `textoSubcuadro` (`etiquetas.ts`), que es
  lo que se ve en las fotos por evento y en la cabecera de la tabla.
- `web/src/lib/retirados.verificar.mjs` (nuevo): verificador sin framework
  (ADR-015), con el patrón de `pose3d.verificar.mjs`.
- Commits: `9107e5b` (los siete archivos de `web/src/` y los dos nuevos),
  y el que lleva este informe y `ESTADO.md`.

Probado:

- **`cd web && node --experimental-strip-types src/lib/retirados.verificar.mjs`
  → exit 0, 0 fallas.** Sobre los tres trabajos de `web/public/demo/`, el filtro
  saca **exactamente** las tres `*_rate_deg_s` y **ninguna otra**, en las tres
  fuentes:

  | trabajo | contrato | columnas | picos | encabezado del CSV |
  |---|---|---|---|---|
  | `72d91d03…` (vid1) | 1.2.0 | 109 → 106 | 4 → 1 | 109 → 106 |
  | `ejemplo-cmu-64_01-down_the_line` | 1.2.0 | 118 → 115 | 5 → 2 | 118 → 115 |
  | `ejemplo-cmu-64_01-face_on` | 1.2.0 | 118 → 115 | 5 → 2 | 118 → 115 |

  Los números que dejan de verse: `hip_line_rate_deg_s` **3662,0** · 4202,5 ·
  3243,74; `shoulder_line_rate_deg_s` 2228,31 · 2307,46 · 453,07;
  `arm_left_rate_deg_s` 1026,43 · 3694,02 · 532,56.

- **Los dos controles del otro lado.** `data/incoming/vid1.kinelab` (2.0.0,
  re-analizado con HEAD) pierde **0 de 115** columnas y 0 de 2 picos.
  `data/examples/analysis.example.json` (2.0.0) **no** saca el aviso de contrato
  anterior; los tres de la demo sí, y los diez bordes de versión (1.0.0, 1.2.0,
  1.9.9, 2.0.0, 2.0.1, 2.1.0, 3.0.0, `null`, `""`, `"vieja"`) dan lo esperado.

- **Mutación manual: 7 de 7 ponen el verificador en rojo** (3 a 12 fallas cada
  una): sacar `hip_line_rate_deg_s` de la lista, agregar `hands_speed_cm_s` que
  no es de ADR-018, `sinRetirados` que no filtra, `retiradosEn` vacío,
  `contratoAnterior` siempre falso, con el `<` al revés, y `CONTRATO_VIGENTE` en
  1.0.0. Restaurado, vuelve a exit 0. La lista esperada está escrita a mano en el
  verificador desde ADR-018: comparar el módulo contra sí mismo no comprueba
  nada.

- **Ninguna frase se repite**, en los tres. vid1 pasa de 3 frases arriba a **4**,
  y la que gana estaba en `analysis.warnings` y en **ninguna** de las tres
  copias: «Sin altura declarada del atleta: las métricas en cm quedan en null…».
  Los dos del mocap quedan en 3 y 3. Las tres copias de `datos-eventos.json`
  están todas adentro de `analysis.warnings` en los tres trabajos: reemplazarlas
  no pierde nada.

- **Grep sobre `web/out/_next/static/chunks/`, antes y después del cambio.**
  Antes, las dos cadenas están, en `app/page-88a59fb9ab051a85.js`. Después,
  **ninguna de las dos** (`grep -rl` exit 1). Y las frases nuevas sí están en
  `app/page-aaa6c870f51f5f04.js` —`juicio habilitado (judgment_allowed)`,
  `precisi\xf3n interna del cruce`, `ya no son una medici\xf3n`—, buscándolas con
  el `\xf3` con el que el compilador escribe la «ó», igual que el `\xb1` del
  prompt. No se grepeó `web/out/demo/`: ahí «±1 cuadro en cada evento ancla…» es
  dato del motor y es lo que la pantalla ahora muestra.

- **`pnpm lint` exit 0 · `pnpm build` exit 0 · `NEXT_PUBLIC_KINELAB_MODO=demo
  pnpm build` exit 0.** No se corrió `pytest`: no se tocó Python, y el 27 tenía
  `kinelab/` y `sports/` a medio escribir en el árbol — correrlo habría dado
  números de un código que no es HEAD.

Queda abierto:

- **La demo hay que reconstruirla y desplegarla** (comando abajo). El arreglo es
  sólo de código: los `analysis.json` de la demo siguen siendo 1.2.0 y las tres
  columnas retiradas siguen en sus archivos — lo que cambia es que la pantalla no
  las muestra y lo dice.
- **La banda de `tempo_ratio` de vid1 en la demo va a seguir diciendo ±1
  cuadro**, porque es lo que dice su `uncertainty.method`. El ±4 real del top
  está en el vid1 re-analizado (`data/incoming/vid1.kinelab`, 2.0.0) y llega a la
  demo cuando se regenere (encargo 13 de la secuencia del 16).
- **`data/publicados.json` marca los tres trabajos con `despliegue: null`** y
  razón «--solo-construir», pero el sitio vivo existe: lo desplegó el orquestador
  a mano el 15/9. El registro no lo sabe, y va a seguir sin saberlo si el
  despliegue se hace con el comando de abajo en vez de con
  `python -m kinelab.tools.publicar`.
- **Una desviación chica, hacia arriba**: el verificador cubre también
  `contratoAnterior` (el prompt pedía sólo las columnas). La mutación manual
  mostró que si no, la función que decide una línea de la pantalla no la miraba
  nadie. Y `uncertainty.method` pasó de `string` a `string?` en `lib/api.ts`: es
  el rótulo que ahora se muestra y viene de un archivo en disco que pudo escribir
  otra versión del contrato. No cambia ningún dato.

Para que pruebe Hernán:

1. **Desplegar la demo corregida**, desde la raíz del repo, todo junto.
   `armar_salida` y `raiz_repo` existen con esos nombres
   (`kinelab/tools/publicar.py:238` y `:150`); el comando es el del prompt, sin
   cambios. **No** usa `python -m kinelab.tools.publicar <id>`, que re-exportaría
   el trabajo a `web/public/demo/`, y este encargo no regenera datos.

   ```bash
   cd web && NEXT_PUBLIC_KINELAB_MODO=demo pnpm build && cd .. && .venv/bin/python -c 'from kinelab.tools.publicar import armar_salida, raiz_repo; print(armar_salida(raiz_repo()))' && cd web && (test -f .vercel/project.json || npx --yes vercel link --yes --project kinelab --scope hernandiazz9s-projects) && npx --yes vercel deploy --prebuilt --prod --yes
   ```

2. **En los tres trabajos**, arriba de todo, después de los avisos del motor y
   separadas por una línea: «Este trabajo se calculó con un contrato anterior: su
   `analysis.json` es 1.2.0 y el vigente es 2.0.0…» y «…trae campos que ya no son
   una medición; no se muestran: hip_line_rate_deg_s · shoulder_line_rate_deg_s ·
   arm_left_rate_deg_s».

3. **En vid1**, abrir «Picos (máximo en todo el clip)»: tiene que quedar **una
   sola fila**, la velocidad de manos. Los 3662,0 de «rotación aparente de
   caderas» no tienen que estar. Y el desplegable «Todas las variables en cada
   evento» tiene que decir **106 columnas**, no 109; buscar `rate` en el filtro
   de la tabla de abajo no tiene que devolver nada.

4. **En «Con este archivo»**, la fila de `tempo_ratio` de vid1: el rótulo de la
   banda es ahora la frase del motor —«±1 cuadro en cada evento ancla a 60.026
   fps (sin_verificar): 2,45 – 2,83»— y no un «±1 cuadro:» inventado por la
   pantalla. En los dos del mocap pasa lo mismo en varias filas. Ninguna fila
   tiene que decir «se puede comparar».

5. **Los avisos de arriba, sin repetirse.** En vid1 son **cuatro** párrafos: los
   tres de `analysis.warnings` —el de EXPLORACIÓN, el de la tasa sin verificar y
   uno nuevo, «Sin altura declarada del atleta…», que antes no se veía— y el de
   `fps_note`. En los del mocap, tres.

6. **El ± del impacto** (vid1, debajo del reproductor): «…· precisión interna del
   cruce ± N ms», y abajo la línea que explica que ese ± no incluye el sesgo
   contra el contacto con la pelota. Lo mismo en los pies de las fotos por evento
   y en la cabecera de la tabla por evento.

Preguntas para el orquestador:

- **Si conviene que el despliegue a mano vuelva a `data/publicados.json`.** Hoy
  el registro dice `despliegue: null` para los tres y el sitio está arriba desde
  el 15/9: el archivo que existe para saber qué salió a internet no lo sabe. Con
  el comando de arriba va a seguir igual. Es del encargo 25, no de éste.
- **Los dos avisos nuevos del 27** van a salir solos en el bloque de arriba, sin
  que la pantalla conozca su texto — es lo que este encargo fue a arreglar. Pero
  sólo en trabajos re-analizados: los tres de la demo son 1.2.0 y no los traen.
