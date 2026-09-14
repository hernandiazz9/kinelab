# 08 — Lista de trabajos anteriores y ejemplos en la pantalla de exploración

Para correr: `/encargo 08` en una sesión nueva. Puede correr ya, en paralelo
con el 04, el 05 y el 06: ninguno toca `web/` ni `service/`.

## Contexto

Hoy la pantalla de exploración abre sólo el último trabajo (guardado en
`localStorage`) o uno recién subido. Hernán quiere abrir trabajos anteriores
sin volver a subir el video, y abrir ejemplos que no vienen de una subida:
el encargo 07 va a dejar swings de mocap real como trabajos ya listos en
`data/exploracion/ejemplo-cmu-<trial>-<vista>/` con `origen: ejemplo` en su
`trabajo.json`. Esta pantalla los tiene que listar y abrir igual que a los
demás. Es una pantalla de mirar datos: sin atletas, sesiones ni gate.

Leer: `service/exploracion.py` (la cola, `trabajo.json`, qué hay en
`data/exploracion/<id>/`), `service/app.py` (los endpoints `/api/datos`),
`tests/test_service.py`, `web/src/app/page.tsx`, `web/src/lib/api.ts`,
`web/src/components/Subida.tsx`, `README.md` §Interfaz de exploración.

## Qué existe ya

- `PUT /api/datos?filename=&altura_m=` → 202 con id; `GET /api/datos/{id}`
  con estado, progreso y el resumen; `GET /api/datos/{id}/archivos/{nombre}`
  con lista blanca. Un trabajo por vez, `trabajo.json` sobrevive al reinicio.
- La página: subida con progreso, sondeo cada 0,5 s, el último trabajo
  vuelve al recargar.

## Encargo

1. `GET /api/datos`: lista de trabajos, del más nuevo al más viejo: `id`,
   nombre del archivo original, fecha, estado, `origen` (`subida` |
   `ejemplo`), altura declarada, fps y eventos si está listo. Sale de los
   `trabajo.json` en disco, no de memoria: los trabajos de sesiones
   anteriores y las carpetas de ejemplo que otro proceso deje (el 07) tienen
   que aparecer. Un `trabajo.json` sin `origen` es `subida`.
2. En la página, arriba o al costado de "Subir video", una lista corta
   "Trabajos anteriores y ejemplos": nombre, fecha, origen, estado; clic →
   se abre ese trabajo como si acabara de terminar (mismo reproductor, mismas
   tablas). Los ejemplos van rotulados como tal en la lista y en el
   resultado ("ejemplo · mocap CMU · no es video", con el texto que traiga
   `trabajo.json`).
3. `?trabajo=<id>` en la URL abre ese trabajo al cargar, y al elegir uno de
   la lista la URL se actualiza; así se puede compartir un enlace local.
4. Un trabajo borrado del disco desaparece de la lista sin romper nada;
   si el `localStorage` apunta a uno que ya no existe, la página no se cuelga.

NO: no borrar trabajos desde la pantalla (eso es la cola con cancelación,
más adelante); no agregar atletas, sesiones ni gate; no rediseñar la página;
no tocar el motor.

## Cómo se prueba

- `tests/test_service.py`: la lista con cero, uno y varios trabajos; una
  carpeta de ejemplo con `origen: ejemplo` aparece; un `trabajo.json` roto o
  una carpeta sin él se salta y se registra.
- `.venv/bin/pytest -q` en verde. `cd web && pnpm lint && pnpm build` limpios.
- Por el proxy con `curl`: `GET /api/datos` con dos trabajos reales (subí
  `~/Desktop/cortado.mp4` dos veces) y una carpeta de ejemplo armada a mano
  para el test (un `trabajo.json` listo con `origen: ejemplo` y los archivos
  copiados de un trabajo real).
- Para Hernán: la lista en la página, abrir un trabajo viejo, abrir el
  ejemplo armado a mano, recargar con `?trabajo=` en la URL.

## En paralelo

El 04 y el 06 tocan `kinelab/ingest/`, `kinelab/contract/`,
`kinelab/explore.py`, `CAPTURA.md`, `CONTRATO.md`, `DECISIONES.md`; el 05
toca `kinelab/tools/interpolar.py`. No toques nada de eso.
