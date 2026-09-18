"""Percepción: del video a `pose.npz`.

Estimación de pose (RTMPose-m, Halpe26, vía rtmlib sobre onnxruntime con
CoreML), selección y seguimiento de un solo sujeto, plausibilidad anatómica por
cuadro, encuadre, y el almacén de pose cruda. Nada de acá conoce un deporte:
los umbrales llegan por `SportConfig.perception`.

`pose.npz` guarda la pose CRUDA del sujeto elegido (CONTEXTO.md, invariante 1).
Relleno de huecos, suavizado y máscaras por score son derivados que se aplican
al leer, nunca se hornean en el archivo.

Este `__init__` no importa nada del paquete a propósito (cargarlo no tiene que
traer onnxruntime ni los 155 MB de pesos): lo único que hace es apagar la
telemetría de onnxruntime ANTES de que alguien la cargue. Ver abajo.
"""

from __future__ import annotations

import os

# Apagar la telemetría de onnxruntime, antes de que se importe.
#
# onnxruntime 1.30 trae telemetría también en macOS
# (`onnxruntime/core/platform/posix/telemetry.cc`, con el SDK 1DS de Microsoft
# compilado adentro de `onnxruntime_pybind11_state.so`). Su hilo de subida
# despacha un evento al terminar el proceso y toma un `recursive_mutex` que los
# destructores estáticos ya destruyeron: `libc++abi: … recursive_mutex lock
# failed: Invalid argument`, excepción no atrapada, `std::terminate`, SIGABRT,
# **exit 134** — siempre DESPUÉS de que el trabajo quedó escrito. Es el cartel
# de macOS «Python se ha cerrado inesperadamente». La pila está en los 23
# informes de `~/Library/Logs/DiagnosticReports/Python-*.ips` del proyecto:
# `WorkerThread::threadFunc` → `HttpResponseDecoder::handleDecode` →
# `DebugEventSource::DispatchEvent` → `recursive_mutex::lock`.
#
# Medido en esta Mac (encargo 30): `cd truth && .venv/bin/pytest` abortaba en
# **7 de 10** corridas y da **0 de 10** con esta línea. No es la sesión de
# CoreML viva al salir: crear una `InferenceSession` con CoreML, usarla y
# dejarla viva da exit 0 en 10 de 10.
#
# Cualquier valor alcanza: onnxruntime mira si la variable EXISTE, no qué dice
# (medido: con `ORT_DISABLE_TELEMETRY=0` tampoco aborta, 6 de 6). Por eso
# `setdefault` acá sólo respeta a quien ya la haya puesto; para volver a
# habilitarla hay que borrarla del entorno, no ponerla en 0.
#
# Y va de suyo con el proyecto: esto corre en la Mac del entrenador, sin nube.
os.environ.setdefault("ORT_DISABLE_TELEMETRY", "1")
