# publicar-un-trabajo — 2026-09-15

Encargo: que un trabajo se pueda publicar a internet con un clic desde la
pantalla y despublicar igual de fácil; que publicar uno no borre del índice a los
que ya estaban; y que los datos publicados dejen de estar en git.

## Hecho

- **`kinelab/tools/publicar.py`**: `python -m kinelab.tools.publicar TRABAJO
  [--quitar] [--solo-construir]`. Cuatro pasos: exporta ese trabajo **sumándolo**
  a los que ya estaban, anota en `data/publicados.json`, construye el estático
  (`NEXT_PUBLIC_KINELAB_MODO=demo pnpm build`) y despliega a producción con el
  CLI de Vercel desde el disco. `--quitar` hace lo inverso; `--solo-construir`
  para antes del deploy y no toca internet.
- **Lo que se sube es un árbol armado acá**, no el repo: `web/.vercel/output/`
  con la Build Output API v3 (`static/` + `config.json`) y
  `vercel deploy --prebuilt --prod`. El `noindex` va en `config.json`: con
  `--prebuilt`, `web/vercel.json` no se aplica. Si el sitio se construyera del
  repo, los datos tendrían que estar **en** el repo, que es lo que esto evita.
- **`web/public/demo/` salió del índice de git** (`git rm -r --cached`, 38
  archivos, 20,4 MB) y entró a `.gitignore`. Sigue en disco. Lo que va a git es
  `data/publicados.json`: qué se mandó afuera, desde cuándo, con qué enlace, y
  qué se dio de baja y cuándo.
- **Backend** (`service/publicacion.py`, nuevo, + `service/app.py`):
  `POST /api/datos/{id}/publicar` y su `DELETE`, en un hilo, 202 con el paso;
  `GET /api/publicacion` con lo publicado y lo que corre; `publicado`,
  `publicado_url` y `publicado_en` en cada fila de `GET /api/datos`. Uno por vez:
  el segundo pedido es 409.
- **Pantalla** (`ListaTrabajos.tsx`): botón «publicar» por fila con confirmación
  de texto completo, el paso mientras corre, y publicado: etiqueta, enlace,
  «copiar enlace» y «quitar de internet». Nada al subir, ni por defecto, ni en
  lote. En modo demo no aparece ninguna acción.
- `README.md` §Publicar un trabajo: el ciclo en cuatro líneas y que lo publicado
  no está en git.
- 25 tests nuevos (19 del comando, 6 de los endpoints) y `eslint.config.mjs` con
  `.vercel/**` ignorado.

## Probado

### 1 · El ciclo, sobre trabajos reales, con `--solo-construir`

| | |
|---|---|
| publicar `17ed40a4…` (`cortado.mp4`) | **3,60 MB**, 12 archivos, **14,4 s** |
| el índice después | **4**: los tres que ya estaban **+ el nuevo** |
| `--quitar` sobre ése | **10,6 s**, el índice vuelve a **3** |
| el `video.mp4` del quitado, por `curl` | **404** |
| el `video.mp4` de `vid1`, por `curl` | **200**, 6.422.370 B |
| el registro | lo pasó a `quitados` con su fecha y su razón |

**La verificación que importa es la primera fila de la tabla**: publicar uno
nuevo dejó a los tres anteriores en el índice y en disco.

### 2 · El estático, por `curl` (sin abrir el navegador)

`web/.vercel/output/static/` servido con `python3 -m http.server`:

`/` 200 text/html 6604 B · `/demo/index.json` 200 application/json 4614 B ·
`trabajo.json` 24.541 B · `video.mp4` 200 video/mp4 1.328.950 B ·
`transformacion.json` 1235 B · `pose3d.json` 375.327 B · un archivo que no
existe, **404**. El `index.json` servido lista los cuatro trabajos con su
etiqueta, fps y procedencia (`sin_verificar` en los cuatro).

### 3 · El registro quedó al día con lo que de verdad está publicado

Los tres que hoy están en el sitio se re-exportaron y se anotaron:

| trabajo | peso | archivos |
|---|---|---|
| `72d91d03…` (`vid1.mp4`) | 14,89 MB | 13 |
| `ejemplo-cmu-64_01-face_on` | 2,71 MB | 12 |
| `ejemplo-cmu-64_01-down_the_line` | 2,53 MB | 12 |

