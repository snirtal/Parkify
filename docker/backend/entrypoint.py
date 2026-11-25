"""Container entrypoint for the Flask API.

Database credentials must already be in the process environment. This script
does not read or print them.
"""

from __future__ import annotations

import os
import sys


def main() -> None:
    if not os.getenv("DATABASE_URL", "").strip():
        print(
            "DATABASE_URL is not set. Pass it when starting the container. "
            "It is not stored in the image.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    os.execvp("python", ["python", "app.py"])


if __name__ == "__main__":
    main()
