"""Every takeover call targeting a Vantrell house over seed-7's 12 turns,
plus the grip scenario's first house. Full relationship + grudge context
for every holder."""
from gilded.chassis import GildedGame
from gilded.society.realm import disloyal_shareholders


def full(g, realm, label):
    ruler = realm.ruler
    by_id = {ch.id: ch for ch in realm.characters}
    print(f"--- {label} target={realm.house_name} ruler={ruler.name} "
          f"{ruler.id} dyn={list(getattr(realm.dynasty, 'all_characters', {}).keys())}")
    for ch in realm.characters:
        shares = {e.name: e.ledger.get(ch.id, 0)
                  for e in g.enterprises if e.house == realm.house_name
                  and ch.id in e.ledger}
        if not shares:
            continue
        loy = getattr(ch, "loyalty", None)
        opp = ch._society.opinions.get((ch.id, ruler.id), "NONE")
        sibs = [c.name for c in realm.characters
                if c.id != ch.id and set(c.parent_ids) & set(ch.parent_ids)]
        # anyone in the household with a grudge against the ruler
        grudges = [f"{c.name}({c.id})={ch._society.opinions.get((c.id, ruler.id), 'NONE')}"
                   for c in realm.characters if c is not ch
                   and ch._society.opinions.get((c.id, ruler.id), 0) <= -20]
        print(f"  {ch.name:16} {ch.id} age={ch.age:2} loy="
              f"{('%.1f' % loy) if loy is not None else None} opp={opp} "
              f"shares={shares} child={ch.id in ruler.children_ids} "
              f"sibs={sibs} grudge_in_house={grudges}")


def run_door():
    g = GildedGame(seed=7)
    targets = set()
    for t in range(1, 13):
        for tk in [tk for tk in list(g.takeovers) if not tk.complete]:
            targets.add(tk.target_house)
            if t in (1, 2, 3, 6, 9, 12):
                full(g, g.realms[tk.target_house],
                     f"turn {t} buyer={tk.buyer_house} "
                     f"ex={getattr(tk.buyer, 'name', tk.buyer)}")
                print(f"   sellers: {[c.name for c in disloyal_shareholders(g.realms[tk.target_house], g.enterprises)]}")
        g.end_turn()
    print("TARGETS:", sorted(targets))
    return


def run_door_old():
    g = GildedGame(seed=7)
    for t in range(1, 13):
        for tk in [tk for tk in list(g.takeovers) if not tk.complete]:
            if tk.target_house == "Vantrell":
                full(g, g.realms["Vantrell"],
                     f"turn {t} buyer={tk.buyer_house} "
                     f"ex={getattr(tk.buyer, 'name', tk.buyer)}")
                print(f"   sellers: {[c.name for c in disloyal_shareholders(g.realms['Vantrell'], g.enterprises)]}")
        g.end_turn()


def run_grip():
    g = GildedGame(seed=7)
    # mimic _game() in test_grip: no turns? check both turn 0 and 1
    h = list(g.realms)[0]
    full(g, g.realms[h], f"turn 0 first_house={h}")


run_door()
run_grip()
