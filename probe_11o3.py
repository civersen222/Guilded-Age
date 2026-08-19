import gilded.chassis as ch

game = ch.GildedGame(seed=7)
for t in range(1, 13):
    for h in ("Ashworth", "Karsgate"):
        r = game.realms[h]
        if r is None:
            continue
        ruler = r.ruler
        parts = []
        for c in r.characters:
            if not c.is_alive or c.id == ruler.id:
                continue
            stake = sum(e.ledger.get(c.id, 0.0) for e in game.enterprises if e.house == h)
            if stake <= 0:
                continue
            loy = getattr(c, "loyalty", None)
            op = c._society.opinions.get((c.id, ruler.id), 0)
            parts.append(f"{c.name[:6]}{stake:.0f}% o={op:+.0f} l={loy if loy is None else round(loy)}")
        print(f"t{t} {h}: " + " ".join(parts))
    game.end_turn()
