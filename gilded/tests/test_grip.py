"""Stage 4 L2 — Grip on the House (gilded/grip.py).

THIS FILE IS THE CONTRACT for the new module `gilded/grip.py`.

grip.py is a PURE READ-MODEL in the shape of gilded/intel.py: it derives the
master tension of Stage 4 — your effective controlling stake in your own
House, measured against the buyout threshold at which a rival seizes it —
from state that already exists. It MUST NOT mutate the game, MUST NOT touch
game.rng, and MUST NOT run any new simulation.

Vocabulary pinned here:

  loyal bloc        the ruler, plus every LIVING character of the ruler's own
                    realm who holds shares in a House enterprise and is NOT in
                    realm.disloyal_shareholders(). (Directors and courtiers who
                    hold a shares salary count; the test is exactly the one in
                    gilded/society/realm.py.)
  controlling stake the portfolio-wide effective stake of that bloc, on the
                    same 0-100 scale the Takeover yardstick uses: for one
                    holder it is shares.house_stake(house_ents, id) — the mean
                    stake across every enterprise of the House — and the bloc's
                    figure is the sum of its members' figures.
  predator          the single strongest holder who is NOT in the loyal bloc,
                    by that same portfolio-wide measure. That includes a
                    disloyal sibling AND a foreign buyer whose id appears in a
                    ledger but in no realm.
  margin            controlling_stake - TAKEOVER_THRESHOLD (from
                    gilded.society.schemes; 50.0).

BAND CUT-POINTS (the spec — chosen off the margin, so the bands are stated in
the sim's own units and stay monotone in the controlling stake). With
GRIP_BAND_MARGIN = 15.0:

    margin >= +15.0            IRON_GRIP   stake >= 65.0  unassailable
    0.0 <= margin <  +15.0     CONTESTED   50.0..65.0     above the bar, but a
                                                          single defection or
                                                          one bought tranche
                                                          puts it in play
    -15.0 <= margin < 0.0      IMPERILED   35.0..50.0     below the bar; a
                                                          rival who consolidates
                                                          can clear it
    margin < -15.0             SEIZED      < 35.0         control has left your
                                                          hands in all but name

Rationale: TAKEOVER_THRESHOLD is the only cut-point the simulation itself
enforces, so it must be a band edge. One TAKEOVER_TRANCHE-sized band either
side of it (15.0 == schemes.TAKEOVER_TRANCHE, the most a predator can buy per
enterprise per seller per turn) makes CONTESTED mean "one turn of quiet buying
from taking you under" and IMPERILED mean "one turn of buying back from safe".

DIVIDEND: there is no stored per-enterprise dividend anywhere in the codebase —
chassis.end_turn recomputes it each turn inside its dividend loop and pays it
straight into holders. So EnterpriseLine.dividend is a RECOMPUTED, NON-MUTATING
estimate of the gross pool this enterprise would pay out this turn: the same
output_gold * dividend_multiplier(dial) stack the chassis uses, with the market
threaded in as an output multiplier and an input cost, floored at 0.0. It is
the WHOLE pool, not the ruler's cut — a caller reads your slice as
line.dividend * line.your_stake / 100. Turn-order effects the chassis applies
(strike output, standing policy) are deliberately NOT included: game.policy
does not even exist before the first end_turn.

Every test below builds its own state. Scenarios that need a disloyal holder or
a predator over the threshold construct that state explicitly by editing a
ledger or a loyalty — never by hoping a seed provides it.
"""

import pytest

import gilded.grip as grip
from gilded.chassis import GildedGame
from gilded.market import PRODUCES
from gilded.society.realm import disloyal_shareholders
from gilded.society.schemes import TAKEOVER_THRESHOLD
from gilded.society.shares import house_stake


# --- helpers ---------------------------------------------------------------

def _game(seed=7):
    return GildedGame(seed)


def _first_house(g):
    return sorted(g.houses)[0]


def _line(rep, eid):
    for line in rep.enterprises:
        if line.eid == eid:
            return line
    raise AssertionError(f"no EnterpriseLine for eid {eid}")


