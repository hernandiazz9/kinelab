# 30 — "Python se ha cerrado inesperadamente": el abort al salir, en el motor y en el arnés

Para correr: `/encargo 30` en una sesión nueva, **solo** (edita
`kinelab/perception/`; nadie corre el motor mientras tanto). Después de él,
el 17 y luego el 29. Leé antes el informe del 27 (§2, «el exit 134 es
intermitente»), la auditoría del 16/9 §8, y `ESTADO.md` §cuarta sesión (el
`recursive_mutex lock failed` al cerrar el servidor con Ctrl-C).

## Contexto

Hernán ve seguido el cartel de macOS «Python se ha cerrado inesperadamente»
(SIGABRT). En la terminal es `libc++abi: … recursive_mutex lock failed` y
exit 134, **después** de que el proceso terminó su trabajo: al cerrar
`python -m service` con Ctrl-C, al terminar `cd truth && .venv/bin/pytest`
(intermitente: 0 / 134 / 0 en tres corridas del 27), y hay que verificar si
también al terminar `python -m kinelab datos` y `kinelab.perception`. Todo
apunta al teardown del proveedor CoreML de onnxruntime cuando quedó una
`InferenceSession` viva al salir del intérprete. No se pierden datos, pero la
regla del proyecto es leer las suites y los comandos por exit code, y un 134
aleatorio la rompe.

Leer: `kinelab/perception/estimator.py` (dónde se crea la sesión, si queda en
un global o en un objeto; el cache de modelos de CoreML), `kinelab/perception/
__init__.py` (qué carga al importar el paquete), `kinelab/perception/run.py`,
`kinelab/explore.py` (el estimador compartido), `service/exploracion.py`
(«estimador CoreML creado una vez y compartido») y `service/__main__.py`
(cómo cierra), `truth/kinelab_truth/mocap.py:49-50,402,557-559`,
`truth/tests/`, `AGENTS.md` §Cosas que muerden (CoreML), `HERENCIA.md`
§Gotchas de entorno.

## Encargo

1. **Diagnóstico reproducible, antes de tocar nada.** Diez corridas de cada
   uno, con su exit: `cd truth && .venv/bin/pytest`; `python -m kinelab datos
   ~/Desktop/cortado.mp4 --altura-m 1.75`; `python -m kinelab.perception`
   sobre un take de scratch; `python -m service` cerrado con SIGINT a los 5 s
   sin trabajos y después con un trabajo hecho; y `python -c "import
   kinelab.perception"`, `"import onnxruntime"`, `"import cv2"` y la creación
   de una sesión con el proveedor CoreML sin usarla. Tabla. El objetivo es una
   frase del tipo «aborta si y sólo si …», con los números.
2. **El arreglo, en la raíz.** Si es la sesión viva al salir: que quien la
   crea la libere explícitamente al terminar (`del` de la sesión y del
   estimador en un `close()` llamado desde los puntos de salida —el final
   de `explore`, el de `run_perception`, el apagado del servidor— y un
   `atexit` como red, con comentario de por qué). Si `kinelab.perception`
   carga el estimador o el proveedor al importar el paquete sin que el
   arnés lo use: carga perezosa en `__init__.py`, sin cambiar la API
   pública (`from kinelab.perception import X` sigue funcionando). Si el
   arnés queda con algo vivo por sus propios tests, un `conftest.py` en
   `truth/tests/` que lo libere en `pytest_sessionfinish`. **No** es
   aceptable `os._exit` para tapar el abort, ni ignorar el exit code en
   ningún script.
3. **Que no vuelva sin que se note.** Un script `truth/corridas.sh` (o en
   `banco/`) que corra N veces `cd truth && pytest` y falle si algún exit no
   es 0; y en `tests/`, un test del motor que lance `python -m kinelab datos`
   sobre el clip sintético en un subproceso y afirme exit 0 (hoy el test de
   explore corre en el mismo proceso y no lo ve). Una línea en `AGENTS.md`
   §Comandos o §Cosas que muerden con el comando y la causa.

NO: no tocar `sports/`, `web/`, `kinelab/metrics/`, `kinelab/events/`,
`kinelab/analysis.py`, `kinelab/perception/framing.py` (el 17), ningún
umbral, ni `sports/golf/mdc.yaml`; no cambiar ningún número de ninguna
corrida; no esconder el abort.

## Cómo se prueba

Diez corridas seguidas de cada uno de los comandos del punto 1 con exit 0 en
las diez, y la tabla antes/después. `.venv/bin/pytest` del motor (hoy 357,
más los tuyos) y `cd truth && .venv/bin/pytest` en verde por exit code y
conteo. Para Hernán: que el cartel deje de aparecer al cerrar el servidor y
al terminar `datos`; si aparece igual, decir en qué momento exacto.

## En paralelo

Ninguno. Vos: `kinelab/perception/estimator.py`, `__init__.py`, `run.py`,
`kinelab/explore.py` (sólo el cierre del estimador), `service/exploracion.py`
y `service/__main__.py` (sólo el apagado), `truth/tests/conftest.py`,
`truth/corridas.sh`, tus tests, `AGENTS.md` (una línea), `ESTADO.md` (tu
sección) y tu informe.
