# 25 — Publicar un trabajo a internet desde la pantalla, y despublicarlo

Para correr: `/encargo 25` en una sesión nueva. Leé antes los informes del
22 (el exportador y el modo demo) y del 08 (la lista de trabajos) en
`docs/informes/`.

## Contexto

Hoy el ciclo de publicar es a mano y en cuatro pasos: correr
`kinelab.tools.exportar_demo`, construir el estático, commitear los 15 MB por
trabajo y desplegar. Hernán quiere subir un video al análisis local y, si el
resultado le sirve, publicarlo con un clic para mostrarlo por link.

Dos cosas que el diseño tiene que respetar:

- **Publicar es deliberado, uno por uno.** Subir un video a la pantalla local
  no lo publica. El motor corre en la Mac del entrenador y los videos son de
  personas: que un trabajo salga a internet tiene que ser un acto explícito,
  reversible, y visible en la lista.
- **Los datos publicados no van a git.** Hoy `web/public/demo/` está
  commiteado (20 MB). Un entrenador que publique veinte swings metería 300 MB
  en la historia del repo, que no se borra nunca. El sitio se despliega desde
  el disco local con el CLI de Vercel, que ya está autenticado en esta Mac;
  en git queda el **código** y el **registro de qué está publicado**, no los
  videos.

El sitio ya está online en
`https://kinelab-qnm5fa60a-hernandiazz9s-projects.vercel.app` (proyecto
`kinelab` del team `hernandiazz9s-projects`, sin protección, con `noindex`).

Leer: `kinelab/tools/exportar_demo.py` (**ojo**: reescribe `index.json` con
sólo los trabajos que recibe; publicar uno nuevo no puede borrar del índice a
los que ya estaban, que es el bug que hay que evitar),
`service/exploracion.py` y `service/app.py`, `web/src/components/
ListaTrabajos.tsx`, `web/src/lib/api.ts`, `web/next.config.ts`, `.gitignore`,
`README.md` §La demo estática.

## Encargo

1. **`kinelab/tools/publicar.py`**, nuevo:
   ```
   python -m kinelab.tools.publicar TRABAJO [--quitar] [--solo-construir]
   ```
   - Exporta ese trabajo con el exportador que ya existe, **sumándolo** a los
     que ya estaban publicados en vez de reemplazarlos: el índice se arma del
     conjunto en disco, no del argumento.
   - Construye el estático (`NEXT_PUBLIC_KINELAB_MODO=demo`) y despliega a
     producción con el CLI de Vercel. Si el token expiró, un mensaje que diga
     qué correr, no un stacktrace.
   - `--quitar` hace lo inverso: saca el trabajo de `web/public/demo/`,
     reconstruye y vuelve a desplegar. Despublicar tiene que ser tan fácil
     como publicar.
   - `--solo-construir` deja todo listo sin desplegar, para poder probarlo sin
     tocar internet (y es lo que van a usar los tests).
   - Mantiene `data/publicados.json`: qué trabajos están publicados, cuándo,
     con qué URL. Ese archivo **sí** va a git: es el registro de qué se
     mandó afuera.
2. **`web/public/demo/` sale de git.** Agregalo a `.gitignore` y sacá del
   índice lo que hoy está commiteado (`git rm -r --cached`, sin borrar del
   disco). Decí en el informe que los 20 MB ya commiteados siguen en la
   historia y que eso no se deshace sin reescribirla, que no vale la pena.
3. **En el backend**: `POST /api/datos/{id}/publicar` y
   `DELETE /api/datos/{id}/publicar`, que corren el comando en un hilo y
   devuelven estado y progreso como ya hace la cola de exploración (exportar
   y desplegar tarda; la pantalla no puede quedarse colgada). `GET /api/datos`
   suma `publicado` y su URL en cada fila.
4. **En la pantalla**: en cada trabajo de la lista, un botón **«publicar»**
   que pide confirmación diciendo con todas las letras qué implica —el video y
   sus datos quedan accesibles para cualquiera que tenga el enlace—, y que
   mientras corre muestra en qué paso va. Publicado, la fila lo indica y
   ofrece **copiar el enlace** y **quitar de internet**. Nada de publicar al
   subir, ni por defecto, ni en lote.
5. `README.md`: el ciclo en cuatro líneas, y que lo publicado no está en git.

NO: no publicar nada durante la sesión (el deploy real lo dispara Hernán
desde la pantalla, o vos con `--solo-construir` que no toca internet); no
tocar `kinelab/explore.py`, `kinelab/events/`, `sports/`, `truth/`; no
guardar el token de Vercel en el repo ni imprimirlo; no agregar dependencias.

## Cómo se prueba

- Tests del comando con `--solo-construir` sobre trabajos de prueba: publicar
  uno **no saca del índice** a los que ya estaban (el bug del punto 1, con su
  test); `--quitar` lo saca y deja a los demás; `publicados.json` queda
  consistente; un id inexistente falla con mensaje y sin dejar basura.
- Tests del endpoint en `tests/test_service.py` con el comando simulado: la
  publicación corre en un hilo, la fila cambia de estado, el 404 del id que no
  existe.
- `.venv/bin/pytest -q` en verde. `cd web && pnpm lint` y los dos builds
  limpios.
- El estático construido servido localmente y verificado **por `curl`**: el
  índice tiene los tres de ahora más el de prueba.
- Para Hernán: los pasos exactos, incluido cuánto tarda y cómo despublicar.

## En paralelo

El 21 (visor desde datos) toca `service/app.py`, `Reproductor.tsx` y
`api.ts`: **no lo lances hasta que este cierre**, o avisá. El 16 toca
`kinelab/` y el contrato; el 18 `kinelab/events/`; el 24 `capture-paths.yaml`
y `data/incoming/`. Vos: `kinelab/tools/publicar.py`, `exportar_demo.py`,
`service/app.py`, `service/exploracion.py`, `ListaTrabajos.tsx`, `api.ts`,
`.gitignore`, `README.md`, `data/publicados.json`.
