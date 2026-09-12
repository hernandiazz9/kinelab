# Prompt: interfaz de exploración (subir un video → palitos + toda la data)

Pegar entero en una sesión nueva de Claude Code abierta en `/Users/heralc/Desktop/HDDev/kinelab`.

---

Estás en `/Users/heralc/Desktop/HDDev/kinelab`, un motor de medición del movimiento humano a partir de video de celular (golf primero). Antes de escribir una línea, leé completos y en este orden: `AGENTS.md`, `CONTEXTO.md`, `DECISIONES.md`, `ESPECIFICACION.md`, `CONTRATO.md`, `CAPTURA.md`, `HERENCIA.md` y por último `ESTADO.md`, que dice dónde quedó todo. Después leé `kinelab/explore.py` y `service/app.py`: son las dos piezas sobre las que vas a construir.

**Reglas de trabajo con Hernán (no negociables).** Vos creás; él prueba. Escribí el código con tests mínimos (los justos para que el backend no esté roto), no abras el navegador, no lances subagentes ni workflows, no hagas pruebas exhaustivas: gastan el contexto y no lo dejan seguir. Al terminar cada bloque, commit con mensaje en español que diga qué cambió y por qué, y una lista corta de "probá esto, esto y esto" con los comandos. Prosa en español, identificadores en inglés. Si algo de los documentos no se puede cumplir, avisá y anotalo en `ESTADO.md`; no rodees.

**Lo que ya existe y funciona.** `python -m kinelab datos VIDEO.mp4 --altura-m 1.75` (ver `kinelab/explore.py`) toma cualquier video de un swing, corre la pose (RTMPose-m, 26 puntos Halpe26, CoreML) y deja en `<video>.kinelab/`: `overlay.mp4` (el video con el esqueleto, los ángulos de codos y rodillas y los eventos dibujados), `evento-address.png`, `evento-top.png`, `evento-impact.png`, `datos-por-cuadro.csv` (122 columnas por cuadro: posición y confianza de los 26 puntos, ángulos de codo/rodilla/cadera/hombro/tronco, líneas de hombros y caderas, altura de manos en %, desplazamientos de pelvis/tórax/cabeza/manos respecto del address en % y en cm, velocidades lineales y angulares), `datos-eventos.json` (todo eso en cada evento, diferencias contra el address, duraciones, picos) y `analysis.json`. Tarda ~10 s por un clip de 3 s. Corre sin gate y sin juicio a propósito: es el modo de mirar datos.

También existe `service/` (FastAPI local, `python -m service`, puerto 8765) con una página HTML del gate de ingesta que Hernán encontró confusa y **no quiere usar**. FastAPI sigue siendo el backend (está en el stack, ADR-015); la página se reemplaza.

**Lo que hay que construir: UNA pantalla, nada más.**

1. Un botón "Subir video" (y un campo opcional de altura en metros). Al subir, la app manda el archivo al backend, muestra el progreso ("subiendo", "detectando la pose", "calculando"), y cuando termina muestra el resultado. Nada de atletas, gestos, vistas, caminos de captura ni gate en esta pantalla.
2. Arriba, el video con los palitos: por ahora se reproduce `overlay.mp4` tal como sale del motor. Reproductor con pausa, arrastre por la línea de tiempo, cámara lenta y, si la librería lo da, ir cuadro a cuadro hacia atrás y adelante. Debajo del reproductor, las tres fotos por evento (address, top, impacto).
3. Abajo, toda la data recolectada: primero un cuadro como este, con una fila por variable y una columna por evento (address, top, impacto), en unidades legibles:

   | | address | top | impacto |
   |---|---|---|---|
   | codo izquierdo / derecho | 168° / 171° | 127° / 149° | 162° / 177° |
   | rodilla izquierda / derecha | … | … | … |
   | línea de hombros, línea de caderas, tronco | … | … | … |
   | altura de manos (%) | … | … | … |
   | pelvis / tórax / cabeza vs address (cm) | … | … | … |
   | velocidad de manos (cm/s) | … | … | … |

   más las duraciones (backswing, downswing, tempo), los picos (velocidad de manos, rotación aparente de hombros y caderas), y después TODA la tabla por cuadro (`datos-por-cuadro.csv`) navegable, con descarga del CSV y del JSON. Todo lo que el motor produce se muestra; no se esconde nada ni se resume en un puntaje (ADR-012: sin puntaje, sin veredicto).
4. Más nada por ahora. Sin login, sin lista de sesiones, sin edición de eventos, sin dibujar desde datos todavía.

**Reproductor: investigá antes de elegir.** Buscá una librería de reproductor de video para React/Next que dé, con el menor código posible: pausa, arrastre fino, velocidad 0,1×–1×, y cuadro a cuadro hacia atrás y adelante (el fps real está en `datos-eventos.json.fps_archivo`). Candidatas a evaluar: Video.js, Plyr, Vidstack, react-player, y el enfoque propio con `<video>` + `requestVideoFrameCallback` (que es el que ADR-014 fija para el visor definitivo). Para cada una anotá: licencia (sólo MIT/Apache/BSD; ADR-010), si permite frame-stepping real o sólo seek a `(n + 0,5) / fps`, si funciona con H.264 en Chrome, y cuánto pesa. Elegí una, explicá por qué en dos líneas, y anotá en `ESTADO.md` que reproducir `overlay.mp4` pre-renderizado es un paso provisorio que contradice la invariante 10 de `CONTEXTO.md` (nunca video anotado como única vista): el visor definitivo dibuja el esqueleto desde `pose.npz` sobre el video original, y eso viene después.

**Stack y estructura.** Frontend en `web/` con Next.js última estable (ADR-015 dice 16; si Hernán habla de "Next 15" es lo mismo: la última), React 19, Tailwind 4, pnpm, Node 22. App Router, una sola página. El backend es `service/app.py`: agregale `PUT /api/datos` (el archivo viaja como cuerpo crudo con `?filename=`, como ya hace `/api/ingest`) que arranca `kinelab.explore.explore` en un hilo y devuelve un id de trabajo; `GET /api/datos/{id}` con el estado y, cuando termina, el resumen de `datos-eventos.json`; y `GET /api/datos/{id}/archivos/{nombre}` para servir `overlay.mp4`, las fotos, el CSV y el JSON. El video necesita respuestas con `Range` (206) para poder arrastrar: verificá si `FileResponse` de la versión instalada de Starlette lo hace sola; si no, portá el patrón de `padel-coach` que `HERENCIA.md` señala (`web/src/app/api/media/[...path]/route.ts:58-127`). Los trabajos van a `data/exploracion/<id>/`; agregá esa carpeta a `.gitignore`. Nada de dependencias Python nuevas fuera de ADR-015. En `web/`, sólo la librería del reproductor que elijas, con su licencia anotada.

**Cómo tiene que quedar para que Hernán lo pruebe.** Dos comandos, documentados en `README.md`: uno para el backend (`.venv/bin/python -m service`) y uno para el frontend (`cd web && pnpm dev`), con el proxy configurado para que el frontend hable con el 8765 sin CORS a mano. Un video de prueba real está en `~/Desktop/cortado.mp4` (3 s, 30 fps): no lo pruebes vos en el navegador; dejalo listo y decile qué esperar al abrir http://localhost:3000.

**Al cerrar:** commit, `ESTADO.md` actualizado (qué existe, qué falta, la desviación de la invariante 10), y la lista de qué probar.
