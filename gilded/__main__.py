"""python -m gilded (mission G19): the console entry point.

  python -m gilded --console <dir> [--seed N] [--house NAME] [--ai-only]

The graphical client arrives in G23; until then --console is the way in.
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

    print("The graphical client arrives in mission G23. "
          "For now, run with --console <dir>.")
    return 0


if __name__ == "__main__":
    sys.exit(main())