def _kin(realm, n=1):
    """n living characters of the realm who are not the ruler."""
    out = [c for c in realm.characters
           if c.is_alive and c.id != realm.ruler.id][:n]
    assert len(out) == n, "realm has too few living characters for this test"
    return out


def _snapshot(g):
    """Everything report() could plausibly damage."""
    return {
        "ledgers": {e.eid: dict(e.ledger) for e in g.enterprises},
        "directors": {e.eid: e.director_id for e in g.enterprises},
        "tiers": {e.eid: (e.tier, e.under_construction) for e in g.enterprises},
        "dials": {e.eid: e.extraction_dial for e in g.enterprises},
        "gold": {c.id: c.gold_reserve
                 for r in g.realms.values() for c in r.characters},
        "loyalty": {c.id: getattr(c, "loyalty", None)
                    for r in g.realms.values() for c in r.characters},
        "opinions": dict(g.society.opinions),
        "prices": dict(g.market.prices),
        "treasury": {h: g.houses[h].treasury for h in g.houses},
        "turn": g.turn,
        "rng": g.rng.getstate(),
    }


# --- module surface --------------------------------------------------------

def test_module_exposes_the_band_vocabulary():
    assert grip.BAND_IRON_GRIP == "IRON_GRIP"
    assert grip.BAND_CONTESTED == "CONTESTED"
    assert grip.BAND_IMPERILED == "IMPERILED"
    assert grip.BAND_SEIZED == "SEIZED"
    # BANDS is ordered weakest-grip first, so BANDS.index() is a strength rank.
    assert grip.BANDS == (grip.BAND_SEIZED, grip.BAND_IMPERILED,
                          grip.BAND_CONTESTED, grip.BAND_IRON_GRIP)
    assert grip.GRIP_BAND_MARGIN == 15.0


def test_band_for_cut_points_are_exact():
    assert grip.band_for(100.0) == grip.BAND_IRON_GRIP
    assert grip.band_for(65.0) == grip.BAND_IRON_GRIP
    assert grip.band_for(64.99) == grip.BAND_CONTESTED
    assert grip.band_for(50.0) == grip.BAND_CONTESTED
    assert grip.band_for(49.99) == grip.BAND_IMPERILED
    assert grip.band_for(35.0) == grip.BAND_IMPERILED
    assert grip.band_for(34.99) == grip.BAND_SEIZED
    assert grip.band_for(0.0) == grip.BAND_SEIZED


def test_band_for_is_monotonic_in_stake():
    ranks = [grip.BANDS.index(grip.band_for(x / 2.0)) for x in range(0, 201)]
    assert ranks == sorted(ranks)
    assert set(grip.BANDS) == set(grip.band_for(x / 2.0) for x in range(0, 201))


def test_threshold_is_the_takeover_threshold():
    g = _game()
    rep = grip.report(g, _first_house(g))
    assert rep.threshold == TAKEOVER_THRESHOLD


# --- report shape ----------------------------------------------------------

def test_report_has_one_line_per_house_enterprise():
    g = _game()
    for h in sorted(g.houses):
        rep = grip.report(g, h)
        assert isinstance(rep, grip.GripReport)
        assert rep.house == h
        assert isinstance(rep.enterprises, tuple)
        assert ([l.eid for l in rep.enterprises]
                == [e.eid for e in g.ents_of(h)])


def test_report_lines_are_frozen_records_with_the_pinned_fields():
    g = _game()
    h = _first_house(g)
    rep = grip.report(g, h)
    line = rep.enterprises[0]
    assert isinstance(line, grip.EnterpriseLine)
    for field in ("eid", "name", "sector", "tier", "dividend",
                  "director", "your_stake", "top_outside"):
        assert hasattr(line, field), field
    with pytest.raises(Exception):
        line.tier = 99                      # frozen dataclass
    with pytest.raises(Exception):
        rep.band = "NOPE"


