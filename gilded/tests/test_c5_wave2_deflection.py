import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
from gilded.ui.app import new_app_state

def _head_name(order):
    h = getattr(order, "head", None)
    return getattr(h, "name", h)

def test_bank_receivership_collision_logs_deflection_beat():
    for seed in range(3, 19):
        s = new_app_state(seed=seed)
        g = s.game
        player = s.house
        for _ in range(16):
            g.end_turn()
            goal = getattr(g.orders["Bank"], "goal", None)
            if (goal is not None
                    and getattr(goal, "family", None) == "Receivership"
                    and getattr(goal, "target", None) in g.houses
                    and goal.target != player
                    and getattr(goal, "opened_turn", None) == g.resolved_turn):
                target = goal.target
                bank_head = _head_name(g.orders["Bank"])
                g.set_ambition(player, "Buyout", target)
                for _ in range(10):
                    g.end_turn()
                st = g.ambitions.status(player)
                assert st.get("fulfilled") is False, f"seed {seed}: {st!r}"
                defl = [bt for bt in g.beats.log
                        if getattr(bt, "kind", None) == "deflection"
                        and getattr(bt, "face", None) == bank_head
                        and "Receivership" in (getattr(bt, "text", "") or "")
                        and "of 10" in (getattr(bt, "text", "") or "")]
                assert defl, (f"seed {seed}: thwarted but no deflection beat "
                              f"faced by {bank_head!r} naming Receivership + 'of 10'")
                return
    raise AssertionError("no seed in 3-18 opened a fresh Bank Receivership "
                        "of a non-player house within 16 turns")
