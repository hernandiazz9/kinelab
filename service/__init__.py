"""Servicio local mínimo: una página para pasar clips por el gate de la Fase 0.

Construido a pedido del entrenador antes de la Fase 4 (ver ESTADO.md). Expone
sólo lo que la Fase 0 produce: la verdad del fps de un clip y el veredicto del
gate con su `capture.json`. No hay pose, métricas ni visor: eso llega con las
Fases 1 a 4. El motor (`kinelab/`) no sabe que esto existe.

    .venv/bin/python -m service          # http://127.0.0.1:8765
"""
