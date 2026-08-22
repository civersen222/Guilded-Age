"""The ONE place a game is written and read (stage S13).

Format: the ASCII header line ``GILDEDSAVE 1\n`` followed by the pickled
game object, docket included. load_game never leaks pickle's own errors:
every refusal is a SaveError with a message a player could read. It does
NOT call open_turn() — the docket rides in the file."""

import pickle

from gilded.chassis import GildedGame

HEADER_PREFIX = b"GILDEDSAVE "
SUPPORTED_VERSIONS = {1}


class SaveError(Exception):
    """A save file could not be written or read."""


def save_game(game: GildedGame, path) -> None:
    with open(path, "wb") as f:
        f.write(b"GILDEDSAVE 1\n")
        pickle.dump(game, f)


def load_game(path) -> GildedGame:
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        raise SaveError(f"the save could not be opened: {e}") from e

    if not data:
        raise SaveError("the save file is empty; it is not a game")

    nl = data.find(b"\n")
    if nl < 0:
        raise SaveError("the save file is not a Gilded save (missing header)")
    header = data[:nl]
    if not header.startswith(HEADER_PREFIX):
        raise SaveError("the save file is not a Gilded save (foreign header)")
    version_text = header[len(HEADER_PREFIX):]
    try:
        version = int(version_text)
    except ValueError:
        raise SaveError(
            f"the save file carries a version we do not understand: {version_text!r}")
    if version not in SUPPORTED_VERSIONS:
        raise SaveError(f"unknown save version {version}; this build knows {sorted(SUPPORTED_VERSIONS)}")

    payload = data[nl + 1:]
    try:
        game = pickle.loads(payload)
    except Exception as e:  # UnpicklingError and friends, all mapped
        raise SaveError(f"the save file is corrupt and could not be read: {e}") from e

    if not isinstance(game, GildedGame):
        raise SaveError("the save file does not hold a game")
    return game
