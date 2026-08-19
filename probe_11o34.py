"""Instrument Takeover.advance: for BOTH scenarios, dump at EVERY advance
call: buyer, target, executor, and the target's holders (shares/loy/opp)
AT THAT MOMENT, plus which are picked as sellers."""
import gilded.society.realm as realm_mod
from gilded.society.schemes import Takeover
from gilded.chassis import GildedGame

BASE = (lambda loyalty, opinion: (loyalty is not None and loyalty < 40.0)
        or opinion <= -20
        or (loyalty is None and opinion < 0))


def dump_holders(g, realm, label):
    ruler = realm.ruler
    by_id = {ch.id: ch for ch in g.realms[realm.house_name].characters}
    print(f"  [{label}] target={realm.house_name} ruler={ruler.name}")
    for ch in realm.characters:
        shares = {e.name: e.ledger.get(ch.id, 0)
                  for e in g.enterprises if e.house == realm.house_name
                  and ch.id in e.ledger}
        if not shares:
            continue
        loy = getattr(ch, "loyalty", None)
        opp = ch._society.opinions.get((ch.id, ruler.id), "NONE")
        base_seller = BASE(loy, opp if opp != "NONE" else 0)
        print(f"    {ch.name:16} {ch.id} age={ch.age:2} loy={loy} "
              f"opp={opp} shares={shares} base_seller={base_seller} "
              f"child={ch.id in ruler.children_ids} "
              f"parent={ruler.id in ch.parent_ids}")


def run(seed, turns):
    g = GildedGame(seed=seed)
    print(f"########## seed {seed}, {turns} turns ##########")
    n_calls = 0
    for t in range(1, turns + 1):
        for tk in [tk for tk in list(g.takeovers) if not tk.complete]:
            n_calls += 1
            if n_calls > 14:
                print(f"  (truncating at 14 calls)")
                return
            buyer_realm = g.realms[tk.buyer_house]
            target_realm = g.realms[tk.target_house]
            dump_holders(g, target_realm,
                         f"turn {t} call {n_calls} buyer={tk.buyer_house} "
                         f"executor={getattr(tk.buyer, 'name', tk.buyer)}")
            sellers = realm_mod.disloyal_shareholders(target_realm,
                                                      g.enterprises)
            print(f"    -> sellers: {[c.name for c in sellers]}")
            tk.advance(g.realms, g.enterprises, g.rng, g)
        g.end_turn()


run(7, 12)
run(47, 4)
