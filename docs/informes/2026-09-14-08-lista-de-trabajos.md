# lista-de-trabajos — 14 de septiembre de 2026

**Encargo:** que la pantalla de exploración liste los trabajos que ya están en
disco —los de sesiones anteriores y los ejemplos que deje otro proceso— y que
se pueda abrir cualquiera sin volver a subir el video, con `?trabajo=<id>` en
la URL.

**Hecho:**

- `cee7585` — backend. `GET /api/datos` devuelve una fila por trabajo, del más
  nuevo al más viejo: `id`, `video`, `creado`, `terminado`, `estado`, `origen`,
  `etiqueta`, `altura_m`, `vista`, `segundos`, `error` y, sólo si está listo,
  `fps_archivo`, `cuadros` y `eventos_frame`. Sin el resumen entero.
- **El disco manda:** `listar()` y `get()` releen los `trabajo.json` de
  `data/exploracion/` en cada llamada, así que aparecen los trabajos de
  sesiones anteriores y las carpetas que deje otro proceso sin reiniciar el
  servidor. Única excepción: el trabajo que está corriendo en este proceso, que
  sale de memoria porque lleva el progreso por cuadro.
- **El id es el nombre de la carpeta**, no el campo `id` del JSON: es lo que
  resuelve la URL. `JOB_ID` acepta ahora un slug además de los 32 hex, sin
  barras y sin empezar con punto.
- **La forma de un ejemplo, para el encargo 07** (documentada en el encabezado
  de `service/exploracion.py`): una carpeta más, con los mismos archivos y un
  `trabajo.json` con `"estado": "listo"`, `"origen": "ejemplo"` y `"etiqueta"`
  (el rótulo que muestra la pantalla). `estado` es lo único obligatorio; sin
  `origen` el trabajo es `subida`.
- `d5aebbc` — front. «Trabajos anteriores y ejemplos» debajo de «Subir video»
  (`web/src/components/ListaTrabajos.tsx`): nombre, fecha, vista, estado, fps,
  cuadros y los cuadros de cada evento; los ejemplos rotulados en la lista y
  arriba del resultado. Clic → se abre ese trabajo como si acabara de terminar.
  `?trabajo=<id>` lo abre al cargar y la URL se actualiza al elegir uno.
- Un trabajo borrado del disco desaparece de la lista, y su `GET` da 404 sin
  romper nada; el id que quedó en `localStorage` se olvida con un aviso de una
  línea. Un `trabajo.json` roto, o una carpeta sin él, se saltean y quedan en
  el log del servidor.
- No se borra nada desde la pantalla, por encargo.

**Probado:** backend de hoy en el 8765 y el `next dev` que ya corría en el
3000; todo por el proxy con `curl`, sin abrir el navegador.

| | |
|---|---|
| trabajos listados | 8: 5 de sesiones anteriores + 2 subidas nuevas de `cortado.mp4` + 1 ejemplo (quedan 7: una de las dos subidas se borró para probar el borrado) |
| orden | por `creado`, del más nuevo al más viejo |
| `cortado.mp4` en la fila | 29,999 fps · 76 cuadros · address 7 · top 39 · impacto 44 |
| `20260907_170638.mp4` (del 12/9) | 29,436 fps · 265 cuadros · address 111 · top 141 · impacto 147 · fin 219 |
| `GET /api/datos` | 2504 bytes · 3,0–3,3 ms en el backend · 4,4–5,3 ms por el proxy |
| ejemplo armado a mano | se abre por su slug: `origen: ejemplo`, su etiqueta, 8 archivos, `overlay.mp4` con 206 y PNG con 200 |
| trabajo borrado del disco | sale de la lista; su `GET` y el de sus archivos, 404 |
| ids inválidos | `..`, `..%2F..%2Fcapture-paths.yaml`, `.oculto`, `con/barra`, 65 caracteres → 404 |

