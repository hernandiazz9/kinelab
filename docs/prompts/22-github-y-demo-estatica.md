# 22 — El repo en GitHub y una demo estática del front, con los datos que ya tenemos

Para correr: `/encargo 22` en una sesión nueva. El paso 1 (GitHub) se puede
hacer apenas empieces; el paso 3 espera al 19 (ver §En paralelo).

## Contexto

Hernán quiere ver el front desplegado para mostrar **los datos que ya
tenemos**, sin procesar nada nuevo. Eso se puede, con una condición que hay
que decir clara en el README y en la propia pantalla: **el motor no se
despliega**. Es onnxruntime con CoreML, `rtmlib`, OpenCV y ffmpeg, con pesos
de cientos de MB, y tarda 76 s en procesar un clip de 17,8 s (informe del 11).
Nada de eso entra en una función serverless. Lo que se despliega es el visor
con resultados **ya calculados** en la Mac.

El peso es el problema a resolver, no un detalle. Un trabajo de exploración
de `vid1` pesa **424 MB**: `overlay.mp4` 245 MB, `original.mp4` 93 MB y
cuatro PNG de 18 MB cada uno. Nada de eso puede ir a un repo ni a un
deployment. Hace falta un exportador que produzca la versión web.

Ese exportador resuelve de paso un pedido pendiente de Hernán: **recortar al
sujeto y ampliarlo**. El sujeto ocupa 1104 px de 3840 en `vid1` (informe del
11): recortando al bbox con margen y reescalando, el golfista pasa a ocupar
casi todo el cuadro, y el archivo pesa una fracción.

Leer: `web/next.config.ts`, `web/src/lib/api.ts`, `web/src/app/page.tsx`,
`service/exploracion.py` (la forma de un trabajo y su lista blanca),
`kinelab/explore.py` (qué archivos escribe cada trabajo; **no lo modifiques**),
`CONTEXTO.md` §Sistemas de coordenadas (invariante: toda serie lleva su marco
de referencia), el informe del 11 (bbox y pesos), `README.md`, `.gitignore`.

## Encargo

### 1 · El repo en GitHub, privado

`gh` ya está autenticado como `hernandiazz9`. Creá el repositorio **privado**
`kinelab` y subí `main`. Privado, no público, por tres cosas que hoy están
commiteadas: los informes llevan rutas de la máquina de Hernán, su nombre y
su correo en los commits, y el informe del 11 incluye las **coordenadas GPS**
donde se filmó (`location` del `udta` de Samsung). Verificá si hay algo más
de esa clase y listalo en el informe; no borres nada, sólo reportalo. Si algún
día se hace público, esa lista es lo que hay que revisar antes.

### 2 · El exportador de demo

`kinelab/tools/exportar_demo.py`, nuevo:

```
python -m kinelab.tools.exportar_demo TRABAJO --out web/public/demo [--recorte sujeto|completo] [--alto 1080] [--tramo auto|A-B]
```

De un trabajo de `data/exploracion/`, escribe en `web/public/demo/<id>/`:

- El video **sin los palitos quemados**: el `original` recortado al tramo de
  la repetición con margen (por defecto ~1 s antes del address y ~1 s después
  del `follow_end`), recortado al bbox del sujeto con margen si
  `--recorte sujeto`, reescalado a `--alto`, H.264 con GOP corto para que el
  cuadro a cuadro siga andando. Objetivo: **menos de 15 MB por trabajo**.
- `transformacion.json`: el recorte y la escala aplicados, como una
  transformación afín explícita (`offset_x`, `offset_y`, `escala`, tamaño de
  origen y de destino) más el offset de cuadros del tramo. **Los keypoints no
  se reescriben**: se guarda cómo pasar de las coordenadas del `pose.npz` a
  las del video exportado, y el front aplica la transformación al dibujar.
  Declarado dentro del archivo, no en un comentario.
