"""Orden de picos entre segmentos, con la exclusión de ADR-008: dos picos a menos
de `min_gap_frames` no se ordenan, se declara `indeterminado`."""

from __future__ import annotations


def sequence_order(peaks: dict[str, int], *, min_gap_frames: int = 2) -> str:
    """`"pelvis>torso>arm"` por cuadro de pico creciente, o `"indeterminado"`."""
    if not peaks:
        return "sin_datos"
    ordered = sorted(peaks.items(), key=lambda kv: kv[1])
    for (_, a), (_, b) in zip(ordered, ordered[1:]):
        if abs(b - a) < min_gap_frames:
            return "indeterminado"
    return ">".join(name for name, _ in ordered)
