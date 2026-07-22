"""python -m gilded: the entry point.

  python -m gilded                      -> the graphical client (random seed)
  python -m gilded --seed N --house X   -> the graphical client
  python -m gilded --console <dir> ...  -> headless file-bridge (mission G19)
"""

import argparse
import random
import sys


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="gilded",
                                 description="The Gilded Machine")
    ap.add_argument("--console", metavar="DIR",
                    help="run headless, bridging commands through DIR")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--house", default=None,
                    help="the player House (default: the first house)")
    ap.add_argument("--ai-only", action="store_true",
                    help="no player house; every House is played by the AI")
    args = ap.parse_args(argv)
    seed = args.seed if args.seed is not None else random.randrange(1 << 30)

    if args.console:
        from gilded.console import run_console
        run_console(args.console, seed, args.house, args.ai_only)
        return 0

    from gilded.ui.app import run_app
    run_app(seed, args.house)
    return 0


if __name__ == "__main__":
    sys.exit(main())
