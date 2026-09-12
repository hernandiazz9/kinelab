"""Una sesión en disco: `data/sessions/<atleta>/<fecha>/<gesto>/<vista>/take-NN/`.

El `take-NN` se reserva con un `mkdir` atómico, así dos ingestas simultáneas
no pisan la misma carpeta (lección heredada de `padel-coach`).
"""

from __future__ import annotations

import hashlib
import re
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

# Minúsculas, dígitos, guion y guion bajo (las vistas son `face_on` y
# `down_the_line`). Empieza con letra o dígito.
SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
MAX_TAKES = 99


def validate_slug(value: str, what: str) -> str:
    if not SLUG.match(value):
        raise ValueError(f"{what} inválido: '{value}'. Sólo minúsculas, dígitos, guion y guion bajo, sin espacios.")
    return value


def session_root(data_dir: Path, athlete: str, day: date, gesture: str, view: str) -> Path:
    return data_dir / "sessions" / athlete / day.isoformat() / gesture / view


def reserve_take(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for n in range(1, MAX_TAKES + 1):
        candidate = root / f"take-{n:02d}"
        try:
            candidate.mkdir()
        except FileExistsError:
            continue
        return candidate
    raise RuntimeError(f"{root}: más de {MAX_TAKES} tomas en la misma sesión")


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def copy_original(src: Path, take_dir: Path) -> Path:
    """Copia — nunca mueve — el archivo tal como llegó. La extensión se conserva
    en minúsculas para que `original.mov` y `original.MOV` sean lo mismo."""
    dest = take_dir / f"original{src.suffix.lower()}"
    shutil.copy2(src, dest)
    return dest


def recording_date(creation_time: str | None, src: Path, override: date | None) -> date:
    """La fecha de la sesión: la que diga el humano; si no, la del archivo; si
    no, la de modificación del archivo."""
    if override is not None:
        return override
    if creation_time:
        try:
            return datetime.fromisoformat(creation_time.replace("Z", "+00:00")).date()
        except ValueError:
            pass
    return datetime.fromtimestamp(src.stat().st_mtime, tz=timezone.utc).date()
