
"""Tests for gilded.society.schemes (mission G9)."""

import random

from gilded.enterprises import Enterprise
from gilded.chassis import GildedGame
from gilded.society.characters import Secret, SocietyState
from gilded.society.ideology import IdeologicalTide
from gilded.society.realm import create_house_realm
from gilded.society.schemes import (
    Conspiracy,
    SchemeManager,
    Takeover,
    share_price,
    blackmail,
    compromise,
    expose_secret,
    sabotage,
    seduce,
    start_conspiracy,
    sway,
)


class SeqRng:
    """Deterministic roll source: pops scripted values, then 0.99 forever."""

    def __init__(self, vals):
        self.vals = list(vals)

    def random(self):
        return self.vals.pop(0) if self.vals else 0.99


def _two_realms(seed):
    random.seed(seed)
    rng = random.Random(seed)
    society = SocietyState(rng)
    ra = create_house_realm("Vantrell", society)
    rb = create_house_realm("Karsgate", society)
    return ra, rb, {"Vantrell": ra, "Karsgate": rb}


def test_scheme_mechanics():
    ra, rb, realms = _two_realms(90)
    mgr = SchemeManager()
    agent = ra.characters[10]
    s = mgr.start_scheme(agent, rb.ruler, "assassination", "Karsgate")
    assert mgr.scheming(agent) and not mgr.scheming(rb.ruler)
    before = s.progress
    s.advance()
    assert s.progress == before + 3 + agent.get_effective_stat("intrigue") // 2
    s.add_participant(ra.characters[11])
    s.add_participant(ra.characters[11])            # dedupe
    s.add_participant(agent)                        # never the agent
    assert len(s.participants) == 1
    assert 0.0 <= s.success_chance(50) <= 0.9


def test_advance_all_prunes_moot_schemes():
    ra, rb, realms = _two_realms(91)
    mgr = SchemeManager()
    dead_agent = ra.characters[10]
    mgr.start_scheme(dead_agent, rb.ruler, "assassination", "Karsgate")
    dead_agent.is_alive = False
    not_ruler = rb.characters[12]
    mgr.start_scheme(ra.characters[11], not_ruler, "coup", "Karsgate")
    mgr.advance_all(realms, {}, SeqRng([0.99, 0.99]))
    assert mgr.schemes == []


def test_assassination_success_marks_succession():
    ra, rb, realms = _two_realms(92)
    mgr = SchemeManager()
    s = mgr.start_scheme(ra.characters[10], rb.ruler, "assassination", "Karsgate")
    s.progress = 99
    msgs = mgr.advance_all(realms, {}, SeqRng([0.99, 0.0]))
    assert not rb.ruler.is_alive
    assert ("ruler_dead", "Karsgate") in mgr.pending_successions
    assert msgs and mgr.schemes == []


def test_coup_success_seats_the_agent():
    ra, rb, realms = _two_realms(93)
    mgr = SchemeManager()
    old_ruler = rb.ruler
    agent = next(ch for ch in rb.court.positions.values() if ch is not None)
    s = mgr.start_scheme(agent, old_ruler, "coup", "Karsgate")
    s.progress = 99
    mgr.advance_all(realms, {}, SeqRng([0.99, 0.0]))
    assert rb.ruler is agent and rb.court.ruler is agent
    assert agent not in rb.court.positions.values()
    assert agent.id in rb.dynasty.all_characters
    assert mgr.pending_successions == []            # coup is its own succession


def test_discovery_shames_the_house():
    ra, rb, realms = _two_realms(94)
    mgr = SchemeManager()
    agent = ra.characters[10]
    mgr.start_scheme(agent, rb.ruler, "assassination", "Karsgate")
    legit = {"Vantrell": 50.0}
    msgs = mgr.advance_all(realms, legit, SeqRng([0.0]))
    assert legit["Vantrell"] < 50.0
    assert any(sec.kind == "scheme" for sec in agent.secrets)
    assert rb.ruler._society.opinions[(rb.ruler.id, agent.id)] <= -40
    assert agent.is_alive                           # cross-house: no execution
    assert msgs


