"""Capture unmeasured holders at the EXACT firing call site (mid-end_turn),
full attributes, for seed-7 (door) and seed-47 (fixture), to find the
discriminating feature."""
import gilded.society.realm as realm_mod
from gilded.chassis import GildedGame


def run(seed, turns, target_names, label):
    g = GildedGame(seed=seed)
    orig = realm_mod.disloyal_shareholders
    rows = []

    def counting(realm, *rest, **kwargs):
        sellers = orig(realm, *rest, **kwargs)
        targets = {tk.target_house for tk in g.takeovers if not tk.complete}
        if realm is not None and realm.house_name in targets:
            for s in sellers:
                loy = getattr(s, "loyalty", None)
                if loy is not None:
                    continue  # only unmeasured (the contested ones)
                ruler = realm.ruler
                is_child = s.id in ruler.children_ids
                is_parent = ruler.id in s.children_ids
                check_ents = [e for e in g.enterprises if e.house == realm.house_name]
                holdings = {e.name: round(e.ledger.get(s.id, 0), 1)
                           for e in check_ents if s.id in e.ledger}
                is_director = any(e.director_id == s.id for e in check_ents)
                rows.append(f"{label} {realm.house_name:10s} {s.name[:12]:12s} {s.id} "
                            f"age={s.age:2d} child={int(is_child)} parent={int(is_parent)} "
                            f"director={int(is_director)} holds={list(holdings)}")
        return sellers

    realm_mod.disloyal_shareholders = counting
    try:
        for _ in range(turns):
            g.end_turn()
    finally:
        realm_mod.disloyal_shareholders = orig

    print(f"--- {label} seed={seed} (unmeasured firing sellers) ---")
    for r in rows:
        print("  " + r)
    print()


run(7, 12, None, "DOOR-7")
run(47, 4, None, "FIX-47")
