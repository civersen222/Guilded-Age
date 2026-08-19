"""ALL share-holders of the target house in both scenarios, with the
full relationship map (dynasty, heirs, siblings, spouses)."""
from gilded.chassis import GildedGame


def dump(seed, turns, house):
    g = GildedGame(seed=seed)
    for _ in range(turns):
        g.end_turn()
    r = g.realms[house]
    ruler = r.ruler
    by_id = {ch.id: ch for ch in r.characters}
    print(f"=== {seed} {house} turn={turns} ===")
    print(f"dynasty: {type(r.dynasty).__name__} {getattr(r.dynasty, 'members', '?')}")
    try:
        print(f"  dynasty attrs: { {k: getattr(r.dynasty, k) for k in r.dynasty.__dict__ if not k.startswith('_')} }")
    except Exception as exc:
        print("  dyn fail:", exc)
    print(f"ruler {ruler.name} {ruler.id} age={ruler.age} children={ruler.children_ids} "
          f"parents={ruler.parent_ids} heir={ruler.is_heir}")
    # all characters who hold shares of the target house
    for ch in r.characters:
        shares = {e.name: e.ledger.get(ch.id, 0)
                  for e in g.enterprises if e.house == house
                  and ch.id in e.ledger}
        if not shares:
            continue
        loy = getattr(ch, "loyalty", None)
        opp = ch._society.opinions.get((ch.id, ruler.id), "NONE")
        unmeas = (loy is None
                  and (ch.id, ruler.id) not in ch._society.opinions)
        court = any(p is ch for p in r.court.positions.values())
        dirs = {e.director_id for e in g.enterprises if e.house == house}
        is_child = ch.id in ruler.children_ids
        is_parent = ruler.id in ch.parent_ids or ch.id in ruler.parent_ids
        sib = [c.name for c in r.characters
               if c.id != ch.id and set(c.parent_ids) & set(ch.parent_ids)]
        print(f"  {ch.name:14} {ch.id} age={ch.age:2} unmeas={unmeas} "
              f"court={court} dir={ch.id in dirs} child={is_child} "
              f"parent={is_parent} heirs={ch.is_heir} opp={opp} "
              f"loy={loy} sib={sib} shares={shares}")
    print()


dump(7, 1, "Ashworth")
dump(47, 4, "Vantrell")
