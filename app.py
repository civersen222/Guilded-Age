#!/usr/bin/env python
"""Entry point for The Gilded Machine."""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", os.environ.get("SDL_VIDEODRIVER", "windib"))

from gilded.ui import app


def main():
    app.run_app()


if __name__ == "__main__":
    main()
