"""Compare family context: seed-7 Ashworth (turns 1..12) vs seed-47
Vantrell (turn 4). Focus: the children's other parent, dynasty, heirs."""
from gilded.chassis import GildedGame


def dump(seed, turns, house):
    g = GildedGame(seed=seed)
    for _ in range(turns):
        g.end_turn()
    r = g.realms[house]
    print(f"=== {seed} {house} turn={turns} ===")
    ruler = r.ruler
    by_id = {ch.id: ch for ch in r.characters}
    print(f"ruler {ruler.name} {ruler.id} alive={ruler.is_alive} "
          f"children={ruler.children_ids} parents={ruler.parent_ids}")
    # other parent(s) of each child
    for cid in ruler.children_ids:
        ch = by_id.get(cid)
        if ch is None:
            print(f"  child {cid} NOT IN REALM")
            continue
        for pid in ch.parent_ids:
            if pid == ruler.id:
                continue
            p = by_id.get(pid)
            print(f"  child {ch.name} parent {pid}: "
                  f"{p.name if p else 'NOT IN REALM'} "
                  f"alive={p.is_alive if p else '-'} "
                  f"shares={sum(e.ledger.get(pid,0) for e in g.enterprises if e.house==house)}")
    print("  dynasty:", [c.name for c in getattr(r, "dynasty", [])]
          if not isinstance(getattr(r, "dynasty", None), set)
          else None)
    print("  realm attrs dyn type:", type(r.dynasty))
    d = r.dynasty
    if hasattr(d, "heir_id") or hasattr(d, "__iter__"):
        try:
            print("  dynasty:", d)
        except Exception as exc:
            print("  dynasty repr fail:", exc)
    print()


dump(7, 1, "Ashworth")
dump(47, 4, "Vantrell")