def test_expose_secret_spends_the_leverage():
    ra, rb, realms = _two_realms(95)
    publisher, subject = ra.ruler, rb.ruler
    secret = Secret("affair", subject.id, f"{subject.name} hides an affair", 30)
    secret.holders.add(publisher.id)
    subject.secrets.append(secret)
    legit = {"Karsgate": 60.0}
    msgs = expose_secret(publisher, secret, subject, "Karsgate", legit)
    assert msgs and msgs[0].startswith("EXPOSED")
    assert legit["Karsgate"] < 60.0
    assert secret not in subject.secrets
    stranger = ra.characters[10]
    assert expose_secret(stranger, secret, subject, "Karsgate", legit) == []


def test_blackmail_extorts_shares():
    ra, rb, realms = _two_realms(96)
    agent, victim = ra.ruler, rb.ruler
    secret = Secret("compromise", victim.id, f"{victim.name} was compromised", 20)
    secret.holders.add(agent.id)
    ent = Enterprise(eid=1, kind="bank", name="K Bank", house="Karsgate", province=0)
    ent.ledger = {victim.id: 40.0}
    msgs = blackmail(agent, secret, victim, rb, [ent], SeqRng([0.99]))
    assert ent.ledger[agent.id] == 10.0
    assert ent.ledger[victim.id] == 30.0
    assert any("turns the screw" in m for m in msgs)
    bluff = blackmail(agent, secret, victim, rb, [ent], SeqRng([0.0]))
    assert any("calls the bluff" in m for m in bluff)


def test_sabotage_hits_the_rival_works():
    ra, rb, realms = _two_realms(97)

    class Province:
        name = "Karsholm"
        population = 50
        unrest = 0.0

    ent = Enterprise(eid=1, kind="mill", name="K Mill", house="Karsgate", province=0)
    tide = IdeologicalTide()
    msgs = sabotage(ra.ruler, ent, Province(), rb, SeqRng([0.0]), tide)
    assert any("mysterious accident" in m for m in msgs)
    assert tide.house_atrocities.get("Karsgate", 0.0) > 0
    assert any(sec.kind == "sabotage" for sec in ra.ruler.secrets)


def test_leverage_verbs():
    ra, rb, realms = _two_realms(98)
    a, t = ra.ruler, rb.ruler
    sway(a, t, SeqRng([0.0]))
    assert a._society.opinions[(t.id, a.id)] >= 15
    seduce(a, t, SeqRng([0.0]))
    assert any(sec.kind == "affair" for sec in t.secrets)
    compromise(a, t, SeqRng([0.0]))
    assert any(sec.kind == "compromise" for sec in t.secrets)
    legit = {"Vantrell": 50.0}
    msgs = compromise(a, t, SeqRng([0.99]), legitimacy=legit, agent_house="Vantrell")
    assert legit["Vantrell"] < 50.0 and any("fabricating" in m for m in msgs)


def test_takeover_buys_the_house_out():
    game = GildedGame(seed=99)
    for _ in range(3):
        game.end_turn()
    ra = game.realms["Vantrell"]
    rb = game.realms["Karsgate"]
    realms = game.realms
    buyer = ra.ruler
    buyer.gold_reserve = 1000.0
    seller = rb.characters[10]
    seller.loyalty = 10.0
    ent = Enterprise(eid=1, kind="bank", name="K Bank", house="Karsgate", province=0)
    ent.ledger = {seller.id: 80.0}
    tk = Takeover(buyer, "Vantrell", "Karsgate")
    ents = [ent]
    for _ in range(6):
        msgs = tk.advance(realms, ents, SeqRng([]), game)
        if tk.complete:
            break
    assert tk.complete
    assert ent.house == "Vantrell"
    assert ra.ruler.id in ent.ledger                # ledger re-carved for the buyer
    assert seller.gold_reserve > 0
    assert any("HOSTILE TAKEOVER" in m for m in msgs)
    assert tk.advance(realms, ents, SeqRng([]), game) == []


def test_conspiracy_staged_accident():
    ra, rb, realms = _two_realms(100)
    m = ra.ruler
    m.gold_reserve = 200.0
    assert start_conspiracy(m, rb.ruler, "Karsgate", ra.characters[5:6]) is None
    c = start_conspiracy(m, rb.ruler, "Karsgate", ra.characters[5:8])
    assert isinstance(c, Conspiracy) and m.gold_reserve == 100.0
    assert c.advance(realms, SeqRng([0.99] * 3)) == []
    assert c.advance(realms, SeqRng([0.99] * 3)) == []
    msgs = c.advance(realms, SeqRng([0.99, 0.99, 0.99, 0.5]))
    assert c.done and not c.exposed
    assert not rb.ruler.is_alive
    assert msgs


