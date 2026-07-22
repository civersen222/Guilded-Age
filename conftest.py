"""Test-session defaults for CivKings.

The Gilded Saga Narrator (gilded/saga/narrator.py) calls a local language model
in real play, but every automated test must stay deterministic and offline. This
forces the templated (identity) narrator for the whole test session unless a run
explicitly opts in with GILDED_NARRATE=1. select_narrator() reads this env var,
and subprocesses (e.g. the console bridge test) inherit it."""

import os

os.environ.setdefault("GILDED_NARRATE", "0")