def test_report_top_level_fields():
    g = _game()
    rep = grip.report(g, _first_house(g))
    assert isinstance(rep.loyal_bloc, tuple)
    assert isinstance(rep.controlling_stake, float)
    assert isinstance(rep.margin, float)
    assert rep.band in grip.BANDS
    assert rep.top_predator is None or isinstance(rep.top_predator,
                                                  grip.Holder)
    assert 0.0 <= rep.controlling_stake <= 100.0 + 1e-9
    assert abs(rep.margin - (rep.controlling_stake - rep.threshold)) < 1e-9
    assert rep.band == grip.band_for(rep.controlling_stake)


def test_line_name_and_tier_mirror_the_enterprise():
    g = _game()
    h = _first_house(g)
    rep = grip.report(g, h)
    for ent in g.ents_of(h):
        line = _line(rep, ent.eid)
        assert line.name == ent.name
        assert line.tier == ent.tier


def test_sector_is_the_produced_commodity_and_bank_for_banks():
    g = _game()
    for h in sorted(g.houses):
        rep = grip.report(g, h)
        for ent in g.ents_of(h):
            line = _line(rep, ent.eid)
            expected = PRODUCES.get(ent.kind) or "bank"
            assert line.sector == expected
        for line in rep.enterprises:
            assert line.sector in ("coal", "steel", "freight", "farm", "bank")


def test_your_stake_is_the_rulers_ledger_pct_in_that_one_enterprise():
    g = _game()
    h = _first_house(g)
    ruler = g.realms[h].ruler
    ents = g.ents_of(h)
    ents[0].ledger[ruler.id] = 41.5
    rep = grip.report(g, h)
    assert abs(_line(rep, ents[0].eid).your_stake - 41.5) < 1e-9
    for ent in ents[1:]:
        assert abs(_line(rep, ent.eid).your_stake
                   - ent.ledger.get(ruler.id, 0.0)) < 1e-9


# --- the loyal bloc and the controlling stake ------------------------------

def test_bloc_members_are_holders_and_carry_a_portfolio_stake():
    g = _game()
    h = _first_house(g)
    ents = g.ents_of(h)
    rep = grip.report(g, h)
    assert rep.loyal_bloc, "a fresh House holds its own shares"
    ids = [m.id for m in rep.loyal_bloc]
    assert len(ids) == len(set(ids))
    assert g.realms[h].ruler.id in ids
    by_id = {c.id: c for c in g.realms[h].characters}
    for m in rep.loyal_bloc:
        assert isinstance(m, grip.Holder)
        assert m.name == by_id[m.id].name
        assert abs(m.stake - house_stake(ents, m.id)) < 1e-9
        assert m.stake > 0.0


def test_controlling_stake_is_the_sum_of_the_blocs_stakes():
    g = _game()
    for h in sorted(g.houses):
        rep = grip.report(g, h)
        assert abs(rep.controlling_stake
                   - sum(m.stake for m in rep.loyal_bloc)) < 1e-6


def test_an_undivided_house_holds_the_whole_portfolio():
    g = _game()
    h = _first_house(g)
    realm = g.realms[h]
    assert disloyal_shareholders(realm, g.enterprises) == []
    rep = grip.report(g, h)
    assert abs(rep.controlling_stake - 100.0) < 1e-6
    assert rep.band == grip.BAND_IRON_GRIP
    assert rep.top_predator is None
    for line in rep.enterprises:
        assert line.top_outside is None


