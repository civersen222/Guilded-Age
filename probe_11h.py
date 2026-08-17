"""Probe for Stage 11H: money supply and docket crowding measurement."""
import sys
from gilded.chassis import GildedGame

BASE_PURSES = {
    "Ashworth": 1834, "Brandtner": 1181, "Duval-Corse": 2277,
    "Ferrenholt": 3891, "Karsgate": 1692, "Mordaine": 2608, "Vantrell": 1117,
}
BASE_TOTAL = 14601
BASE_LABELS = {
    "expansion": 22013, "railway": 5750, "charter": 2000,
    "strike buyoff": 900, "heir allowance": 500, "share purchase": 160,
}

def run_probe():
    g = GildedGame(7)
    for _ in range(12):
        if g.game_over is not None:
            break
        g.end_turn()

    # 1. Total gold
    total = sum(h.treasury for h in g.houses.values())
    low, high = 13141, 16061
    r1 = low <= total <= high
    print(f"1. Total gold: {total:.0f}  (target {BASE_TOTAL}, band {low}-{high})  {'PASS' if r1 else 'FAIL'}")

    # 2. Per-house within 40%
    r2 = True
    for name, base in BASE_PURSES.items():
        h = g.houses.get(name)
        if h is None:
            print(f"2. {name}: MISSING  FAIL")
            r2 = False
            continue
        pct = (h.treasury - base) / base * 100
        ok = abs(pct) <= 40
        if not ok:
            r2 = False
        print(f"2. {name}: {h.treasury:.0f} vs base {base} ({pct:+.1f}%)  {'PASS' if ok else 'FAIL'}")

    # 3. Ledger table (union of all labels)
    took = {}
    gave = {}
    for h in g.houses.values():
        for turn, label, amount in h.journal:
            if amount < 0:
                took[label] = took.get(label, 0) + abs(amount)
            else:
                gave[label] = gave.get(label, 0) + amount
    all_labels = sorted(set(took) | set(gave))
    print(f"\n{'Label':<20} {'Took':>10} {'Gave':>10} {'Net':>10}")
    for label in all_labels:
        t = took.get(label, 0)
        gv = gave.get(label, 0)
        net = gv - t
        print(f"{label:<20} {t:>10.0f} {gv:>10.0f} {net:>10.0f}")

    # 4. Base label floors (10%)
    r4 = True
    print(f"\n{'Base label':<20} {'Base spent':>12} {'Now spent':>12} {'Floor':>8}  Result")
    for label, base_amt in BASE_LABELS.items():
        now = took.get(label, 0)
        floor = base_amt * 0.1
        ok = now >= floor
        if not ok:
            r4 = False
        print(f"{label:<20} {base_amt:>12.0f} {now:>12.0f} {floor:>8.0f}  {'PASS' if ok else 'FAIL'}")

    # 5. Docket kind counts
    kind_counts = {}
    for h in g.houses.values():
        for petition in getattr(h, '_docket', []):
            kind = petition.kind
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
    # Count from generated petitions over the run - need to track during play
    # Alternative: check journals for petition-related entries
    print(f"\nDocket kind counts (from current docket):")
    for kind, count in sorted(kind_counts.items(), key=lambda x: -x[1]):
        print(f"  {kind:<25} {count}")

    # Summary
    results = [r1, r2, r4]
    print(f"\n{'='*60}")
    print(f"Requirements passed: {sum(results)}/{len(results)}")
    print(f"  1. Total in band: {'PASS' if r1 else 'FAIL'}")
    print(f"  2. Per-house within 40%: {'PASS' if r2 else 'FAIL'}")
    print(f"  4. Base label floors: {'PASS' if r4 else 'FAIL'}")

if __name__ == "__main__":
    run_probe()
