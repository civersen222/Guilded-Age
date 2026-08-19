from gilded.chassis import GildedGame
from gilded.society.realm import disloyal_shareholders, tick_loyalty
import gilded.society.realm as realm_mod

g = GildedGame(seed=7)
h = sorted(g.houses)[0]
r = g.realms[h]

# Track family holders across turns
def show(g, r, tag):
    print(f"== {tag} t={g.turn} house={r.house_name}")
    for ch in r.characters:
        if not ch.is_alive or ch.id == r.ruler.id: continue
        ents = [e for e in g.enterprises if e.house == r.house_name]
        holding = sum(e.ledger.get(ch.id, 0) for e in ents)
        if holding <= 0: continue
        loy = getattr(ch, "loyalty", None)
        op = ch._society.opinions.get((ch.id, r.ruler.id), 0)
        posted = any(v is not None and v.id == ch.id for v in r.court.positions.values())
        is_dir = any(e.director_id == ch.id for e in ents)
        print(f"  {ch.name!r} age={ch.age} shares={holding} loy={loy} op={op} posted={posted} dir={is_dir}")

show(g, r, "t0")
print(f"  sellers(house_only=True):  {[c.name for c in disloyal_shareholders(r, g.enterprises)]}")
print(f"  sellers(house_only=False): {[c.name for c in disloyal_shareholders(r, g.enterprises, house_only=False)]}")

# Now step through end_turn and track
for i in range(12):
    g.end_turn()
    # find the realm again (it might have changed)
    r = g.realms.get(h)
    if r is None:
        print(f"t{i+1}: realm {h} is None")
        continue
    show(g, r, f"t{i+1}")
    print(f"  sellers(house_only=False): {[c.name for c in disloyal_shareholders(r, g.enterprises, house_only=False)]}")
    # also check takeovers
    for tk in g.takeovers:
        if not tk.complete:
            print(f"  takeover: buyer={tk.buyer.name} target={tk.target_house}")
