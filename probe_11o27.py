"""Which child is posted/measured in each scenario, and current seller lists."""
from gilded.chassis import GildedGame
from gilded.society.realm import disloyal_shareholders

for seed, turns, house in [(7, 1, "Ashworth"), (47, 4, "Vantrell")]:
    g = GildedGame(seed=seed)
    for _ in range(turns):
        g.end_turn()
    r = g.realms[house]
    print(f"=== {seed} {house} ===")
    court_ids = {ch.id for ch in r.court.positions.values() if ch is not None}
    dirs = {e.director_id for e in g.enterprises
            if e.house == house and e.director_id}
    for ch in r.characters:
        if ch.id in r.ruler.children_ids:
            loy = getattr(ch, "loyalty", None)
            shares = {e.name: e.ledger.get(ch.id, 0)
                      for e in g.enterprises if ch.id in e.ledger}
            opp = ch._society.opinions.get((ch.id, r.ruler.id), "NONE")
            print(f"  {ch.name:14} loyalty={loy} court={ch.id in court_ids} "
                  f"dir={ch.id in dirs} opp={opp} age={ch.age} shares={shares}")
    print("  current sellers:",
          [s.name for s in disloyal_shareholders(r, g.enterprises)])
