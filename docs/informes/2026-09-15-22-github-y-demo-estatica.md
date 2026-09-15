# github-y-demo-estatica — 2026-09-15

Encargo: subir el repo privado a GitHub, escribir un exportador que produzca la
versión web de un trabajo (recortada al sujeto, liviana, con la transformación
declarada) y un modo demo del front que lea de ahí sin backend, listo para
Vercel. Sin desplegar nada.

## Hecho

- **Repo privado en GitHub: https://github.com/hernandiazz9/kinelab**, `main`
  subido, `visibility: PRIVATE` verificado por `gh repo view`. 6,2 MB de
  archivos versionados antes de la demo; 23 MB de `.git` después.
- **`kinelab/tools/exportar_demo.py`** (`636426a`): de un trabajo de
  `data/exploracion/` escribe `web/public/demo/<id>/` con el video sin palitos,
  el overlay, `transformacion.json`, `pose.json`, los JSON tal cual, el CSV
  recortado al tramo, las fotos por evento en JPEG y el `trabajo.json` que
  devolvería la API; y reescribe `web/public/demo/index.json`. 23 tests en
  `tests/test_exportar_demo.py`.
- **Modo demo del front** (`5fb278a`): `NEXT_PUBLIC_KINELAB_MODO=demo` →
  `output: "export"`, lectura de `/demo/*`, formulario de subir reemplazado por
  la frase que dice por qué, `noindex` en el `<meta>` y `X-Robots-Tag` desde
  `web/vercel.json`. La decisión de por dónde leer está en **un** lugar
  (`web/src/lib/api.ts`).
- **La demo exportada commiteada** (`c7997da`): `vid1` y los dos ejemplos de
  mocap, 20,4 MB en total.
- `README.md` §La demo estática: el comando para regenerarla, y qué es y qué no
  es lo que se despliega.

## Probado

### 1 · El peso, archivo por archivo

| | en `data/exploracion/` | exportado | |
|---|---|---|---|
| `72d91d03…` (`vid1.mp4`) | **424 MB** | **14,89 MB** | ×28,5 |
| `ejemplo-cmu-64_01-face_on` | 4,8 MB | 2,58 MB | |
| `ejemplo-cmu-64_01-down_the_line` | 4,4 MB | 2,40 MB | |
| **total en el repo** | | **20,4 MB** (`web/public/demo/`, 21 MB en disco) | |

`vid1`, archivo por archivo: `overlay.mp4` 6,507 · `video.mp4` 6,422 ·
`datos-por-cuadro.csv` 0,573 · cuatro JPEG de evento 0,281–0,296 ·
`pose.json` 0,161 · `trabajo.json` 0,029 · `datos-eventos.json` 0,025 ·
`analysis.json` 0,019 · `capture.json` 0,002 · `transformacion.json` 0,001 MB.
Los dos de mocap: `overlay.mp4` 1,148 y 0,997 · `datos-por-cuadro.csv` 0,75 ·
`pose3d.json` 0,252 · `pose.json` 0,21.

**Ningún archivo pasa de 6,51 MB y ningún trabajo de 15.** Los 14,89 MB de
`vid1` dejan **0,7 % de margen** contra el objetivo: la palanca es `--crf`
(hoy 23 con `-preset slow`, ~10,6 Mb/s a 618×1080) o `--alto`. Se eligió 23 a
ojo y **no se midió**: el 20 cerró mientras esta sesión corría y midió el
`crf 20` del overlay (94,1 % del laplaciano del original en la caja de las
manos, y el borrón es el obturador, no el códec), pero nadie midió el 23 sobre
el recorte reescalado. Si hace falta bajar peso, ése es el número a medir
primero.

### 2 · El sujeto, ampliado

`vid1`, mediana de `body_height_px` en el tramo: **1113 px**.

| | del alto del cuadro |
|---|---|
| original (3840 px de alto) | **29,0 %** |
| exportado (1080 px de alto) | **56,0 %** |

**×1,93.** El recorte es 1140×1988 px en (506, 957) del cuadro de 2160×3840, y
la escala 0,5433. El límite no es el margen: la caja que contiene al sujeto en
todo el tramo mide **1655 px de alto contra 809 de ancho** —en el top las manos
suben muy por encima de la cabeza—, así que el cuerpo no puede pasar de ~60 %
sin cortar el swing.