**22 MB en disco, 0 en git.** Y de paso los dos de mocap pasaron a `pose3d.json`
**1.1.0**, con la capa de ángulos: era lo que el 23 dejó pendiente.

### 4 · El backend de verdad, con `curl` (sin publicar nada)

`.venv/bin/python -m service` en el 8768: `GET /api/publicacion` devuelve los
tres con su enlace y `corriendo: null`; `GET /api/datos` marca `publicado=true`
en esos tres y `false` en los otros quince. Errores: `POST` de un id que no
existe → **404** «No hay ningún trabajo de exploración con id…»; `DELETE` de uno
que no está publicado → **404** «El trabajo … no está publicado»;
`..%2F..%2Fx` → **404**.

### 5 · Suites y mutación

- Motor **320 en verde** (295 → 320, 52 s). Arnés **49** (12,3 s, no se tocó).
- `pnpm lint` limpio y **los dos builds** limpios.
- **Mutación manual: 13 de 13.** Entre las que se cazan: el índice armado del
  argumento en vez del disco (el bug del encargo), `--quitar` borrando todo,
  `--solo-construir` desplegando igual, el `noindex` fuera de `config.json`, un
  build roto que no frena el deploy, dos publicaciones a la vez, la fila
  diciendo `publicado` siempre, publicar un trabajo a medias. **Una se
  escapaba** —reescribir `publicado_en` al republicar: las dos fechas caían en el
  mismo segundo y el test pasaba igual— y el test se rehizo con una fecha vieja
  escrita a mano.

### 6 · El bug que el prompt anticipaba no estaba

`exportar_demo.escribir_indice` ya recorría la carpeta de salida en vez de la
lista de argumentos (viene así del 22). El test que lo cuida se escribió igual,
porque es la clase de cosa que vuelve sola: si alguna vez se arma del argumento,
el trabajo anterior queda **en disco pero invisible**, que es la peor de las dos
fallas — el dato sigue afuera y el registro dice otra cosa.

## Queda abierto

- **No se desplegó nada.** Todo corrió con `--solo-construir`. El paso 4
  (`vercel link` + `vercel deploy --prebuilt --prod`) está escrito y testeado con
  el ejecutor inyectado, pero **nunca corrió contra Vercel**. El primer deploy
  real es el de Hernán, y es donde puede aparecer lo que no se puede probar en
  seco: que el proyecto se llame `kinelab` en el scope `hernandiazz9s-projects`
  (las dos constantes están arriba de `kinelab/tools/publicar.py`), y que un
  `.vercel/output` de sólo `static/` + `config.json` sirva el sitio como lo
  sirve hoy el build de Vercel.
- **La `SITIO` anotada es la URL de deploy del prompt**
  (`kinelab-qnm5fa60a-…`), no el alias estable de producción. Si Vercel da otro,
  se cambia con `--sitio` / `KINELAB_SITIO`.
- **20,4 MB siguen en la historia de git.** `git rm --cached` los saca del índice
  y del árbol futuro, pero los blobs de los commits `c7997da` y siguientes están
  ahí para siempre. Sacarlos pide reescribir la historia (`filter-repo`) y
  forzar el push; **no vale la pena**: el repo es privado, son 20 MB, y la lista
  de siete cosas a resolver antes de hacerlo público (informe del 22) ya incluye
  reescribir la historia por otras dos razones. Si alguna vez se hace esa
  limpieza, ésta entra en el mismo pasaje.
- **El deploy no informa progreso**: el paso 4 dura lo que dure `vercel deploy` y
  la pantalla no se mueve mientras tanto.
- **El sitio entero se reconstruye y se sube en cada publicación.** Con tres
  trabajos, 22 MB y ~15 s de build. Con veinte, no está medido.
- **Quitar de internet no borra el trabajo local**, a propósito. Borrar
  `data/exploracion/<id>/` sigue siendo `rm -rf`.
