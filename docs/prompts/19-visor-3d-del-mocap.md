# 19 — El swing 3D medido, girable en la pantalla

Para correr: `/encargo 19` en una sesión nueva. Leé antes los informes del
07 (el mocap y el mapeo), el 13 (§1, por qué la ganancia muere) y el 09 (la
pantalla) en `docs/informes/`.

## Contexto

Hernán quiere ver un swing en 3D y girarlo en la pantalla. Se puede, con
**un solo** material: el mocap del sujeto 64 de CMU, que está medido con
marcadores ópticos y tiene posición 3D verdadera de cada articulación. Los
clips de celular **no**: una cámara no ve profundidad, y fabricarla es lo
que ADR-010 veta y el contrato pone en nivel 3. La pantalla tiene que decir
esa diferencia con todas las letras.

Además del valor de demostración, esto explica en dos segundos algo que hoy
sólo existe como tabla: **por qué cada métrica declara su vista**. Girando la
escena hasta `down_the_line`, la línea de caderas se pone de frente a la
cámara y su largo proyectado colapsa. El 13 lo midió: 3,6 px de largo y un
giro aparente de 11110 °/s contra 139,6 verdaderos. Verlo colapsar mientras
se gira es la explicación entera.

Leer: `truth/kinelab_truth/mocap.py` (el parser, la cinemática directa, el
mapeo a Halpe26, `APPROX_NOTES`, el marco del arnés y `events_3d`),
`truth/kinelab_truth/camera.py` (la proyección pinhole y los extrínsecos de
las dos vistas), `service/exploracion.py` (la lista blanca de archivos y la
forma de un trabajo de ejemplo), `service/app.py`
(`GET /api/datos/{id}/archivos/{nombre}`), `web/src/app/page.tsx`,
`web/src/components/Reproductor.tsx` (la convención de cuadro y los controles
que ya existen), `web/src/lib/api.ts`, `CONTEXTO.md` §Sistemas de coordenadas
e invariante 10, ADR-010, ADR-015.

## Qué existe ya

- `python -m kinelab_truth.mocap 64_01 --vista face_on --out DIR` deja un
  trabajo de ejemplo completo en `data/exploracion/`, que la pantalla ya
  lista y abre (encargos 07 y 08). Diez trials en `data/examples/cmu-mocap/`.
- El reproductor propio con cuadro a cuadro verificado, cámara lenta, zoom y
  marcas de evento.
- La lista blanca de archivos servidos por trabajo.

## Encargo

1. **Exportar el 3D.** `mocap.py` escribe además `pose3d.json` en el trabajo:
   los 26 puntos Halpe26 en **metros**, en el marco del arnés (origen entre
   los tobillos sobre el suelo, x hacia el objetivo, y arriba, z hacia la
   pelota), cuadro por cuadro, con 3 decimales; más `fps`, `frames`, los
   nombres y los pares de huesos, los cuadros de evento, la estatura del ASF,
   `APPROX_NOTES` (qué puntos son construidos y cómo) y la atribución de CMU.
   El marco y las unidades van declarados **dentro del archivo**, no en un
   comentario (`CONTEXTO.md` §Sistemas de coordenadas). Agregarlo a la lista
   blanca de `service/exploracion.py`.
2. **El visor**, componente nuevo `web/src/components/Visor3D.tsx`, que
   aparece **sólo** cuando el trabajo tiene `pose3d.json`:
   - Esqueleto de 26 puntos con sus huesos, sobre una grilla de suelo con
     escala en metros.
   - Arrastrar para girar azimut y elevación, rueda para acercar, y la misma
     línea de tiempo y los mismos controles que el reproductor: reproducir,
     pausa, cuadro a cuadro, cámara lenta, ir a address, top e impacto.
   - **Sin dependencias nuevas** (ADR-015): canvas 2D y la misma proyección
     pinhole de `camera.py`, escrita en TypeScript. Nada de WebGL ni de
     librerías 3D. Son 26 puntos.
3. **Que sirva para entender, no sólo para mirar:**
   - Dos botones, «ver como face_on» y «ver como down_the_line», que llevan
     la cámara exactamente a los extrínsecos del protocolo. Desde ahí, la
     imagen del visor tiene que parecerse a la del overlay de esa vista.
   - Un indicador permanente: el largo proyectado de la línea de caderas y
     el de la de hombros, en porcentaje de su largo real, desde el ángulo
     actual. Al girar hacia `down_the_line` tiene que caer a casi cero. Una
     línea de texto explica qué significa: desde ese ángulo esa línea no se
     puede medir, y por eso las métricas declaran vista.
4. **Los rótulos, siempre visibles:** de dónde sale (mocap CMU 64_01, medido
   con marcadores ópticos), que no es un video ni un swing de Hernán, y que
   **esto no se puede hacer con un clip de celular** porque una cámara sola
   no mide profundidad. Redacción para un entrenador, no para un ingeniero.

NO: no tocar `kinelab/` ni el contrato; no inventar 3D desde ningún video;
no agregar dependencias; no mostrar ningún número como juicio; no tocar
`web/src/lib/etiquetas.ts` ni `TablaEventos.tsx` (los toca el 16); no abrir
el navegador.

## Cómo se prueba

- `cd truth && .venv/bin/pytest -q` en verde, con tests nuevos: `pose3d.json`
  tiene 26 puntos finitos por cuadro; los pares laterales no están cruzados;
  el suelo está en cero; y **la prueba que importa**: proyectar el `pose3d`
  con los extrínsecos de `face_on` y de `down_the_line` reproduce, dentro de
  1 px, los keypoints 2D del `pose.npz` que ya escribe `mocap.py`. Si el
  visor y el arnés no coinciden, uno de los dos miente.
- `.venv/bin/pytest -q` y `cd web && pnpm lint && pnpm build` limpios.
- Regenerar los dos ejemplos (`face_on` y `down_the_line`) con la regla del
  top de ADR-017 ya aplicada, y verificar por `curl` que `pose3d.json` se
  sirve.
- Para Hernán: la lista de qué mirar, incluido qué tiene que pasar con el
  indicador de la línea de caderas al girar.

## En paralelo

El 16 toca `kinelab/`, el contrato, `explore.py`, `etiquetas.ts`,
`TablaEventos.tsx`, `tests/test_fase2.py`, `data/examples/`. El 18 toca
`kinelab/events/`, `sports/golf/events.py`, `tests/data/`. Vos:
`truth/kinelab_truth/mocap.py`, `truth/tests/`, `service/exploracion.py`,
`web/src/components/Visor3D.tsx` y el punto de entrada en `page.tsx`, que
tiene que ser lo más chico posible.