El margen por defecto es **0,10 del alto de la caja**, y sale de medir, no de
elegir: en el cuadro del top la cabeza del palo llega a y≈1086 px y el keypoint
más alto del tramo está en 1123. El palo no es un keypoint. Con el 0,10 el
recorte arranca en 957 y quedan **129 px de aire** sobre la cabeza del palo;
verificado mirando el cuadro exportado (palo entero adentro en el top, palo y
pelota adentro en el address).

### 3 · La transformación, sobre datos reales

Los 291 × 26 keypoints del tramo de `vid1`, transformados con
`transformacion.json`, contra el cuadro exportado de 618×1080:

| | mínimo | máximo | |
|---|---|---|---|
| x | 131,2 | 494,2 | dentro de [0, 618] |
| y | 178,3 | 901,9 | dentro de [0, 1080] |

Y la prueba que importa: **dibujé el esqueleto de `pose.json` sobre el
`video.mp4` exportado usando sólo `transformacion.json`** —o sea exactamente lo
que va a hacer el front— en los cuadros del top (722) y del impacto (741). Los
26 puntos y los 27 huesos caen sobre el golfista. Es la verificación de punta a
punta de que recortar el video y no reescribir los puntos funciona.

**Lo que queda fuera del cuadro del ORIGEN se cuenta**
(`puntos_fuera_del_origen`): 0 de 7566 en `vid1`, 0 de 11.102 en el mocap
`face_on`, y **315 de 10.972 (2,9 %) en el mocap `down_the_line`**, donde la
cámara virtual proyecta las manos del top fuera del lienzo de 1080×1920.
Ningún recorte los puede incluir; el archivo lo dice en una frase en vez de
dejar que se descubra mirando.

### 4 · Suites y mutación

- Motor: **295 en verde** (23 nuevos, 32 s). Arnés: **37 en verde** (7,3 s).
- `cd web && pnpm lint` limpio. **Los dos builds limpios**: el local de siempre
  y `NEXT_PUBLIC_KINELAB_MODO=demo pnpm build` → `web/out/` (23 MB, 22 de los
  cuales son `demo/`).
- **Mutación manual: 13 de 13** mutaciones del exportador hacen fallar al menos
  un test (signo del offset, escala invertida, `cuadro_offset` en 0 y corrido
  un cuadro, margen ignorado, recorte sin acotar, un cuadro de menos en el
  `select`, CSV renumerado, `pose.json` sin recortar, tramo sin margen, x e y
  cambiadas, fotos sin recortar, `_par` redondeando para arriba). **Tres tests
  nacieron de ahí y no estaban en el plan**:
  1. *el alto pedido es el alto que sale*, verificado contra el archivo que
     escribió ffmpeg: con `escala = h/alto` en vez de `alto/h` **todo lo demás
     sigue siendo consistente consigo mismo**, porque el tamaño declarado sale
     del mismo número mal. El único testigo de afuera es el video.
  2. *el recorte nunca se pasa del cuadro con tamaño impar*: `_par` redondea al
     par de **abajo**; para arriba empuja el recorte un píxel afuera.
  3. Y el video sintético hubo que rehacerlo: con `testsrc` los cinco cuadros
     vecinos daban **la misma diferencia** que el correcto (su franja móvil deja
     regiones idénticas), así que un `cuadro_offset` en 0 pasaba sin que nada
     fallara. Ahora cada cuadro es distinto de todos los demás en cualquier
     recorte, y el test comprueba además que **distingue** el cuadro: la
     diferencia en los vecinos ±3 y ±5 es más de 4× la del cuadro correcto.

### 5 · El build de demo no puede hablar con un backend

No es una promesa, está medido: en `web/out/_next/static/chunks/` las cadenas
`api/datos` y `api/config` **no aparecen** (la rama local es código muerto y el
minificador la elimina), y en el build local sí aparecen. El `<meta>` que sale
es `<meta name="robots" content="noindex, nofollow, nocache"/>` y
`<meta name="googlebot" content="noindex, nofollow"/>`.

### 6 · Servido estático, por `curl`

