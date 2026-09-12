"""`python -m service`: levanta la página del gate en localhost."""

from __future__ import annotations

import os

import uvicorn

from service.app import create_app


def main() -> int:
    host = os.environ.get("KINELAB_HOST", "127.0.0.1")
    port = int(os.environ.get("KINELAB_PORT", "8765"))
    app = create_app()
    print(f"kinelab · gate de ingesta · http://{host}:{port}  (datos en {app.state.data_dir})")
    uvicorn.run(app, host=host, port=port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