def test_a_disloyal_kinsman_leaves_the_bloc_and_becomes_the_predator():
    g = _game()
    h = _first_house(g)
    realm = g.realms[h]
    ruler = realm.ruler
    (kin,) = _kin(realm, 1)
    for ent in g.ents_of(h):
        ent.ledger.clear()
        ent.ledger[ruler.id] = 30.0
        ent.ledger[kin.id] = 70.0

    kin.loyalty = 90.0                      # loyal: the bloc still holds it all
    loyal = grip.report(g, h)
    assert abs(loyal.controlling_stake - 100.0) < 1e-6
    assert loyal.top_predator is None
    assert loyal.band == grip.BAND_IRON_GRIP

    kin.loyalty = 5.0                       # disloyal by loyalty
    torn = grip.report(g, h)
    assert kin.id not in [m.id for m in torn.loyal_bloc]
    assert abs(torn.controlling_stake - 30.0) < 1e-6
    assert abs(torn.margin - (30.0 - TAKEOVER_THRESHOLD)) < 1e-9
    assert torn.band == grip.BAND_SEIZED
    assert torn.top_predator is not None
    assert torn.top_predator.id == kin.id
    assert torn.top_predator.name == kin.name
    assert abs(torn.top_predator.stake - 70.0) < 1e-6


def test_a_grudge_alone_makes_a_holder_disloyal():
    """realm.DISLOYAL_OPINION: opinion of the ruler at or below -20."""
    from gilded.society.characters import modify_opinion
    g = _game()
    h = _first_house(g)
    realm = g.realms[h]
    ruler = realm.ruler
    (kin,) = _kin(realm, 1)
    for ent in g.ents_of(h):
        ent.ledger.clear()
        ent.ledger[ruler.id] = 55.0
        ent.ledger[kin.id] = 45.0
    kin.loyalty = 99.0                      # loyalty is fine...
    assert abs(grip.report(g, h).controlling_stake - 100.0) < 1e-6
    modify_opinion(kin, ruler, -60, "denied the throne")   # ...the grudge is not
    rep = grip.report(g, h)
    assert kin.id not in [m.id for m in rep.loyal_bloc]
    assert abs(rep.controlling_stake - 55.0) < 1e-6
    assert rep.band == grip.BAND_CONTESTED


def test_a_foreign_buyer_in_the_ledger_is_a_predator_even_with_no_realm():
    g = _game()
    h = _first_house(g)
    ruler = g.realms[h].ruler
    for ent in g.ents_of(h):
        ent.ledger.clear()
        ent.ledger[ruler.id] = 40.0
        ent.ledger["OUTSIDER"] = 60.0
    rep = grip.report(g, h)
    assert [m.id for m in rep.loyal_bloc] == [ruler.id]
    assert abs(rep.controlling_stake - 40.0) < 1e-6
    assert rep.band == grip.BAND_IMPERILED
    assert rep.top_predator is not None
    assert rep.top_predator.id == "OUTSIDER"
    assert abs(rep.top_predator.stake - 60.0) < 1e-6
    # an unknown holder still gets a printable name
    assert isinstance(rep.top_predator.name, str) and rep.top_predator.name


def test_a_dead_holders_stake_is_neither_yours_nor_a_predators():
    """Dead kin hold inert paper until succession partitions it: it is not in
    your bloc, and a corpse is not a predator."""
    g = _game()
    h = _first_house(g)
    realm = g.realms[h]
    ruler = realm.ruler
    (kin,) = _kin(realm, 1)
    for ent in g.ents_of(h):
        ent.ledger.clear()
        ent.ledger[ruler.id] = 60.0
        ent.ledger[kin.id] = 40.0
    kin.is_alive = False
    rep = grip.report(g, h)
    assert [m.id for m in rep.loyal_bloc] == [ruler.id]
    assert abs(rep.controlling_stake - 60.0) < 1e-6
    assert rep.top_predator is None
    for line in rep.enterprises:
        assert line.top_outside is None


def test_the_predator_is_the_strongest_outsider_not_merely_an_outsider():
    g = _game()
    h = _first_house(g)
    ruler = g.realms[h].ruler
    for ent in g.ents_of(h):
        ent.ledger.clear()
        ent.ledger[ruler.id] = 30.0
        ent.ledger["SMALL_FISH"] = 25.0
        ent.ledger["BIG_FISH"] = 45.0
    rep = grip.report(g, h)
    assert rep.top_predator.id == "BIG_FISH"
    assert abs(rep.top_predator.stake - 45.0) < 1e-6


