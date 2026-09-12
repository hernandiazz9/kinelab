"""Configuración por deporte. Todo lo que el motor no tiene que saber vive acá."""

from __future__ import annotations

from kinelab.sport import SportConfig

from .golf.config import GOLF

SPORTS: dict[str, SportConfig] = {GOLF.id: GOLF}


def get_sport(sport_id: str) -> SportConfig:
    try:
        return SPORTS[sport_id]
    except KeyError:
        raise KeyError(f"deporte desconocido: '{sport_id}'. Disponibles: {', '.join(sorted(SPORTS))}") from None