def test_conspiracy_exposure_is_nuclear():
    ra, rb, realms = _two_realms(101)
    m = ra.ruler
    m.gold_reserve = 200.0
    c = start_conspiracy(m, rb.ruler, "Karsgate", ra.characters[5:8])
    tide = IdeologicalTide()
    legit = {"Vantrell": 70.0}
    msgs = c.advance(realms, SeqRng([0.0, 0.0]), tide, legit)
    assert c.exposed and c.done
    assert legit["Vantrell"] < 70.0
    assert tide.house_atrocities.get("Vantrell", 0.0) > 0
    assert rb.ruler._society.opinions[(rb.ruler.id, m.id)] <= -60
    assert not m.is_alive                           # execution roll came up
    assert any("loses their nerve" in m_ for m_ in msgs)
# --- L3.5: share_price tests ---

def test_share_price_positive_floor():
    """An enterprise the market values at 0 still costs > 0 per percent."""
    game = GildedGame(seed=42)
    for _ in range(3):
        game.end_turn()
    worthless = [e for e in game.enterprises if game.market.value(e, game) == 0.0][0]
    p = share_price(worthless, game)
    assert p > 0.0

def test_share_price_rises_in_boom():
    """Raising the commodity price raises the share price."""
    game = GildedGame(seed=42)
    for _ in range(3):
        game.end_turn()
    from gilded.market import PRODUCES
    e = max([e for e in game.enterprises if game.market.value(e, game) > 0],
            key=lambda e: game.market.value(e, game))
    commodity = PRODUCES.get(e.kind)
    game.market.prices[commodity] = 0.5
    cheap = share_price(e, game)
    game.market.prices[commodity] = 4.0
    dear = share_price(e, game)
    assert dear > cheap

def test_share_price_bounded():
    """share_price stays within [TAKEOVER_PRICE * 0.25, TAKEOVER_PRICE * 4.0]."""
    game = GildedGame(seed=42)
    for _ in range(3):
        game.end_turn()
    lo = 0.5
    hi = 8.0
    prices = [share_price(e, game) for e in game.enterprises]
    assert all(lo - 1e-9 <= p <= hi + 1e-9 for p in prices)

def test_share_price_both_sides_of_base():
    """Some ventures price above 2.0, some below, in a normal market."""
    game = GildedGame(seed=42)
    for _ in range(3):
        game.end_turn()
    prices = [share_price(e, game) for e in game.enterprises]
    above = [p for p in prices if p > 2.0 + 1e-9]
    below = [p for p in prices if p < 2.0 - 1e-9]
    assert above, "no venture prices above the base rate"
    assert below, "no venture prices below the base rate"

def test_advance_uses_game_not_flat_rate():
    """advance() requires a game argument and charges the priced rate."""
    game = GildedGame(seed=42)
    for _ in range(4):
        game.end_turn()
    target_house = sorted(game.houses)[0]
    buyer_house = sorted(game.houses)[1]
    buyer = game.realms[buyer_house].ruler
    house = game.houses[buyer_house]
    house.treasury = 1000.0
    gold_before = house.treasury
    tk = Takeover(buyer, buyer_house, target_house)
    target_ents = [e for e in game.enterprises if e.house == target_house]
    assert len(target_ents) >= 1, f"Expected at least one enterprise for {target_house}"
    tk.advance(game.realms, target_ents, SeqRng([]), game)
    # advance charges the priced rate — buyer should have spent gold
    assert house.treasury < gold_before, \
        f"Treasury unchanged ({gold_before}): advance should charge the priced rate"


def test_sway_base_chance():
    """sway base chance = 0.60: statecraft 0 agent succeeds on roll 0.59, fails on roll 0.61."""
    ra, rb, realms = _two_realms(42)
    agent = ra.characters[10]
    agent.base_stats["statecraft"] = 0
    offset = agent.get_effective_stat("statecraft")
    agent.base_stats["statecraft"] = 0 - offset
    # roll 0.59 < 0.60 base → must succeed (catches SWAY_BASE→0.5)
    msgs = sway(agent, rb.ruler, SeqRng([0.59]))
    assert not any("sees through" in m for m in msgs)
    # roll 0.61 > 0.60 base → must fail
    msgs = sway(agent, rb.ruler, SeqRng([0.61]))
    assert any("sees through" in m for m in msgs)