`web/out/` con `python3 -m http.server`, sin abrir el navegador. Los 14
archivos que el front pide responden 200 con su media type:
`/` 200 text/html · `/demo/index.json` 200 application/json 3508 B ·
`trabajo.json` 28.734 B · `transformacion.json` 1249 B · `video.mp4` 200
video/mp4 6.422.370 B · `overlay.mp4` 6.506.661 B · `pose.json` 160.537 B ·
`analysis.json` 19.112 B · `datos-eventos.json` 25.111 B · `capture.json`
2423 B · `datos-por-cuadro.csv` 200 text/csv 572.600 B · `evento-top.jpg` 200
image/jpeg 284.703 B · `pose3d.json` del mocap 251.649 B.

Y lo que **no** está: `pose.npz` y `original.mp4` dan **404**. El
`index.json` lista los tres trabajos con su etiqueta, fps, procedencia
(`sin_verificar` en los tres) y eventos.

## Auditoría de lo que hay commiteado (paso 1 del prompt)

Nada nuevo de la clase "no puede ser público" más allá de lo que el prompt ya
sabía. **No borré nada.** La lista para revisar el día que se piense en hacerlo
público:

1. **Coordenadas GPS del lugar de filmación**: `−32,0431 −065,0295`, en
   `docs/informes/2026-09-15-11-diagnostico-vid123.md:48` (`location` del
   `udta` de Samsung). Citadas también en `docs/PLAN.md:63`.
2. **Nombre y correo de Hernán en los 79 commits** (`Hernan Diaz Daives
   <hernandiazz99@gmail.com>`) — reescribir la historia es la única forma.
3. **Rutas absolutas de la máquina** (`/Users/heralc/…`): `ARRANQUE.md:5`,
   `ESTADO.md:2068`, `docs/prompts/01-interfaz-exploracion.md:3,7`,
   `docs/informes/2026-09-14-04-gate-fps-efectivo.md:127`,
   `.claude/skills/orquestador/SKILL.md:10`.
4. **Las rutas a los dos prototipos anteriores** (`HERENCIA.md:5,8`:
   `BMPadel/biomech/` y `padel-coach/`), con la auditoría de sus bugs al lado.
   Es material de otros proyectos, no de éste.
5. **El nombre de pila en 10 archivos** (`CONTRATO.md`, informes 06 y 11,
   prompts, ejemplos y tests de `capture-paths`) y **el modelo de teléfono con
   sus caminos de transferencia** (`data/capture-paths.yaml`: Galaxy S22 Ultra,
   cable, WhatsApp documento).
6. **Nombres y fechas de los clips del teléfono** (`20260907_170638`,
   `vid1/2/3`) en 22 archivos: dicen el día y la hora de filmación.
7. **`data/examples/cmu-mocap/`**: 10 `.amc` + `64.asf` redistribuidos. No es
   dato personal, pero CMU pide atribución explícita y **no crawlear** la base
   (`ATRIBUCION.md`); un repo público es exactamente lo que se crawlea.

No hay ninguna credencial, token ni clave: lo único que matchea `token|secret|
password` son `js-tokens` del lockfile, `passwd.mov` de un test de
path-traversal y la palabra "token" en una frase de un informe. Antes de este
encargo ningún archivo versionado pasaba de 448 KB; ahora los dos videos de
`vid1` pesan 7,2 MB cada uno.

## Queda abierto

- **El `--crf` no se midió.** 14,89 MB de 15 es poco margen; un tramo un poco
  más largo en un trabajo futuro se pasa (la herramienta avisa por stderr, no
  falla). El 23 se eligió a ojo. El **20** cerró mientras esta sesión corría y
  su método —ajuste de rampa al perfil de gris, y laplaciano contra el original
  en cajas fijas— es exactamente el que serviría para elegir el `--crf` del
  recorte reescalado con un número en vez de con un dedo.
- **Se exportan dos videos por trabajo** (`video.mp4` limpio + `overlay.mp4`
  con palitos), y son el 87 % del peso. El overlay es lo que el reproductor
  muestra hoy; el limpio es para cuando el **21** dibuje desde datos. Cuando el
  21 cierre, el overlay se puede dejar de exportar y `vid1` baja a **8,4 MB**.
  La invariante 10 sigue sin cerrar, como antes de este encargo.
