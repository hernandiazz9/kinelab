"""Escritura de `analysis.json`: valida, versiona el anterior y escribe atómico.

Re-analizar conserva el `analysis.json` previo como
`analysis.<engine_version>.json` (nunca se borra; si ya existe, `-2`, `-3`…).
"""

from __future__ import annotations

import json
from pathlib import Path

from kinelab.contract.validate import ContractError, validate_analysis
from kinelab.perception.posestore import finite_or_none

ANALYSIS_FILE = "analysis.json"


def _archive_previous(take_dir: Path) -> Path | None:
    current = take_dir / ANALYSIS_FILE
    if not current.is_file():
        return None
    try:
        version = json.loads(current.read_text(encoding="utf-8"))["header"]["engine_version"]
    except (ValueError, KeyError, TypeError):
        version = "desconocida"
    dest = take_dir / f"analysis.{version}.json"
    n = 2
    while dest.exists():
        dest = take_dir / f"analysis.{version}-{n}.json"
        n += 1
    current.replace(dest)
    return dest


def write_analysis(take_dir: str | Path, analysis: dict) -> Path:
    take_dir = Path(take_dir)
    clean = finite_or_none(analysis)
    errors = validate_analysis(clean)
    if errors:
        raise ContractError(errors)
    _archive_previous(take_dir)
    path = take_dir / ANALYSIS_FILE
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    return path
