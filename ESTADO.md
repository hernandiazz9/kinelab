# Estado del trabajo

Dónde quedó el repo al cerrar la última sesión. Se lee **después** de los seis
documentos de `AGENTS.md` y se actualiza al cerrar cada sesión.

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