Los dos trabajos del 12/9 sobre el original del S22 conservan `fps_archivo`
29,436, el **bruto**: se calcularon antes del encargo 04. Nada recalcula un
trabajo viejo, y está bien que sea así.

Suites: **239 en verde** en el motor (`tests/test_service.py` pasa de 41 a 47
casos), ~25 s, con el trabajo sin commitear del encargo 06 adentro.
`cd web && pnpm lint && pnpm build`, limpios.

**Queda abierto:**

- La pantalla **no se abrió en un navegador** (regla de trabajo). Sin verlo, lo
  que más puede fallar: el alto de la lista (`max-h-72` con scroll) con muchos
  trabajos, y que `?trabajo=` conviva bien con el router de Next al recargar.
- El ejemplo que hay hoy es **armado a mano y no es mocap**: una copia de
  `cortado.mp4` con su `trabajo.json` escrito aparte, para probar la lista. Su
  etiqueta lo dice con todas las letras. Lo reemplaza el encargo 07; se borra
  con `rm -rf data/exploracion/ejemplo-a-mano-cortado-face_on`.
- Sin paginado: se devuelven todos los trabajos (8 → 2,5 KB y 3 ms; con
  cientos habría que cortar).
- Un trabajo a medio correr de **otro** proceso se lista con su estado tal
  cual: sólo el arranque del propio servidor marca como `error` lo que quedó a
  medias, y no se escribe sobre el `trabajo.json` de otro.
- Se mató el backend viejo del 8765 (PID 16524, del 12/9, con código anterior a
  los encargos 02–06) para poder probar por el proxy: Next 16 no deja levantar
  un segundo `next dev` sobre el mismo directorio, así que había que usar el
  que ya corría en el 3000, y ése habla con el 8765. En su lugar quedó
  corriendo el backend de hoy; el `next dev` de Hernán no se tocó.

**Para que pruebe Hernán:** el backend de hoy y el `next dev` del 3000 ya están
corriendo; si hace falta levantarlos de nuevo:

```bash
.venv/bin/python -m service
```

```bash
cd web && pnpm dev
```

1. Recargar http://localhost:3000. Debajo de «Subir video» tiene que aparecer
   «Trabajos anteriores y ejemplos» con **7 trabajos**: arriba de todo el
   `ejemplo` (etiqueta verde: *ejemplo armado a mano… NO es mocap*), después un
   `cortado.mp4` de hoy, y abajo los del 12 y 13 de septiembre.
2. Clic en uno viejo: se abre con el reproductor, las fotos y las tablas, sin
   subir nada. En `cortado.mp4`: address 7, top 39, impacto 44. En
   `20260907_170638.mp4`: 111, 141, 147 y 219.
3. Mirar la barra de direcciones: tiene que decir `?trabajo=<id>`. Copiar ese
   enlace, abrirlo en otra pestaña: se abre el mismo trabajo.
4. Clic en el ejemplo: arriba del resultado, el rótulo verde con el texto de su
   `trabajo.json`.
5. Subir `~/Desktop/cortado.mp4` de nuevo: cuando termina, el nuevo aparece
   primero en la lista y queda resaltado.
6. Borrar uno a mano (`rm -rf data/exploracion/<id>`) y recargar: desaparece
   solo. Si era el que estaba abierto, la página avisa en una línea y vuelve al
   inicio en vez de colgarse.

**Preguntas para el orquestador:**

- La lista no tiene límite ni paginado, y `data/exploracion/` crece ~20 MB por
  clip de 3 s (las tres fotos PNG pesan 3,7 MB cada una). Borrar un trabajo hoy
  es `rm -rf`. ¿Entra la cancelación + borrado desde la pantalla como encargo
  propio, o primero conviene abaratar el trabajo (PNG → JPEG)?
- El ejemplo de mentira que quedó en disco se puede borrar cuando el 07 deje
  el de verdad. ¿Conviene que el 07 lo borre como parte de su trabajo, o lo
  hace Hernán?
