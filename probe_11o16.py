from gilded.chassis import GildedGame
from gilded.society.realm import DISLOYAL_LOYALTY, DISLOYAL_OPINION

def run(seed=7, turns=12):
    g = GildedGame(seed=seed)
    target = None
    # find a live takeover target like the door test does
    for _ in range(turns):
        g.end_turn()
        for tk in list(g.takeovers):
            if not tk.complete:
                realm = g.realms.get(tk.target_house)
                ruler = realm.ruler
                ents = [e for e in g.enterprises if e.house == tk.target_house]
                print(f"t{g.turn} target={tk.target_house} ruler={ruler.name} "
                      f"buyers={tk.buyer_house}")
                for ch in realm.characters:
                    if ch.id == ruler.id or not ch.is_alive:
                        continue
                    shares = [e.ledger.get(ch.id) for e in ents]
                    if not any(shares):
                        continue
                    op = ch._society.opinions.get((ch.id, ruler.id), None)
                    loy = getattr(ch, "loyalty", None)
                    in_dyn = ch.id in {c.id for c in realm.dynasty.get_all_members()}
                    base = (loy is not None and loy < DISLOYAL_LOYALTY) or \
                           (op is not None and op <= DISLOYAL_OPINION)
                    fam = (loy is None and op is None and not in_dyn)
                    print(f"    {ch.name} dyn={in_dyn} op={op} loy={loy} "
                          f"base_seller={base} non_dyn_unmeas={fam}")
                break

run()