def test_bands_walk_down_as_the_predator_buys_in():
    """The whole point of the meter: bands degrade monotonically."""
    g = _game()
    h = _first_house(g)
    ruler = g.realms[h].ruler
    seen = []
    for mine in (80.0, 60.0, 45.0, 20.0):
        for ent in g.ents_of(h):
            ent.ledger.clear()
            ent.ledger[ruler.id] = mine
            ent.ledger["RIVAL"] = 100.0 - mine
        rep = grip.report(g, h)
        assert abs(rep.controlling_stake - mine) < 1e-6
        seen.append(rep.band)
    assert seen == [grip.BAND_IRON_GRIP, grip.BAND_CONTESTED,
                    grip.BAND_IMPERILED, grip.BAND_SEIZED]


# --- per-enterprise top_outside -------------------------------------------

def test_top_outside_names_the_largest_non_bloc_holder_of_that_enterprise():
    g = _game()
    h = _first_house(g)
    realm = g.realms[h]
    ruler = realm.ruler
    loyal_kin, angry_kin = _kin(realm, 2)
    loyal_kin.loyalty = 95.0
    angry_kin.loyalty = 1.0
    ents = g.ents_of(h)
    for ent in ents:
        ent.ledger.clear()
        ent.ledger[ruler.id] = 30.0
        ent.ledger[loyal_kin.id] = 20.0     # in the bloc: never "outside"
        ent.ledger[angry_kin.id] = 50.0
    rep = grip.report(g, h)
    for ent in ents:
        line = _line(rep, ent.eid)
        assert line.top_outside == (angry_kin.id, 50.0)


def test_top_outside_is_none_when_the_bloc_owns_the_enterprise_outright():
    g = _game()
    h = _first_house(g)
    ruler = g.realms[h].ruler
    ent = g.ents_of(h)[0]
    ent.ledger.clear()
    ent.ledger[ruler.id] = 100.0
    assert _line(grip.report(g, h), ent.eid).top_outside is None


def test_top_outside_is_per_enterprise_not_portfolio_wide():
    g = _game()
    h = _first_house(g)
    ruler = g.realms[h].ruler
    ents = g.ents_of(h)
    assert len(ents) >= 2, "seed 7's first House needs two ventures"
    ents[0].ledger.clear()
    ents[0].ledger.update({ruler.id: 100.0})
    ents[1].ledger.clear()
    ents[1].ledger.update({ruler.id: 40.0, "RAIDER": 60.0})
    rep = grip.report(g, h)
    assert _line(rep, ents[0].eid).top_outside is None
    assert _line(rep, ents[1].eid).top_outside == ("RAIDER", 60.0)


# --- the director record ---------------------------------------------------

def test_director_is_none_when_the_seat_is_empty():
    g = _game()
    h = _first_house(g)
    ent = g.ents_of(h)[0]
    ent.director_id = ""
    assert _line(grip.report(g, h), ent.eid).director is None


def test_director_carries_id_name_industry_and_the_disloyalty_flag():
    g = _game()
    h = _first_house(g)
    realm = g.realms[h]
    ruler = realm.ruler
    (d,) = _kin(realm, 1)
    ent = g.ents_of(h)[0]
    ent.director_id = d.id
    ent.ledger.clear()
    ent.ledger[ruler.id] = 70.0
    ent.ledger[d.id] = 30.0

    d.loyalty = 95.0
    line = _line(grip.report(g, h), ent.eid)
    assert isinstance(line.director, grip.Director)
    assert line.director.id == d.id
    assert line.director.name == d.name
    assert line.director.industry == d.get_effective_stat("industry")
    assert line.director.disloyal is False
    with pytest.raises(Exception):
        line.director.disloyal = True       # frozen

    d.loyalty = 2.0
    assert _line(grip.report(g, h), ent.eid).director.disloyal is True


