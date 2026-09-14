# 07 — Un swing de muestra desde mocap real (CMU), y el primer número de nivel 1

Para correr: `/encargo 07` en una sesión nueva. Leé antes los informes del
04, 06 y 08 en `docs/informes/`: el 06 dejó `explore()` con `camino` y
procedencia, y el 08 documentó la forma de un trabajo de ejemplo.

## Contexto

Hernán quiere un swing de muestra que se vea andar en la pantalla de
exploración: los palitos, los ángulos en cada evento, reproducir, frenar,
cuadro a cuadro. No para comparar ni medir contra él: para ver la
herramienta funcionando sobre un swing que no sea el suyo. No sale de un
dibujo inventado ni de YouTube (`HERENCIA.md`, cementerio 1): sale de captura
de movimiento real. ADR-009 ya fija la base de datos de mocap de CMU como el
nivel 1 de validación del arnés (movimiento humano real, licencia libre con
atribución), y ADR-010 la lista como "Sí. Tiene golf". Este encargo hace las
dos cosas con la misma corrida: el ejemplo, y la primera comparación de una
métrica calculada desde 2D contra un valor verdadero 3D de un humano.

Leer: `truth/kinelab_truth/chain.py`, `camera.py`, `swing.py`, `harness.py`
(la cadena, la cámara virtual, cómo se proyecta y qué formato de keypoints
produce); `tests/helpers/synth_swing.py`; `kinelab/explore.py` (cómo dibuja
el overlay, qué escribe en `datos-eventos.json`, y lo que agregaron el 04 y
el 06); `sports/golf/events.py`; `service/exploracion.py` (la forma de un
trabajo en `data/exploracion/<id>/`, para que el ejemplo se abra desde la
pantalla que hace el 08); `CONTRATO.md` §pose.npz (provenance).

## Qué existe ya

- El arnés en `truth/` con entorno propio: esqueleto de 26 puntos Halpe26,
  cámara pinhole con extrínsecos `face_on` y `down_the_line`, swing
  paramétrico. Puede agregar dependencias a su `pyproject` sin tocar el del
  motor.
- `explore.explore()` corre pose + eventos + overlay + CSV + JSON sobre un
  video. El overlay dibuja esqueleto, ángulos de codos y rodillas y eventos.
- `data/examples/` **sí** viaja con el repo (`.gitignore` lo exceptúa).
- La forma de un trabajo de ejemplo está documentada en el encabezado de
  `service/exploracion.py` (encargo 08): una carpeta en `data/exploracion/`
  con los mismos archivos y un `trabajo.json` con `estado: listo`,
  `origen: ejemplo` y `etiqueta`. El id es el nombre de la carpeta.
- Hay un ejemplo **de mentira** armado a mano por el 08 para probar la
  lista: `data/exploracion/ejemplo-a-mano-cortado-face_on`. Borralo al dejar
  el de verdad.
- En exploración la procedencia del fps es siempre `sin_verificar`
  (ADR-016). Para el mocap no inventes un camino de captura: dejá el default
  y que la `etiqueta` y `fps_aviso` digan "fps 120 exacto por construcción
  (mocap CMU), cámara virtual, no es video". Sin juicio, como todo lo demás.

## Encargo

1. Bajar de `mocap.cs.cmu.edu` los archivos ASF/AMC del sujeto de golf
   (según el índice del sitio es el 64; verificalo). Guardarlos en
   `data/examples/cmu-mocap/` con un `ATRIBUCION.md` con el texto que pide
   CMU y el sha256 de cada archivo. Elegí uno o dos trials de swing completo
   (no putt) y decí por qué.
2. En `truth/`, `python -m kinelab_truth.mocap TRIAL --vista face_on|
   down_the_line --out DIR`: parsea ASF/AMC (parser propio en numpy, o una
   dependencia con licencia MIT/BSD/Apache anotada en el `pyproject` de
   `truth/`), mapea las articulaciones del esqueleto de CMU a los 26 puntos
   Halpe26 (documentá el mapeo y sus aproximaciones: cara, `hip`, talones y
   puntas), lo proyecta con la cámara virtual del arnés a 1080×1920 vertical
   con el sujeto al 80 % del alto, y escribe un `pose.npz` con `provenance`
   que diga `source: cmu-mocap`, trial, fps 120, cámara `sin_verificar`, y
   `scores` en 1,0.
3. Desde ese `pose.npz`, el mismo camino que un video: eventos de golf,
   ángulos, `datos-eventos.json`, CSV, y el `overlay.mp4` con los palitos
   sobre fondo liso, con una línea quemada en cada cuadro: "mocap CMU
   <trial> · cámara virtual · no es video". Para eso, `explore` tiene que
   poder arrancar de un `pose.npz` en vez de correr el estimador (cambio
   mínimo en `explore.py`; si el dibujo no está factorizado para eso, es la
   única refactorización permitida y la decís en el informe). El resultado
   queda como un trabajo en `data/exploracion/ejemplo-cmu-<trial>-<vista>/`
   con `trabajo.json` en estado listo y `origen: ejemplo`, la forma que el
   encargo 08 lista en la pantalla.
4. El primer número de nivel 1: para el trial elegido, en `face_on`, el
   desplazamiento lateral de pelvis entre address y top calculado por el
   motor desde la proyección 2D (`pelvis_sway_cm` o la primitiva que use)
   contra el desplazamiento verdadero del centro de cadera 3D del mocap en el
   mismo eje, en cm. Sesgo en cm, en el informe. Lo mismo para las duraciones
   (backswing y downswing) contra los eventos leídos a mano sobre las curvas
   3D. Es un solo trial: es una primera lectura, no una tabla; decilo así.

NO: no tocar `web/` ni `service/` (eso es el 08); no usar el mocap para
ajustar ningún umbral de eventos ni de métricas; no llamar a nada de esto
"referencia" ni "ideal": es un ejemplo y un dato de validación; no commitear
el `overlay.mp4` (se genera).

## Cómo se prueba

- `cd truth && .venv/bin/pytest -q` en verde con tests nuevos: el parser
  sobre un AMC mínimo escrito en el test; el mapeo produce 26 puntos con las
  simetrías bien (izquierda/derecha); la proyección de un punto conocido cae
  donde la cámara dice.
- `.venv/bin/pytest -q` en verde (el cambio en `explore.py` con un test que
  arranque de un `pose.npz` sintético).
- La corrida real: rutas del trabajo generado en las dos vistas, eventos
  detectados (address, top, impacto en cuadros y segundos), y los números de
  nivel 1 del punto 4.
- Para Hernán: cuando el 08 esté, abrir el ejemplo desde la lista y mirar que
  se reproduzca, frene y vaya cuadro a cuadro con los ángulos.

## En paralelo

El 09 toca `service/` y `web/` (y quizá una línea de `explore.py` en la
etapa de la ficha); el 10 toca `kinelab/metrics/registry.py`,
`tests/test_fase2.py` y `CONTRATO.md` §sextuplo. No los toques; si chocás en
`explore.py`, tu cambio es sólo "arrancar de un `pose.npz`".