- **El `pose.json` que escribo es un formato que inventé acá**, porque el 21 no
  cerró: `{schema, reference_frame, fps, tamano_origen, cuadro_offset, cuadros,
  nombres, huesos, eventos_frame, keypoints, scores, plausibility, provenance}`,
  keypoints a 1 decimal y scores a 2 (160 KB para 291 cuadros de `vid1`). Es la
  forma que el prompt del 21 pide para `GET /api/datos/<id>/pose`; **si el 21
  elige otra, hay que cambiarla en los dos lados**.
- **No hay `master.mp4`** (ESPECIFICACION 4.2). El video exportado es H.264 CFR
  con `-g 12` y rotación aplicada, o sea *casi* un master, pero su hash no va a
  `analysis.json` y los índices de cuadro siguen refiriéndose al original. Eso
  es del 21.
- **Range/206 no se probó en Vercel.** El servidor de prueba
  (`python3 -m http.server`) devuelve 200 y no 206, así que el cuadro a cuadro
  sobre un archivo de 6,4 MB se apoyó en que Chrome se baje el archivo entero
  (`+faststart` está puesto). La CDN de Vercel sí hace Range; hay que
  confirmarlo en el deploy real.
- **La pantalla no se abrió** (regla de trabajo). Lo que más puede fallar sin
  verla: que el reproductor arranque en el cuadro 612 y no en el 0 (el slider
  va de 612 a 902 en `vid1`), y que la línea que explica el recorte no moleste
  debajo del video.
- **`ListaTrabajos` no muestra los `avisos`** que el `index.json` trae por
  trabajo. Están en el archivo por si sirven; el componente es del 16 y no lo
  toqué.

## Desviaciones

- **Del contrato, ninguna.** `transformacion.json`, `pose.json` y el
  `index.json` no están en `CONTRATO.md` §Layout y no se agregaron: son
  artefactos de una exportación para mostrar, cada uno con su `schema` declarado
  adentro (`kinelab.transformacion/1.0.0`, `kinelab.pose2d/1.0.0`,
  `kinelab.demo/1.0.0`). Si el visor desde datos (21) los vuelve parte del
  producto, ahí sí hay que meterlos en el contrato. **Pregunta para el
  orquestador.**
- **Del prompt, dos de archivos.** (1) `web/src/components/Reproductor.tsx` y
  `DosCuadros.tsx` reciben `primerCuadro` (default 0, o sea el modo local no
  cambia en nada). Sin eso el reproductor pide el cuadro 672 en un video de 291
  cuadros y la demo no funciona; la alternativa —renumerar los eventos en
  `api.ts`— mostraría "cuadro 60" donde el análisis dice 672, que es
  precisamente lo que el resto del encargo evita. Ninguno de los dos archivos
  está asignado a un encargo en curso; el **21** va a reescribir el reproductor
  y se va a encontrar el `primerCuadro` ya puesto. (2) `web/src/app/layout.tsx`
  para el `noindex`, que el propio prompt pide.
- **Del prompt, una de alcance, hacia arriba**: se exporta también el
  `overlay.mp4` recortado, además del video limpio que el prompt pide. Es la
  alternativa que el propio prompt prevé («si no, usá el overlay exportado y
  anotá que queda pendiente»): sin el 21 cerrado, el reproductor no dibuja
  nada, y un video limpio sin esqueleto no es la demo. Los dos salen del mismo
  recorte, así que `transformacion.json` vale para los dos.
- **El `noindex` va también en modo local**, no sólo en demo: una pantalla en
  `localhost` tampoco tiene nada que indexar y un solo camino es menos que dos.

## Para que pruebe Hernán

### A · Vercel (los pasos exactos; **el deploy no lo dio esta sesión**)

1. vercel.com → **Add New… → Project → Import Git Repository** →
   `hernandiazz9/kinelab`. Si no aparece, **Adjust GitHub App Permissions** y
   darle acceso a ese repo (es privado).
2. En la pantalla de configuración, **Root Directory: `web`** (botón *Edit* al
   lado de `./`). Es el único campo obligatorio: el resto lo lee
   `web/vercel.json`, que ya trae `framework: nextjs` y
   `buildCommand: NEXT_PUBLIC_KINELAB_MODO=demo pnpm build`.
3. **No hace falta agregar ninguna variable de entorno.** Si preferís verla en
   el panel igual: Settings → Environment Variables →
   `NEXT_PUBLIC_KINELAB_MODO = demo`, en Production y Preview.