def test_director_disloyalty_uses_the_realm_test_exactly():
    g = _game()
    h = _first_house(g)
    realm = g.realms[h]
    (d,) = _kin(realm, 1)
    ent = g.ents_of(h)[0]
    ent.director_id = d.id
    d.loyalty = 2.0
    # ...but the director holds NO shares, so realm.disloyal_shareholders
    # does not list them, and neither may grip.
    for e in g.ents_of(h):
        e.ledger.pop(d.id, None)
    assert d not in disloyal_shareholders(realm, g.enterprises)
    assert _line(grip.report(g, h), ent.eid).director.disloyal is False


def test_a_dead_director_is_not_reported():
    g = _game()
    h = _first_house(g)
    realm = g.realms[h]
    (d,) = _kin(realm, 1)
    ent = g.ents_of(h)[0]
    ent.director_id = d.id
    assert _line(grip.report(g, h), ent.eid).director is not None
    d.is_alive = False
    assert _line(grip.report(g, h), ent.eid).director is None


# --- the dividend estimate -------------------------------------------------

def _first_earning(g):
    for h in sorted(g.houses):
        rep = grip.report(g, h)
        for line in rep.enterprises:
            if line.dividend > 0.0:
                return h, line.eid
    raise AssertionError("no enterprise in this game pays anything")


def test_dividends_are_non_negative_and_at_least_one_venture_pays():
    g = _game()
    paying = 0
    for h in sorted(g.houses):
        for line in grip.report(g, h).enterprises:
            assert line.dividend >= 0.0
            paying += 1 if line.dividend > 0.0 else 0
    assert paying > 0


def test_dividend_rises_with_the_market():
    g = _game()
    h, eid = _first_earning(g)
    for c in g.market.prices:
        g.market.prices[c] = 0.5
    cheap = _line(grip.report(g, h), eid).dividend
    for c in g.market.prices:
        g.market.prices[c] = 2.0
    dear = _line(grip.report(g, h), eid).dividend
    assert dear > cheap > 0.0


def test_dividend_rises_with_the_extraction_dial():
    g = _game()
    h, eid = _first_earning(g)
    ent = next(e for e in g.ents_of(h) if e.eid == eid)
    ent.extraction_dial = 0.0
    gentle = _line(grip.report(g, h), eid).dividend
    ent.extraction_dial = 100.0
    squeezed = _line(grip.report(g, h), eid).dividend
    assert squeezed > gentle > 0.0


def test_a_venture_under_construction_pays_nothing():
    g = _game()
    h, eid = _first_earning(g)
    ent = next(e for e in g.ents_of(h) if e.eid == eid)
    ent.under_construction = 2
    ent.target_tier = ent.tier + 1
    assert _line(grip.report(g, h), eid).dividend == 0.0


# --- purity ----------------------------------------------------------------

def test_report_mutates_nothing_and_never_touches_the_rng():
    g = _game(11)
    before = _snapshot(g)
    for h in sorted(g.houses):
        grip.report(g, h)
        grip.report(g, h)
    assert _snapshot(g) == before


def test_report_is_repeatable_and_seed_stable():
    a, b = _game(11), _game(11)
    h = _first_house(a)
    ra1, ra2 = grip.report(a, h), grip.report(a, h)
    rb = grip.report(b, h)
    assert ra1 == ra2
    assert ra1 == rb


def test_report_does_not_pay_out_gold():
    """The dividend figure is an ESTIMATE — nobody's purse may move."""
    g = _game()
    h = _first_house(g)
    purses = {c.id: c.gold_reserve for c in g.realms[h].characters}
    treasury = g.houses[h].treasury
    for _ in range(3):
        grip.report(g, h)
    assert {c.id: c.gold_reserve for c in g.realms[h].characters} == purses
    assert g.houses[h].treasury == treasury


# --- edges -----------------------------------------------------------------

def test_report_unknown_house_returns_empty_report():
    """report() should return an empty report for a house not in game.realms,
    not raise KeyError."""
    g = _game()
    rep = grip.report(g, "NONEXISTENT")
    assert rep.house == "NONEXISTENT"
    assert rep.enterprises == ()
    assert rep.loyal_bloc == ()
    assert rep.controlling_stake == 0.0
    assert rep.top_predator is None
    assert rep.threshold == TAKEOVER_THRESHOLD
    assert rep.band in grip.BANDS