def test_sway_coefficient():
    """sway coefficient = 0.01 per statecraft: statecraft 20 chance=0.80 succeeds on roll 0.75, fails on 0.81."""
    ra, rb, realms = _two_realms(42)
    agent = ra.characters[10]
    agent.base_stats["statecraft"] = 0
    offset = agent.get_effective_stat("statecraft")
    agent.base_stats["statecraft"] = 20 - offset
    # roll 0.75 < 0.80 (0.60 + 20*0.01) → must succeed
    # If coeff→0.005: chance=0.60+20*0.005=0.70, roll 0.75>0.70 → fails (caught)
    # If coeff→0.02: chance=0.60+20*0.02=1.00→capped 0.95, roll 0.75<0.95 → succeeds (not caught here)
    msgs = sway(agent, rb.ruler, SeqRng([0.75]))
    assert not any("sees through" in m for m in msgs)
    # roll 0.81 > 0.80 → must fail
    # If coeff→0.02: chance=1.00→capped 0.95, roll 0.81<0.95 → succeeds (caught)
    msgs = sway(agent, rb.ruler, SeqRng([0.81]))
    assert any("sees through" in m for m in msgs)


def test_sway_cap():
    """sway cap = 0.95: statecraft 40 chance=0.95 succeeds on roll 0.94."""
    ra, rb, realms = _two_realms(42)
    agent = ra.characters[10]
    agent.base_stats["statecraft"] = 0
    offset = agent.get_effective_stat("statecraft")
    agent.base_stats["statecraft"] = 40 - offset
    # roll 0.94 < 0.95 cap → must succeed (catches CAP→0.90)
    msgs = sway(agent, rb.ruler, SeqRng([0.94]))
    assert not any("sees through" in m for m in msgs)
    # roll 0.96 > 0.95 cap → must fail
    msgs = sway(agent, rb.ruler, SeqRng([0.96]))
    assert any("sees through" in m for m in msgs)


def test_sway_penalty():
    """failed sway costs exactly 5 opinion."""
    ra, rb, realms = _two_realms(42)
    agent = ra.characters[10]
    agent.base_stats["statecraft"] = 0
    offset = agent.get_effective_stat("statecraft")
    agent.base_stats["statecraft"] = 0 - offset
    target = rb.ruler
    before = target._society.opinions.get((target.id, agent.id), 0)
    sway(agent, target, SeqRng([0.70]))
    after = target._society.opinions.get((target.id, agent.id), 0)
    assert after - before == -5


# ---------------------------------------------------------------- I4c1 (FIND-4)
# A takeover campaign is House business and spends the House treasury.
#
# Before this wave, Takeover.advance funded itself from self.buyer.gold_reserve
# -- one person's purse. The buyer is whoever _executor_for picks for the
# "capital" domain, and that person is chosen by STAT, never by wealth: measured
# 0.00 gold in 20/20 seeds, and at turn 21 only 3-7 of 61-84 living kin per
# house hold any gold at all. Ten campaigns started through the real initiative
# path moved 0.0% of shares over 20 turns each while the House treasury held
# 419 to 17,443 gold. Every OTHER spending verb -- charter, expansion, railway,
# buyoff, allowance, compensation -- checks and debits house.treasury.
#
# Fixture: seed 47 at turn 2 is the smallest tree that discriminates. Ashworth's
# capital executor is Ashoka Ashworth holding exactly 0.0 gold, the treasury
# holds 2381.98, and House Vantrell has exactly one disloyal shareholder
# (Alexios Vantrell, 20.0% of Yarehaven Ironworks).

I4C1_BUYER_HOUSE = "Ashworth"
I4C1_TARGET_HOUSE = "Vantrell"


