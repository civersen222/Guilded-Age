import gilded.chassis as ch
from gilded.society.realm import disloyal_shareholders

game = ch.GildedGame(seed=7)
for t in range(1, 13):
    for tk in game.takeovers:
        if tk.complete:
            continue
        tgt = game.realms.get(tk.target_house)
        sellers = disloyal_shareholders(tgt, game.enterprises) if tgt else []
        buyer_tre = game.houses[tk.buyer_house].treasury
        print(f"t{t} buyer={tk.buyer_house}({tk.buyer.name[:8]}) -> {tk.target_house} "
              f"buyerTreasury={buyer_tre:.0f} sellers={[c.name[:8] for c in sellers]}")
    print("---")
    game.end_turn()