def test_ruler_in_loyal_bloc_even_without_shares():
    """The ruler should always be in the loyal bloc while alive, even if they
    personally hold no shares in any enterprise."""
    g = _game()
    h = _first_house(g)
    realm = g.realms[h]
    ruler = realm.ruler
    # Strip the ruler from all ledgers
    house_ents = list(g.ents_of(h))
    for ent in house_ents:
        if ruler.id in ent.ledger:
            del ent.ledger[ruler.id]
    rep = grip.report(g, h)
    ruler_in_bloc = any(m.id == ruler.id for m in rep.loyal_bloc)
    assert ruler_in_bloc, "Ruler should be in the loyal bloc even without shares"


def test_disloyalty_judged_across_all_enterprises():
    """Disloyalty should be judged across every enterprise in the game, not just
    the house's own enterprises. A kinsman's grudge does not stop mattering
    because his shares happen to sit in someone else's company."""
    g = _game()
    h = _first_house(g)
    realm = g.realms[h]
    # Find a living non-ruler character
    kin = _kin(realm, 1)[0]
    # Set a very bad opinion of the ruler (below DISLOYAL_OPINION = -20)
    g.society.opinions[(kin.id, realm.ruler.id)] = -50
    # Make the character a director of a house enterprise
    house_ents = list(g.ents_of(h))
    assert len(house_ents) > 0
    house_ents[0].director_id = kin.id
    # Give this character shares ONLY in ANOTHER house's enterprise (not house_ents)
    # Strip any shares they have in house enterprises
    for ent in house_ents:
        if kin.id in ent.ledger:
            del ent.ledger[kin.id]
    other_houses = [hh for hh in g.houses if hh != h]
    assert other_houses, "Need at least two houses"
    other_ent = None
    for ent in g.enterprises:
        if ent.house == other_houses[0]:
            other_ent = ent
            break
    assert other_ent is not None, "Need an enterprise from another house"
    other_ent.ledger[kin.id] = 10.0
    # The character is a director of a house enterprise, but only holds shares
    # in another house's company. With disloyal_shareholders called on house_ents,
    # they won't be flagged (they don't hold shares in house_ents).
    # With ALL enterprises, they should be flagged as disloyal.
    rep = grip.report(g, h)
    line = _line(rep, house_ents[0].eid)
    assert line.director is not None
    assert line.director.disloyal, "Director should be marked disloyal (bad opinion) even though their shares are in another house's enterprise"


def test_a_house_with_no_enterprises_reports_cleanly():
    g = _game()
    h = _first_house(g)
    g.enterprises = [e for e in g.enterprises if e.house != h]
    rep = grip.report(g, h)
    assert rep.enterprises == ()
    assert rep.loyal_bloc == ()
    assert rep.controlling_stake == 0.0
    assert rep.top_predator is None
    assert rep.band in grip.BANDS


def test_every_house_reports_after_the_simulation_has_run():
    """Soak: turns move ledgers, kill holders and seat Directors. The read-model
    must survive all of it and stay internally consistent."""
    g = _game(11)
    for _ in range(8):
        g.end_turn()
    for h in sorted(g.houses):
        rep = grip.report(g, h)
        assert rep.band == grip.band_for(rep.controlling_stake)
        assert abs(rep.controlling_stake
                   - sum(m.stake for m in rep.loyal_bloc)) < 1e-6
        assert 0.0 <= rep.controlling_stake <= 100.0 + 1e-9
        assert len(rep.enterprises) == len(g.ents_of(h))
        for line in rep.enterprises:
            assert line.dividend >= 0.0
            assert 0.0 <= line.your_stake <= 100.0 + 1e-9
            if line.top_outside is not None:
                holder, pct = line.top_outside
                assert isinstance(holder, str) and pct > 0.0
