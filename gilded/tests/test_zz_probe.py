import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gilded.chassis import GildedGame

def _find(g, name):
    for h in g.realms.values():
        for ch in h.characters:
            if ch.name == name:
                return ch
    return None

def test_dump():
    g = GildedGame(seed=5)
    bjorn = _find(g, "Bjorn")
    print("\n=== PROBE ===")
    print("turn", g.turn)
    if bjorn:
        print("Bjorn t0 base=", dict(bjorn.base_stats))
    realm = g.realms["Duval-Corse"]
    for pos, ch in realm.court.positions.items():
        if ch is not None:
            print("t0", pos, ch.name, dict(ch.base_stats))
    print("=== END ===")
