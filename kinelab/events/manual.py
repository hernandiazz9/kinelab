"""Corrección manual de eventos: `events-manual.json` en la toma.

Portado en espíritu de padel-coach analyzer/padel_analyzer/adjust.py:132-234
(ADR-013), más el chequeo que ahí faltaba: dos repeticiones no pueden
compartir cuadro (HERENCIA.md §Bugs concretos). El valor detectado nunca se
pierde (`frame_detected`).
"""

from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass
from pathlib import Path

MANUAL_FILE = "events-manual.json"
MANUAL_SCHEMA_VERSION = "1.0.0"


@dataclass
class Edit:
    rep: int
    event: str
    frame: int
    edited_at: str
    note: str = ""


class EventCollisionError(ValueError):
    """Una corrección deja dos repeticiones en el mismo cuadro o un evento fuera de orden."""


def load_edits(take_dir: str | Path) -> list[Edit]:
    p = Path(take_dir) / MANUAL_FILE
    if not p.is_file():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    return [Edit(**e) for e in data.get("edits", [])]


def save_edits(take_dir: str | Path, edits: list[Edit]) -> Path:
    p = Path(take_dir) / MANUAL_FILE
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"schema_version": MANUAL_SCHEMA_VERSION, "edits": [asdict(e) for e in edits]}, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)
    return p


def check_consistency(events: list[dict], order: tuple[str, ...]) -> None:
    """Dentro de cada repetición los eventos van en orden estricto; entre
    repeticiones, ningún evento comparte cuadro y no se solapan."""
    by_rep = sorted(events, key=lambda e: e["rep"])
    for rep in by_rep:
        frames = [(name, rep[name]["frame"]) for name in order if rep.get(name)]
        for (na, fa), (nb, fb) in zip(frames, frames[1:]):
            if fb <= fa:
                raise EventCollisionError(f"repetición {rep['rep']}: {nb} (cuadro {fb}) no puede ir antes o en el mismo cuadro que {na} (cuadro {fa}).")
    for a, b in zip(by_rep, by_rep[1:]):
        for name in order:
            if a.get(name) and b.get(name) and a[name]["frame"] == b[name]["frame"]:
                raise EventCollisionError(f"las repeticiones {a['rep']} y {b['rep']} comparten el cuadro {a[name]['frame']} en {name}.")
        a_end = max((a[n]["frame"] for n in order if a.get(n)), default=None)
        b_start = min((b[n]["frame"] for n in order if b.get(n)), default=None)
        if a_end is not None and b_start is not None and b_start <= a_end:
            raise EventCollisionError(f"la repetición {b['rep']} empieza (cuadro {b_start}) antes de que termine la {a['rep']} (cuadro {a_end}).")


def apply_edits(events: list[dict], edits: list[Edit], *, fps: float, order: tuple[str, ...]) -> list[dict]:
    """Aplica las correcciones y devuelve una copia; conserva `frame_detected`."""
    out = copy.deepcopy(events)
    by_rep = {e["rep"]: e for e in out}
    for ed in edits:
        rep = by_rep.get(ed.rep)
        if rep is None:
            raise EventCollisionError(f"no hay repetición {ed.rep}.")
        if ed.event not in order:
            raise EventCollisionError(f"evento desconocido: {ed.event}.")
        ev = rep.get(ed.event)
        if ev is None:
            ev = {"id": ed.event, "frame": ed.frame, "t_s": 0.0, "tol_frames": 1, "uncertainty_s": round(1 / fps, 5), "method": "manual", "manual": True, "frame_detected": None}
            rep[ed.event] = ev
        if ev.get("frame_detected") is None:
            ev["frame_detected"] = ev["frame"] if not ev.get("manual") else None
        ev["frame"] = int(ed.frame)
        ev["t_s"] = round(ed.frame / fps, 4)
        ev["manual"] = True
    check_consistency(out, order)
    return out
