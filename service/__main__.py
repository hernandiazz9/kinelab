"""`python -m service`: levanta la página del gate en localhost."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn

from service.app import create_app


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m service", description="Página local del gate de ingesta.")
    ap.add_argument("--data", type=Path, default=None, help="carpeta data/ (por defecto la del repo, o KINELAB_DATA)")
    ap.add_argument("--host", default=os.environ.get("KINELAB_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("KINELAB_PORT", "8765")))
    args = ap.parse_args(argv)
    host, port = args.host, args.port
    app = create_app(data_dir=args.data)
    print(f"kinelab · gate de ingesta · http://{host}:{port}  (datos en {app.state.data_dir})")
    uvicorn.run(app, host=host, port=port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
