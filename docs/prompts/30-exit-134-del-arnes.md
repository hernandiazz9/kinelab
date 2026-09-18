# 30 — El exit 134 del arnés: encontrar la causa y frenarlo sin esconderlo

Para correr: `/encargo 30` en una sesión nueva, **después de que cierre el
17**, en paralelo con el 29. Leé antes el informe del 27 (§2, «el exit 134
es intermitente») y la auditoría del 16/9 §8.

## Contexto

`cd truth && .venv/bin/pytest` imprime su resumen en verde y después, a
veces, el intérprete aborta: `libc++abi: … recursive_mutex lock failed`,
exit 134. El 27 midió que es **intermitente** (0 / 134 / 0 en tres corridas
seguidas, siempre con 43 pasados); la auditoría lo vio en 2 de 2. La regla
del proyecto es leer las suites por exit code y conteo, y un 134 aleatorio
rompe esa regla: nadie puede distinguir "todo pasó y el cierre explotó" de
"algo pasó de verdad" sin leer la salida. El mismo mensaje apareció al
cerrar `python -m service` con Ctrl-C (ESTADO, cuarta sesión), atribuido al
teardown de CoreML. El arnés no debería crear ninguna sesión de CoreML: ver
qué importa y qué construye.

Leer: `truth/kinelab_truth/mocap.py:49-50,402,557-559` (importa
`kinelab.perception.*`), `kinelab/perception/__init__.py` (qué carga al
importar el paquete: ¿el estimador, onnxruntime, el proveedor CoreML?),
`kinelab/perception/estimator.py` (si crea sesiones al importar o sólo al
llamar), `truth/tests/conftest.py` si existe, `truth/pyproject.toml`,
`AGENTS.md` §Cosas que muerden (CoreML), `HERENCIA.md` §Gotchas de entorno
(CoreML: sesión y cache).

## Encargo

1. **Diagnóstico reproducible antes de tocar nada.** Correr `cd truth &&
   .venv/bin/pytest` diez veces y anotar el exit de cada una. Después
   bisectar por importación: `python -c "import kinelab.perception"`,
   `"import onnxruntime"`, `"import cv2"`, y las combinaciones, diez veces
   cada una, con el exit. Y por test: `pytest truth/tests/test_mocap.py`
   solo, `test_subframe_encuadre.py` solo, etc. El objetivo es una frase del
   tipo "aborta si y sólo si se importó X y se creó Y", con la tabla que la
   sostiene. Mirá también las variables de entorno de onnxruntime y OpenCV
   (`OMP_NUM_THREADS`, `cv2.setNumThreads`) si aparecen en el camino.
2. **El arreglo, en `truth/` si alcanza.** Si la causa es que importar
   `kinelab.perception` carga el estimador o el proveedor de CoreML sin que
   el arnés lo use, la solución correcta es que el paquete no lo cargue al
   importar (carga perezosa en `kinelab/perception/__init__.py`), pero **ese
   archivo es de `kinelab/` y no lo tocás**: dejá el diff exacto en el
   informe para un encargo que edite el motor, y mientras tanto, en
   `truth/`, importá lo que el arnés necesita por el camino que no dispare
   la carga si existe, o documentá que no existe. Si la causa está en el
   cierre (un objeto vivo al salir), un `conftest.py` del arnés que lo libere
   explícitamente en `pytest_sessionfinish` es aceptable. **No** es aceptable
   `os._exit` para tapar el abort, ni ignorar el exit code en ningún script.
3. **Un test o chequeo que lo fije:** un script en `truth/` que corra la suite
   N veces y falle si algún exit no es 0, para que la próxima vez que vuelva
   se vea (y la orden para correrlo en el informe y en `truth/README` o en
   `AGENTS.md` §Comandos, una línea).

NO: no tocar `kinelab/`, `sports/`, `service/`, `web/`; no cambiar ningún
número del arnés ni `sports/golf/mdc.yaml` (si tu cambio en `truth/` obliga
a regenerar la tabla, no la regeneres: decilo); no esconder el abort.

## Cómo se prueba

Diez corridas seguidas de `cd truth && .venv/bin/pytest` con exit 0 en las
diez, y la tabla del diagnóstico. `.venv/bin/pytest` del motor sin cambios
(357).

## En paralelo

El 29 toca `kinelab/tools/camera_drift.py` y `tests/test_camera_drift.py`.
Vos: `truth/` (salvo `mocap.py` si no hace falta; si hace falta, es tuyo,
nadie más lo toca), `AGENTS.md` una línea, `ESTADO.md` (tu sección) y tu
informe.