4. **Deploy.** Tarda ~1 min. Cada push a `main` redespliega solo.
5. Si el sitio queda en blanco o dice que no encuentra los trabajos: mirá
   `https://<tu-url>/demo/index.json` a mano. Si eso da 404, el Root Directory
   no quedó en `web`.

### B · El sitio, cuando esté arriba (o en local, ver C)

1. **Arriba de todo**, en lugar del formulario de subir, tiene que estar el
   recuadro ámbar que dice que el motor no se despliega y que acá no se puede
   subir un video. **Si ves el formulario de subir, la variable no llegó.**
2. **«Trabajos anteriores y ejemplos»** con tres: `vid1.mp4` y los dos
   `cmu-64_01`. Abrí `vid1.mp4`.
3. **El video**: el golfista tiene que llenar la pantalla, no ser una figurita
   entre árboles. El palo entero adentro en el top, la pelota adentro en el
   address. El reproductor **arranca en el cuadro 612, no en el 0**, y la línea
   de tiempo va de 612 a 902: es a propósito, el video son los 291 cuadros del
   swing y los números siguen siendo los del original.
4. **Los botones «ir a address / top / impacto / follow_end»** tienen que saltar
   a 672 / 722 / 741 / 842 y **mostrar ese cuadro**. Si aparece el aviso ámbar
   «pedí el cuadro N y el navegador mostró el M», copiámelo: significa que el
   offset del recorte y el seek no están de acuerdo.
5. **«ver los cuadros 741 y 742»**: los dos lado a lado. En el 741 la pelota
   está en el tee, en el 742 ya salió.
6. **Las cuatro fotos por evento**, ahora en JPEG y con el mismo encuadre que el
   video. Un clic lleva a ese cuadro arriba.
7. **El ejemplo de mocap `face_on`**: abajo de las fotos tiene que seguir
   apareciendo el **visor 3-D girable** del encargo 19.
8. **Nada de esto tiene que pedirle nada a un backend.** Si abrís las
   herramientas del navegador no debería haber ninguna llamada a `/api/`.

### C · Verlo en tu Mac antes de subirlo (sin backend)

```bash
cd web && NEXT_PUBLIC_KINELAB_MODO=demo pnpm build
cd web/out && python3 -m http.server 8812
```

y abrir `http://127.0.0.1:8812`. Es exactamente lo que va a servir Vercel.

### D · Regenerar la demo cuando cambie algo

```bash
.venv/bin/python -m kinelab.tools.exportar_demo data/exploracion/72d91d030f12490692019526b34f188f data/exploracion/ejemplo-cmu-64_01-face_on data/exploracion/ejemplo-cmu-64_01-down_the_line --out web/public/demo
```

Tarda ~34 s e imprime el peso archivo por archivo. **Ojo**: si re-subís `vid1`
desde la pantalla, el id cambia y hay que exportar el nuevo y borrar
`web/public/demo/<id-viejo>/` a mano.

## Preguntas para el orquestador

1. **¿El repo se hace público alguna vez?** Si sí, la lista de siete puntos de
   arriba es lo que hay que resolver antes, y los dos primeros (GPS y el correo
   en 79 commits) piden reescribir la historia.
2. **¿`transformacion.json` y `pose.json` entran al contrato?** Hoy son
   artefactos de exportación con su `schema` adentro. Si el 21 sirve
   `pose.json` por la API, deja de ser un artefacto de demo y pasa a ser parte
   del producto.
3. **¿El `pose.json` que inventé es el formato del 21?** Está descrito arriba.
   Elegir ahora evita que el 21 lo cambie y la demo quede con otro.
4. **Cuando cierre el 21, ¿se deja de exportar el `overlay.mp4`?** Son 6,5 de
   los 14,9 MB de `vid1`.
5. **¿La demo se regenera sola o a mano?** Hoy es un comando manual y
   `web/public/demo/` está commiteado. Si los trabajos se re-suben seguido, los
   ids cambian y los viejos quedan en el repo hasta que alguien los borre.
6. **`vid1` sigue siendo el trabajo del 15/9 a las 13:17**, con el top y la
   escala de entonces. Si el 16 o el 18 cambian los eventos, hay que re-subirlo
   y re-exportar.