- **La pantalla no se abrió** (regla de trabajo). Lo que más puede fallar sin
  verla: los botones de la derecha de cada fila en una ventana angosta —la fila
  pasó de ser un `<button>` entero a un `<div>` con el botón principal y las
  acciones al lado, porque un `<button>` adentro de otro no es HTML válido—, y
  `navigator.clipboard`, que existe en `http://localhost` pero no en un `http://`
  de red (si falta, el enlace queda igual escrito abajo de la fila para copiarlo
  a mano).

## Para que pruebe Hernán

### A · Levantar los dos procesos

```bash
.venv/bin/python -m service
```

```bash
cd web && pnpm dev
```

### B · Publicar, en la pantalla (http://localhost:3000)

1. En **«Trabajos anteriores y ejemplos»**, tres filas tienen que tener la
   etiqueta azul **«publicado»** con su enlace debajo: `vid1.mp4` y los dos
   `cmu-64_01`. El resto, no.
2. En una fila publicada: **«copiar enlace»** (tiene que decir «copiado») y
   **«quitar de internet»**.
3. En una fila cualquiera **no** publicada —por ejemplo un `cortado.mp4`—, botón
   **«publicar»**. Al apretarlo **no publica**: abre el recuadro ámbar con el
   texto entero de qué implica. Ahí están los dos botones.
4. **«Sí, publicar a internet»** arranca de verdad: la fila pasa a mostrar
   «publicando · paso N de 4 · …» y los botones de las demás filas se
   deshabilitan (va uno por vez). **Tarda alrededor de un minuto** y el paso 4
   —el deploy— es el que más dura sin moverse.
5. Cuando termina, la fila queda con «publicado» y su enlace. **Abrilo en otra
   pestaña**: tiene que abrirse el sitio con ese trabajo ya elegido.
6. **«quitar de internet»** en esa misma fila, confirmando: otro minuto, y el
   enlace deja de funcionar (404). Las otras tres siguen estando.

**Si el paso 4 falla con «El CLI de Vercel no está autenticado»**, corré
`npx vercel login` y volvé a apretar publicar. Si falla con algo de `vercel
link`, vinculá a mano:

```bash
cd web && npx vercel link --project kinelab --scope hernandiazz9s-projects
```

### C · Lo mismo sin pantalla, y sin tocar internet

```bash
.venv/bin/python -m kinelab.tools.publicar <id> --solo-construir
```

y después, para mirarlo antes de mandarlo:

```bash
cd web/out && python3 -m http.server 8812
```

### D · Lo que hay que mirar una vez

`git status` no tiene que mostrar nada de `web/public/demo/` nunca más, y
`data/publicados.json` sí, cada vez que publiques o quites algo. Ése es el
archivo que dice qué está afuera.

## Preguntas para el orquestador

1. **¿El alias de producción del sitio es el de `SITIO`?** Hoy está la URL de
   deploy que traía el prompt. Si Vercel tiene un alias estable
   (`kinelab-….vercel.app` sin el hash), conviene poner ése: es el enlace que
   queda escrito en el registro y el que se le pasa a alguien.
2. **¿`cortado.mp4` (`17ed40a4…`) se publica o no?** Lo usé para probar el ciclo
   y después lo quité, así que el sitio queda con los tres de siempre. Publicarlo
   es un clic.
3. **Los 20,4 MB en la historia de git**: ¿se limpian alguna vez? Va junto con
   los otros dos motivos para reescribir la historia del informe del 22 (el GPS
   del lugar de filmación y el correo en 79 commits).
4. **¿El sitio se reconstruye entero en cada publicación, o llega un momento en
   que conviene un índice incremental?** Hoy son 22 MB y ~15 s. Con veinte
   swings serían ~150 MB por deploy.
5. **`web/eslint.config.mjs`** ganó una línea (`.vercel/**`). Es de `web/` y no
   está asignado a ningún encargo abierto; lo digo por si alguien lo esperaba
   intacto.
6. **El commit `1b0a640` del encargo 24 se llevó las 38 eliminaciones de
   `web/public/demo/` que esta sesión tenía en el índice.** El resultado es el
   correcto —los datos publicados quedaron fuera de git—, pero la baja está en el
   commit equivocado, con el mensaje del 24. No lo corregí: reescribir el commit
   de una sesión que puede seguir corriendo es peor que la molestia. Si querés
   que la historia diga de dónde salió, hay que reescribirla; si no, esto queda
   como la anotación.
