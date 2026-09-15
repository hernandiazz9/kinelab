# kinelab

Motor de medición del movimiento humano a partir de video de celular. Para un
entrenador, en su Mac, sin nube. Agnóstico al deporte; golf primero.

**Empezá por [`AGENTS.md`](AGENTS.md).** Dice qué leer, en qué orden, y cuáles
son las reglas de trabajo. Los seis documentos que enumera son la fuente de
verdad; `ESTADO.md` dice dónde quedó el trabajo.

```bash
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev,service]"
.venv/bin/pytest -q
```

## Interfaz de exploración (subir un video → palitos + toda la data)

Dos procesos, en dos terminales. La primera vez, en `web/`: `pnpm install`
(Node 22+, pnpm).

```bash
.venv/bin/python -m service          # backend FastAPI en http://127.0.0.1:8765
```

```bash
cd web && pnpm dev                   # frontend Next.js en http://localhost:3000
```

Abrir http://localhost:3000. Una pantalla: elegir el video, la altura del
atleta en metros (opcional: sin ella no hay centímetros), «Subir video». Se ve
el progreso (subiendo → cargando el modelo → detectando la pose → calculando →
dibujando) y al terminar:

- arriba, el video con los palitos en un reproductor con pausa, arrastre con
  un paso por cuadro, velocidad 0,1×–1×, cuadro a cuadro en las dos direcciones
  (flechas), zoom hasta 4× con la rueda o los botones y paneo arrastrando;
- debajo del reproductor, el instante estimado del impacto **entre dos
  cuadros** («entre el cuadro 44 y el 45 (0,44 ± 0,11)»), con un botón para ver
  esos dos cuadros lado a lado: entre uno y el otro no hay nada filmado;
- las fotos de address, top e impacto (clic: ese cuadro en el reproductor);
- toda la data por evento en tablas, duraciones, picos, diferencias contra el
  address, y la tabla completa por cuadro con filtro de columnas y descarga
  del CSV, del JSON y del video.

Debajo de «Subir video», la lista **«Trabajos anteriores y ejemplos»**: todo lo
que hay en `data/exploracion/`, del más nuevo al más viejo, con fecha, estado,
fps y los cuadros de cada evento. Un clic abre ese trabajo como si acabara de
terminar, sin volver a subir el video, y la URL pasa a `?trabajo=<id>`: ese
enlace, pegado en otra pestaña, abre el mismo trabajo. La lista sale de los
`trabajo.json` en disco, así que también aparecen los trabajos de sesiones
anteriores y los **ejemplos** que deje otro proceso — una carpeta con los
mismos archivos y un `trabajo.json` con `"origen": "ejemplo"` y su `etiqueta`,
que se muestra rotulada en la lista y sobre el resultado (ver el encabezado de
`service/exploracion.py`). Desde la pantalla no se borra nada: un trabajo se
borra con `rm -rf data/exploracion/<id>`, y desaparece de la lista solo.

El frontend habla con el backend por `/api/*` (proxy en `web/next.config.ts`),
así que no hace falta CORS. Los trabajos quedan en `data/exploracion/<id>/`
(ignorado por git); el último se vuelve a mostrar al recargar la página.

Lo mismo sin interfaz: `.venv/bin/python -m kinelab datos VIDEO.mp4 --altura-m 1.75`.

## La demo estática (lo que se despliega, y lo que no)

**El motor no se despliega.** Son onnxruntime con CoreML, `rtmlib`, OpenCV y
ffmpeg, con pesos de cientos de MB, y tardan 76 s en procesar un clip de 17,8 s:
nada de eso entra en una función serverless. Lo que se puede publicar es **el
visor sobre resultados ya calculados** en la Mac del entrenador. En la demo no
se puede subir un video, y la pantalla lo dice con esas palabras.

Un trabajo de `data/exploracion/` pesa hasta 424 MB (`overlay.mp4` 245 MB,
`original.mp4` 93 MB, cuatro PNG de 18 MB). El exportador produce la versión
web: recorta al tramo del gesto, recorta al sujeto con margen, reescala, pasa
las fotos a JPEG, y **deja escrito cómo deshacer las tres cosas** en
`transformacion.json` — los keypoints **no** se reescriben (`CONTEXTO.md`
§Sistemas de coordenadas).

```bash
.venv/bin/python -m kinelab.tools.exportar_demo data/exploracion/<id> --out web/public/demo
```

Deja `web/public/demo/<id>/` y reescribe `web/public/demo/index.json` con todos
los que haya. Medido sobre `vid1`: **424 MB → 14,9 MB**, y el golfista pasa de
ocupar **29,0 %** del alto del cuadro a **56,0 %** (×1,93). Opciones:
`--recorte sujeto|completo`, `--alto`, `--tramo auto|A-B`, `--margen`, `--crf`.

### Publicar un trabajo, y despublicarlo

El ciclo entero es **un comando por trabajo**, y desde la pantalla es el botón
«publicar» de su fila, con su confirmación:

```bash
.venv/bin/python -m kinelab.tools.publicar <id>                    # exporta, construye y despliega
.venv/bin/python -m kinelab.tools.publicar <id> --quitar           # lo saca de internet
.venv/bin/python -m kinelab.tools.publicar <id> --solo-construir   # deja todo listo sin desplegar
```

Cuatro pasos: exporta ese trabajo **sumándolo** a los que ya estaban, anota la
fecha y el enlace en `data/publicados.json`, construye el estático y lo despliega
a producción con el CLI de Vercel desde el disco de esta Mac. Tarda ~1 min
(~15 s de export por clip corto, ~55 s con `vid1`, más el deploy).

**Lo publicado no está en git.** `web/public/demo/` está en `.gitignore`: un
entrenador que publique veinte swings metería 300 MB en una historia que no se
borra nunca. Lo que viaja con el repo es el código y **`data/publicados.json`**,
el registro de qué se mandó afuera, desde cuándo y con qué enlace. Publicar es
deliberado y uno por uno: subir un video a la pantalla local no publica nada.

El front tiene dos modos, con **una sola** decisión en `web/src/lib/api.ts`:

```bash
cd web && pnpm build                                  # local: habla con el backend por /api/*
cd web && NEXT_PUBLIC_KINELAB_MODO=demo pnpm build    # demo: sitio estático en web/out/
```

En demo no hay rewrites ni proxy (`output: "export"`), el formulario de subir se
reemplaza por la frase que explica por qué, y la página va con `noindex`: el
enlace es para mostrar, no para que lo indexe un buscador. En Vercel:
directorio raíz `web`, y `web/vercel.json` ya trae el `buildCommand` con la
variable, así que no hace falta configurarla a mano.

El modo exploración corre sin gate y sin MDC: son números descriptivos para
mirar, no para juzgar. Y reproducir el `overlay.mp4` ya dibujado es un paso
provisorio (contradice la invariante 10 de `CONTEXTO.md`); el visor definitivo
dibuja desde `pose.npz` sobre el video original.

Nombre provisorio. Cambiarlo es un `sed`.