- Los datos: `datos-eventos.json` y `analysis.json` tal cual;
  `datos-por-cuadro.csv` recortado al tramo; la pose en JSON para el visor
  (si el 21 todavía no definió ese formato, elegí uno simple y decilo);
  `pose3d.json` si el trabajo lo tiene (ejemplos de mocap, encargo 19).
- Las fotos por evento en **JPEG** al mismo alto, no PNG de 18 MB.
- `web/public/demo/index.json`: la lista de trabajos exportados con su
  etiqueta, origen, fecha, fps, procedencia del fps y los avisos, para que la
  pantalla los liste igual que hoy.

Con tests: el exportador sobre un trabajo sintético produce todos los
archivos; la transformación afín aplicada a un keypoint conocido cae donde
debe; y el recorte no deja al sujeto fuera del cuadro en ningún cuadro del
tramo.

### 3 · El modo demo del front

- Una variable `NEXT_PUBLIC_KINELAB_MODO`: en `local` (el default de hoy) el
  front habla con el backend por `/api/*` como ahora; en `demo` lee de
  `/demo/index.json` y de `/demo/<id>/`, **sin backend**, y esconde el
  formulario de subir video con una línea que explica por qué: el motor corre
  en la Mac del entrenador, esto es un visor de resultados.
- La lectura se decide en **un solo lugar** de `web/src/lib/api.ts`, no
  repartida por los componentes.
- En modo demo, `output: "export"` en `next.config.ts` (los rewrites del modo
  local no se tocan), y `robots: noindex` en el layout: el enlace es para
  mostrar, no para que lo indexe un buscador.
- El reproductor aplica `transformacion.json` al dibujar sobre el video
  exportado. Si el 21 ya cerró y el dibujo va por canvas, es una
  multiplicación más; si no, usá el `overlay` exportado y anotá que queda
  pendiente.
- Exportá los dos ejemplos de mocap y `vid1`. Que el `README.md` diga cómo
  regenerar la demo con un comando, y qué es y qué no es lo que se despliega.

### 4 · Dejarlo listo para Vercel

`vercel` no está instalado y su login es interactivo: **no lo instales ni
intentes desplegar**. Dejá el build estático funcionando
(`cd web && NEXT_PUBLIC_KINELAB_MODO=demo pnpm build` produce `web/out/`) y
escribí en el informe los pasos exactos para Hernán en vercel.com: importar
el repo, el directorio raíz `web`, la variable de entorno, y el comando de
build. Si hace falta un `vercel.json`, agregalo.

NO: no desplegar nada (el paso público lo da Hernán); no hacer público el
repo; no tocar `kinelab/explore.py`, `kinelab/events/`, `sports/`,
`service/app.py`, `truth/`; no commitear videos de más de 15 MB; no agregar
dependencias de JS; no abrir el navegador.

## Cómo se prueba

- `.venv/bin/pytest -q` en verde con los tests del exportador.
- `cd web && pnpm lint` y los **dos** builds: el local de siempre y el
  estático de demo, los dos limpios.
- El tamaño final de `web/public/demo/` en el informe, archivo por archivo, y
  el peso total del repo después del commit.
- Servir `web/out/` con un servidor estático cualquiera y verificar **por
  `curl`** que `index.json`, los JSON y el video responden (el navegador no
  se abre).
- Para Hernán: la URL del repo, los pasos de Vercel, y qué va a ver.

## En paralelo

El 19 toca `web/src/app/page.tsx` y `web/src/components/Visor3D.tsx`; el 16
toca `web/src/lib/etiquetas.ts` y `TablaEventos.tsx`; el 20 mide y quizá toca
`explore.py`. **El paso 1 y el paso 2 no chocan con nadie: hacelos primero.**
Para el paso 3 esperá a que el 19 haya cerrado; si sigue abierto, dejá el
modo demo escrito en `api.ts` y `next.config.ts` (que nadie más toca) y el
punto de entrada en `page.tsx` para el final.
