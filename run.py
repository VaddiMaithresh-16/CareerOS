"""Single entrypoint. `python run.py` starts the API — no docker, no bare server
command to remember. Runs on Granian (Rust-based ASGI server) instead of Uvicorn —
Granian benchmarks meaningfully faster under concurrent load and ships a native
worker-process manager, so there's no separate Gunicorn layer needed either.
"""

import argparse

from granian import Granian
from granian.constants import Interfaces

from app.config import get_settings


def main():
    settings = get_settings()

    parser = argparse.ArgumentParser(description="Run the CareerOS API")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", default=False,
                         help="auto-reload on code change (off by default)")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    server = Granian(
        "app.main:app",
        address=args.host,
        port=args.port,
        interface=Interfaces.ASGI,
        workers=args.workers,
        reload=args.reload,
        reload_paths=["app"] if args.reload else None,  # never watch the sqlite db file
        log_level="info",
    )
    server.serve()


if __name__ == "__main__":
    main()