def _i4c1_fixture():
    """seed 47, turn 2 -> (game, capital executor of Ashworth).

    Asserts its own premises, so a test built on it can never pass or fail for
    a reason that lives in the fixture rather than in the code under test.
    """
    from gilded.ai import _executor_for
    from gilded.docket import INITIATIVES
    from gilded.society.realm import disloyal_shareholders

    game = GildedGame(seed=47)
    for _ in range(2):
        game.end_turn()
    realm = game.realms[I4C1_BUYER_HOUSE]
    executor = _executor_for(game, realm, INITIATIVES["start_takeover"][0])
    assert executor.gold_reserve == 0.0, (
        f"premise: the capital executor {executor.name} must hold no gold of "
        f"their own, else a treasury test could pass on purse money "
        f"(holds {executor.gold_reserve})")
    assert game.houses[I4C1_BUYER_HOUSE].treasury > 100.0, (
        f"premise: the buying House must be able to afford shares "
        f"(treasury {game.houses[I4C1_BUYER_HOUSE].treasury})")
    sellers = disloyal_shareholders(game.realms[I4C1_TARGET_HOUSE],
                                    game.enterprises)
    assert len(sellers) == 1, (
        f"premise: the target must have exactly one disloyal shareholder for "
        f"the arithmetic below to be single-sourced (has {len(sellers)})")
    return game, executor


def _i4c1_target_ents(game):
    return [e for e in game.enterprises if e.house == I4C1_TARGET_HOUSE]


def test_the_takeover_campaign_spends_the_house_treasury():
    """FIND-4: the House pays, and the executor's own purse is not touched."""
    from gilded.society.shares import house_stake

    game, executor = _i4c1_fixture()
    house = game.houses[I4C1_BUYER_HOUSE]
    treasury_before = house.treasury
    ents = _i4c1_target_ents(game)

    Takeover(executor, I4C1_BUYER_HOUSE,
             I4C1_TARGET_HOUSE).advance(game.realms, game.enterprises,
                                        game.rng, game)

    assert house_stake(ents, executor.id) > 0.0, (
        "one turn of quiet buying moved no shares at all")
    assert house.treasury < treasury_before, (
        f"the House treasury did not pay for the shares "
        f"({treasury_before} -> {house.treasury})")
    assert executor.gold_reserve == 0.0, (
        f"the executor's own purse was charged ({executor.gold_reserve}); "
        f"a takeover is House business")


def test_a_rich_person_cannot_fund_a_takeover_from_an_empty_treasury():
    """The mirror of the rule: personal wealth is not House money.

    Without this, an implementation that reads EITHER purse or treasury would
    satisfy every other test in this block.
    """
    from gilded.society.shares import house_stake

    game, executor = _i4c1_fixture()
    executor.gold_reserve = 10000.0
    game.houses[I4C1_BUYER_HOUSE].treasury = 0.0
    ents = _i4c1_target_ents(game)

    msgs = Takeover(executor, I4C1_BUYER_HOUSE,
                    I4C1_TARGET_HOUSE).advance(game.realms, game.enterprises,
                                               game.rng, game)

    assert house_stake(ents, executor.id) == 0.0, (
        "a broke House bought shares out of a courtier's private fortune")
    assert executor.gold_reserve == 10000.0, (
        f"the private fortune was spent ({executor.gold_reserve})")
    assert msgs == [], f"a campaign that bought nothing still spoke: {msgs}"


def test_the_seller_is_paid_exactly_what_the_treasury_lost():
    """Gold conserves across the sale: the disloyal holder pockets the lot."""
    from gilded.society.realm import disloyal_shareholders

    game, executor = _i4c1_fixture()
    house = game.houses[I4C1_BUYER_HOUSE]
    seller = disloyal_shareholders(game.realms[I4C1_TARGET_HOUSE],
                                   game.enterprises)[0]
    treasury_before = house.treasury
    seller_before = seller.gold_reserve

    Takeover(executor, I4C1_BUYER_HOUSE,
             I4C1_TARGET_HOUSE).advance(game.realms, game.enterprises,
                                        game.rng, game)

    spent = treasury_before - house.treasury
    gained = seller.gold_reserve - seller_before
    assert spent > 0.0, "the treasury spent nothing"
    assert abs(spent - gained) < 1e-9, (
        f"the House spent {spent} but the seller received {gained}")


