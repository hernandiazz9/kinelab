"""Percepción: del video a `pose.npz`.

Estimación de pose (RTMPose-m, Halpe26, vía rtmlib sobre onnxruntime con
CoreML), selección y seguimiento de un solo sujeto, plausibilidad anatómica por
cuadro, encuadre, y el almacén de pose cruda. Nada de acá conoce un deporte:
los umbrales llegan por `SportConfig.perception`.

`pose.npz` guarda la pose CRUDA del sujeto elegido (CONTEXTO.md, invariante 1).
Relleno de huecos, suavizado y máscaras por score son derivados que se aplican
al leer, nunca se hornean en el archivo.
"""
