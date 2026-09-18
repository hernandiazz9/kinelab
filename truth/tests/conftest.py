"""Lo que el arnés deja listo antes de importar cualquier test.

Una sola cosa, y no es una fixture: **importar `kinelab.perception` antes que
nada**. Ese `__init__` apaga la telemetría de onnxruntime poniendo
`ORT_DISABLE_TELEMETRY` en el entorno, y tiene que estar puesta antes de que
onnxruntime se cargue; si no, su hilo de subida despacha un evento al salir del
intérprete sobre un `recursive_mutex` ya destruido y el proceso termina en
SIGABRT (**exit 134**) con los 43 tests en verde. Medido en el encargo 30:
**7 de 10** corridas de esta suite abortaban así, y **0 de 10** con esto puesto.
La razón entera —con la pila de los `.ips` de macOS— está en
`kinelab/perception/__init__.py`, que es el único lugar donde vive.

El arnés llega a onnxruntime sin pedirlo: `test_angulos.py` compara sus
proyecciones contra las columnas del motor, eso importa `kinelab.explore`, y
`kinelab.explore` importa el estimador. Hoy los tests del arnés importan
`kinelab.perception.*` antes, así que la variable ya quedaría puesta por ese
camino; este `conftest` es para que siga siendo cierto el día que dejen de
hacerlo. `truth/` tiene su propio entorno (CONTEXTO.md, invariante 14): que el
motor y el arnés compartan este arreglo es a propósito, porque el bug es de una
dependencia que los dos instalan.
"""

from __future__ import annotations

import kinelab.perception  # noqa: F401 — sólo por su efecto: apagar la telemetría de onnxruntime