def test_the_house_pays_the_market_rate_for_the_shares_it_gets():
    """Conservation is not enough: the RATE has to be the priced one.

    A campaign that pays half of share_price still conserves gold between the
    treasury and the seller and still moves shares, so every other test in this
    block passes while the House quietly buys a rival at a discount.
    """
    from gilded.society.schemes import share_price

    game, executor = _i4c1_fixture()
    house = game.houses[I4C1_BUYER_HOUSE]
    ents = _i4c1_target_ents(game)
    held_before = {e.eid: e.ledger.get(executor.id, 0.0) for e in ents}
    treasury_before = house.treasury

    Takeover(executor, I4C1_BUYER_HOUSE,
             I4C1_TARGET_HOUSE).advance(game.realms, game.enterprises,
                                        game.rng, game)

    expected = sum((e.ledger.get(executor.id, 0.0) - held_before[e.eid])
                   * share_price(e, game) for e in ents)
    assert expected > 0.0, "no shares changed hands"
    spent = treasury_before - house.treasury
    assert abs(spent - expected) < 1e-9, (
        f"the House paid {spent} for shares priced at {expected}")


def test_the_share_purchase_is_journalled_as_a_treasury_debit():
    """The spend goes through House.debit, so the ledger screen can show it.

    An implementation that assigns house.treasury directly would pass every
    test above and leave the player's own accounts silently wrong.
    """
    game, executor = _i4c1_fixture()
    house = game.houses[I4C1_BUYER_HOUSE]
    before = len(house.journal)
    treasury_before = house.treasury

    Takeover(executor, I4C1_BUYER_HOUSE,
             I4C1_TARGET_HOUSE).advance(game.realms, game.enterprises,
                                        game.rng, game)

    added = house.journal[before:]
    assert len(added) == 1, f"expected one journal entry, got {added}"
    turn, label, amount = added[0]
    assert label == "share purchase", f"journalled under {label!r}"
    assert amount < 0.0, f"a purchase was journalled as a credit ({amount})"
    assert abs(amount + (treasury_before - house.treasury)) < 1e-9, (
        f"the journal says {amount} but the treasury moved "
        f"{house.treasury - treasury_before}")


def test_a_thin_treasury_does_not_crash_the_campaign():
    """House.debit RAISES on an overdraft, and floating point overdraws.

    treasury=0.09 is a measured case: the tranche the House can afford costs
    0.09000000000000001 when multiplied back out, one ulp over the balance.
    The campaign must still buy what it can and leave the treasury at or above
    zero, not take the whole game down with a ValueError mid-turn.
    """
    from gilded.society.shares import house_stake

    game, executor = _i4c1_fixture()
    house = game.houses[I4C1_BUYER_HOUSE]
    house.treasury = 0.09
    ents = _i4c1_target_ents(game)

    Takeover(executor, I4C1_BUYER_HOUSE,
             I4C1_TARGET_HOUSE).advance(game.realms, game.enterprises,
                                        game.rng, game)

    assert house_stake(ents, executor.id) > 0.0, (
        "0.09 gold bought no shares at all")
    assert house.treasury >= 0.0, (
        f"the House ended the purchase overdrawn ({house.treasury})")


def test_a_started_campaign_actually_moves_shares():
    """The whole wired path: initiative -> chassis -> advance.

    This is the FIND-4 regression. On the code this wave replaces, this exact
    fixture held 0.0% after both turns, forever, and the player's only feedback
    was the one line of prose the initiative printed on the turn they clicked.
    """
    from gilded.docket import initiative
    from gilded.society.shares import house_stake

    def mine():
        return [t for t in game.takeovers
                if t.buyer_house == I4C1_BUYER_HOUSE
                and t.target_house == I4C1_TARGET_HOUSE]

    game, executor = _i4c1_fixture()
    assert mine() == [], (
        "premise: no Ashworth campaign against Vantrell may already be running, "
        "or the click under test is not the one being measured")
    initiative(game, I4C1_BUYER_HOUSE, "start_takeover", executor,
               target_house=I4C1_TARGET_HOUSE)
    assert len(mine()) == 1, (
        f"the click registered {len(mine())} campaigns of its own")

    game.end_turn()
    game.end_turn()

    ents = _i4c1_target_ents(game)
    assert house_stake(ents, executor.id) > 0.0, (
        "two turns of a running campaign bought nothing the player can see")
    assert executor.gold_reserve == 0.0, (
        f"the campaign charged the executor personally "
        f"({executor.gold_reserve})")
