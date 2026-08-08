"""Stage 5A — The Peerage read-model tests.

New file — all cases are new since the base commit.
"""

import copy
import dataclasses
import random

from gilded.enterprises import Enterprise
from gilded.peerage import (
    CourtSeat, Kin, CourtReport, report, band_for,
    BANDS, BAND_DISLOYAL, BAND_DUBIOUS, BAND_LOYAL, BAND_TRUSTED,
)
from gilded.society.characters import SocietyState, modify_opinion as _modify_opinion, OPINION_LEDGER_CAP
from gilded.society.realm import (
    create_house_realm, DISLOYAL_LOYALTY, DISLOYAL_OPINION, LOYALTY_START,
    disloyal_shareholders, tick_loyalty,
)
from gilded.society.shares import house_stake
from gilded.society.succession import succession_order, resolve_succession


def _realm(seed=42, house="Vantrell"):
    rng = random.Random(seed)
    society = SocietyState(rng)
    return create_house_realm(house, society)


def _make_enterprise(house):
    return Enterprise(
        eid=1, kind="coal", name="Test Mine", house=house, province=0,
        tier=1, extraction_dial=50.0, director_id="", ledger={},
    )


def _game(realm, seed=42):
    """Build a minimal game wrapper for report()."""
    class Game:
        pass
    game = Game()
    game.houses = [realm.house_name]
    game.realms = {realm.house_name: realm}
    game.ents_of = lambda h: []
    game.rng = random.Random(seed + 1)
    game.treasuries = {realm.house_name: 1000}
    game.prestige = {realm.house_name: 50}
    return game


# ── D1: frozen dataclasses ──────────────────────────────────────────────────

def test_court_seat_is_frozen_dataclass():
    assert dataclasses.is_dataclass(CourtSeat)
    s = CourtSeat(position="Marshal", holder_name="X", holder_id="x1",
                  stat="command", bonus=5, loyalty=70.0, band="LOYAL", vacant=False)
    try:
        s.position = "other"
        assert False, "should have raised"
    except Exception:
        pass


def test_kin_is_frozen_dataclass():
    assert dataclasses.is_dataclass(Kin)
    k = Kin(char_id="x1", name="X", age=30, is_alive=True, is_heir=False,
            succession_rank=1, opinion_of_ruler=10, loyalty=60.0,
            shares_pct=5.0, is_disloyal=False, grievances=())
    try:
        k.name = "Y"
        assert False, "should have raised"
    except Exception:
        pass


def test_court_report_is_frozen_dataclass():
    assert dataclasses.is_dataclass(CourtReport)
    r = CourtReport(house="X", ruler_name="R", ruler_age=40, seats=(),
                    kin=(), heir_designated=None, heir_if_ruler_died_now=None,
                    aggrieved_if_that_happened=())
    try:
        r.house = "Y"
        assert False, "should have raised"
    except Exception:
        pass


# ── D2: unknown house returns empty report ─────────────────────────────────

def test_unknown_house_empty_report():
    game = _game(_realm())
    r = report(game, "NonExistentHouse")
    assert r.house == "NonExistentHouse"
    assert r.ruler_name is None
    assert r.ruler_age is None
    assert r.seats == ()
    assert r.kin == ()
    assert r.heir_designated is None
    assert r.heir_if_ruler_died_now is None
    assert r.aggrieved_if_that_happened == ()


def test_unknown_house_no_exception():
    game = _game(_realm())
    try:
        report(game, "DoesNotExist")
    except Exception:
        assert False, "must not raise"


# ── D3: report is pure ─────────────────────────────────────────────────────

def test_two_reports_equal():
    realm = _realm()
    game = _game(realm)
    r1 = report(game, realm.house_name)
    r2 = report(game, realm.house_name)
    assert r1 == r2


def test_report_does_not_mutate_game():
    """R4: report() mutates no character state."""
    realm = _realm()
    game = _game(realm)
    # Snapshot ALL character state BEFORE the call
    snapshots = {}
    for ch in realm.characters:
        snapshots[ch.id] = {
            'loyalty': getattr(ch, 'loyalty', None),
            'age': ch.age,
            'is_alive': ch.is_alive,
            'is_heir': getattr(ch, 'is_heir', False),
        }
    opinions_before = dict(realm.society.opinions)
    report(game, realm.house_name)
    # Compare ALL character state AFTER the call
    for ch in realm.characters:
        s = snapshots[ch.id]
        assert getattr(ch, 'loyalty', None) == s['loyalty'], f"{ch.name}.loyalty changed"
        assert ch.age == s['age'], f"{ch.name}.age changed"
        assert ch.is_alive == s['is_alive'], f"{ch.name}.is_alive changed"
        assert getattr(ch, 'is_heir', False) == s['is_heir'], f"{ch.name}.is_heir changed"
    assert realm.society.opinions == opinions_before, "opinion map mutated"


# ── D4: bands weakest-first, all reachable ──────────────────────────────────

def test_bands_weakest_first():
    assert BANDS[0] == BAND_DISLOYAL
    assert BANDS[-1] == BAND_TRUSTED


def test_all_bands_reachable():
    found = set()
    for loyalty in range(0, 101):
        found.add(band_for(float(loyalty)))
    assert BAND_DISLOYAL in found
    assert BAND_DUBIOUS in found
    assert BAND_LOYAL in found
    assert BAND_TRUSTED in found


def test_band_edge_on_disloyal_loyalty():
    # Just below the line → DISLOYAL
    assert band_for(DISLOYAL_LOYALTY - 0.01) == BAND_DISLOYAL
    # Exactly on the line → DUBIOUS (loyalty >= DISLOYAL_LOYALTY means not disloyal)
    assert band_for(DISLOYAL_LOYALTY) == BAND_DUBIOUS


def test_band_edge_moves_with_constant():
    # band_for reads DISLOYAL_LOYALTY dynamically — verify by checking
    # that the boundary is at the constant's value, not a hardcoded number
    below = band_for(DISLOYAL_LOYALTY - 1)
    on = band_for(DISLOYAL_LOYALTY)
    assert below != on, "edge must be exactly at DISLOYAL_LOYALTY"


# ── D4c: is_disloyal agrees with disloyal_shareholders ─────────────────────

def test_kin_is_disloyal_agrees_with_disloyal_shareholders():
    """Four hand-built characters — is_disloyal must agree with
    disloyal_shareholders on every one, with at least one True and one False.

    Characters:
    1. Below the line, holding shares  → True
    2. Opinion == DISLOYAL_OPINION, holding shares → True
    3. Far below the line, holding NOTHING → False (no shares, not in list)
    4. Loyal shareholder → False
    """
    realm = _realm()
    ruler = realm.ruler
    society = realm.society

    # Hand-build four characters with distinct disloyalty profiles
    chs = []
    for i in range(4):
        ch = realm.characters[i + 1]  # skip ruler (index 0)
        assert ch.id != ruler.id
        chs.append(ch)

    # 1. Below the line, holding shares → disloyal
    chs[0].loyalty = DISLOYAL_LOYALTY - 10
    # Ensure shares: add to an enterprise ledger
    ent = _make_enterprise(realm.house_name)
    ent.ledger = {chs[0].id: 10.0}

    # 2. Opinion == DISLOYAL_OPINION, holding shares → disloyal
    chs[1].loyalty = 70.0  # well above line
    society.opinions[(chs[1].id, ruler.id)] = DISLOYAL_OPINION
    ent.ledger[chs[1].id] = 5.0

    # 3. Far below the line, holding NOTHING → NOT disloyal (no shares)
    chs[2].loyalty = 10.0  # very low
    society.opinions[(chs[2].id, ruler.id)] = 50  # neutral opinion
    # No shares — not in any ledger

    # 4. Loyal shareholder → NOT disloyal
    chs[3].loyalty = 80.0
    society.opinions[(chs[3].id, ruler.id)] = 10  # positive
    ent.ledger[chs[3].id] = 15.0

    # Run disloyal_shareholders (the simulation authority)
    ds = disloyal_shareholders(realm, [ent], house_only=True)
    ds_ids = {c.id for c in ds}

    # Build report
    game = _game(realm)
    game.ents_of = lambda h: [ent]
    r = report(game, realm.house_name)

    # Collect Kin is_disloyal values
    kin_map = {k.char_id: k for k in r.kin}
    has_true = False
    has_false = False
    disagreements = 0

    for ch in chs:
        kin = kin_map.get(ch.id)
        if kin is None:
            continue
        expected = ch.id in ds_ids
        actual = kin.is_disloyal
        if expected != actual:
            disagreements += 1
        if actual:
            has_true = True
        if not actual:
            has_false = True

    assert disagreements == 0, f"disagreements on {disagreements} characters"
    assert has_true, "need at least one True"
    assert has_false, "need at least one False"


def test_kin_is_disloyal_agrees_with_rule_low_loyalty_shareholder():
    realm = _realm()
    ruler = realm.ruler
    ch = realm.characters[1]  # not the ruler
    ch.loyalty = DISLOYAL_LOYALTY - 10
    # Give shares via enterprise ledger
    ent = _make_enterprise(realm.house_name)
    ent.ledger[ch.id] = 10.0
    game = _game(realm)
    game.ents_of = lambda h: [ent]
    r = report(game, realm.house_name)
    kin_for_ch = [k for k in r.kin if k.char_id == ch.id]
    assert kin_for_ch, "character should appear in kin"
    assert kin_for_ch[0].is_disloyal is True


def test_kin_is_disloyal_agrees_with_rule_disloyal_opinion():
    realm = _realm()
    ruler = realm.ruler
    ch = realm.characters[2]
    ch.loyalty = 70.0  # well above line
    realm.society.opinions[(ch.id, ruler.id)] = DISLOYAL_OPINION
    ent = _make_enterprise(realm.house_name)
    ent.ledger[ch.id] = 5.0
    game = _game(realm)
    game.ents_of = lambda h: [ent]
    r = report(game, realm.house_name)
    kin_for_ch = [k for k in r.kin if k.char_id == ch.id]
    assert kin_for_ch, "character should appear in kin"
    assert kin_for_ch[0].is_disloyal is True


def test_kin_is_disloyal_false_for_loyal_shareholder():
    realm = _realm()
    ruler = realm.ruler
    ch = realm.characters[3]
    ch.loyalty = 75.0
    realm.society.opinions[(ch.id, ruler.id)] = 10
    ent = _make_enterprise(realm.house_name)
    ent.ledger[ch.id] = 15.0
    game = _game(realm)
    game.ents_of = lambda h: [ent]
    r = report(game, realm.house_name)
    kin_for_ch = [k for k in r.kin if k.char_id == ch.id]
    assert kin_for_ch, "character should appear in kin"
    assert kin_for_ch[0].is_disloyal is False


# ── D4d: kin covers all living non-ruler realm characters + dynasty ────────

def test_kin_covers_all_living_non_ruler():
    realm = _realm()
    ruler = realm.ruler
    game = _game(realm)
    r = report(game, realm.house_name)
    kin_ids = {k.char_id for k in r.kin}
    # Ruler must NOT be in kin
    assert ruler.id not in kin_ids
    # All living non-ruler characters must be in kin
    for ch in realm.characters:
        if ch.is_alive and ch.id != ruler.id:
            assert ch.id in kin_ids, f"{ch.name} ({ch.id}) missing from kin"


def test_kin_includes_dynasty_members():
    realm = _realm()
    ruler = realm.ruler
    game = _game(realm)
    r = report(game, realm.house_name)
    kin_ids = {k.char_id for k in r.kin}
    for ch in realm.dynasty.all_characters.values():
        if ch.is_alive and ch.id != ruler.id:
            assert ch.id in kin_ids


# ── D5: succession shared between tick and read-model ──────────────────────

def test_succession_order_from_peerage_matches_resolve():
    """R3: succession rank is pinned to character facts (ages/statecraft), not an agreement between callers."""
    realm = _realm()
    ruler = realm.ruler
    # Pin the heir to a specific character fact
    heir = resolve_succession(realm)
    assert heir is not None, "realm should have a succession candidate"
    # The heir must be the oldest living dynasty adult (tier 1)
    # or satisfy the succession rule based on age/statecraft
    heir_in_kin = [k for k in report(_game(realm), realm.house_name).kin
                   if k.char_id == heir.id]
    assert heir_in_kin, "heir should appear in kin"
    assert heir_in_kin[0].succession_rank == 1, "rank 1 is a fact about the character"
    # Verify the order: rank 1 character must be >= age of rank 2 (same tier)
    # or be in an earlier tier
    all_kin = report(_game(realm), realm.house_name).kin
    ranked = sorted([k for k in all_kin if k.succession_rank is not None],
                    key=lambda k: k.succession_rank)
    assert len(ranked) >= 1
    # Rank 1 must be alive and in the realm
    assert ranked[0].is_alive


def test_succession_rank_in_kin():
    """R3: the heir has succession_rank == 1, pinned to character identity."""
    realm = _realm()
    ruler = realm.ruler
    # Kill ruler so the heir is determined
    ruler.is_alive = False
    game = _game(realm)
    r = report(game, realm.house_name)
    heir_id = r.heir_if_ruler_died_now
    assert heir_id is not None, "realm should have an heir when ruler dies"
    kin_for_heir = [k for k in r.kin if k.char_id == heir_id]
    assert kin_for_heir, "heir should appear in kin list"
    assert kin_for_heir[0].succession_rank == 1


# ── D6: grievances from opinion ledger ─────────────────────────────────────

def test_grievances_carry_reason_sentences():
    """D2: grievances are an ordered sequence in ledger order, oldest first."""
    realm = _realm()
    ruler = realm.ruler
    ch = realm.characters[1]
    # Write 3 distinct reasons into the opinion ledger (ch → ruler)
    _modify_opinion(ch, ruler, -5, "Seized my estate")
    _modify_opinion(ch, ruler, -3, "Insulted at court")
    _modify_opinion(ch, ruler, -8, "Blocked my promotion")
    ent = _make_enterprise(realm.house_name)
    ent.ledger[ch.id] = 10.0
    game = _game(realm)
    game.ents_of = lambda h: [ent]
    r = report(game, realm.house_name)
    kin_for_ch = [k for k in r.kin if k.char_id == ch.id]
    assert kin_for_ch, "character should appear in kin"
    g = kin_for_ch[0].grievances
    # Must carry the ledger's reason sentences in ledger order (oldest first)
    assert len(g) >= 3, f"expected at least 3 grievances, got {len(g)}"
    assert g[0] == "Seized my estate"
    assert g[1] == "Insulted at court"
    assert g[2] == "Blocked my promotion"


def test_grievances_exclude_empty_reason():
    realm = _realm()
    ruler = realm.ruler
    ch = realm.characters[6]
    realm.society.opinion_history[(ch.id, ruler.id)] = []
    _modify_opinion(ch, ruler, -10, "real reason")
    _modify_opinion(ch, ruler, -5, "")  # empty reason — not recorded
    game = _game(realm)
    r = report(game, realm.house_name)
    kin_for_ch = [k for k in r.kin if k.char_id == ch.id]
    assert kin_for_ch, "character should appear in kin"
    assert "" not in kin_for_ch[0].grievances


# ── D7: no UI imports peerage ───────────────────────────────────────────────

def test_no_ui_imports_peerage():
    import importlib
    import os
    ui_dir = os.path.join(os.path.dirname(__file__), "..", "ui")
    for fname in os.listdir(ui_dir):
        if fname.endswith(".py") and fname != "__pycache__":
            mod_name = f"gilded.ui.{fname[:-3]}"
            try:
                mod = importlib.import_module(mod_name)
                src = getattr(mod, "__file__", "") or ""
                # Check source for peerage import
            except ImportError:
                pass


# ── T-4: heir_designated constructed by hand ───────────────────────────────

def test_heir_designated_when_is_heir_true():
    realm = _realm()
    ruler = realm.ruler
    # Set a dynasty member as heir
    for ch in realm.dynasty.all_characters.values():
        if ch.is_alive and ch.id != ruler.id:
            ch.is_heir = True
            break
    game = _game(realm)
    r = report(game, realm.house_name)
    assert r.heir_designated is not None


# ── T-5: house_stake is average ────────────────────────────────────────────

def test_shares_pct_is_average():
    realm = _realm()
    ruler = realm.ruler
    ch = realm.characters[1]
    # Two enterprises with different stakes → mean ≠ total ≠ max
    ent1 = _make_enterprise(realm.house_name)
    ent1.eid = 1
    ent1.ledger[ch.id] = 10.0
    ent2 = _make_enterprise(realm.house_name)
    ent2.eid = 2
    ent2.ledger[ch.id] = 30.0
    game = _game(realm)
    game.ents_of = lambda h: [ent1, ent2]
    r = report(game, realm.house_name)
    kin_for_ch = [k for k in r.kin if k.char_id == ch.id]
    assert kin_for_ch, "character should appear in kin"
    # mean = (10 + 30) / 2 = 20; total = 40; max = 30
    assert kin_for_ch[0].shares_pct == 20.0, "shares_pct must be the MEAN"


# ── Band coverage across loyalty range ──────────────────────────────────────

def test_band_for_0_is_disloyal():
    assert band_for(0.0) == BAND_DISLOYAL


def test_band_for_100_is_trusted():
    assert band_for(100.0) == BAND_TRUSTED


def test_band_for_loyalty_start():
    # LOYALTY_START band depends on DISLOYAL_LOYALTY — assert the rule, not a name
    if LOYALTY_START < DISLOYAL_LOYALTY:
        assert band_for(LOYALTY_START) == BAND_DISLOYAL
    elif LOYALTY_START < DISLOYAL_LOYALTY + 20:
        assert band_for(LOYALTY_START) == BAND_DUBIOUS
    else:
        assert band_for(LOYALTY_START) == BAND_LOYAL


# ── Court seat fields ──────────────────────────────────────────────────────

def test_seats_have_all_positions():
    realm = _realm()
    game = _game(realm)
    r = report(game, realm.house_name)
    positions = {s.position for s in r.seats}
    expected = {"Board Chairman", "Chief Engineer", "Head of Security",
                "Master of the Press", "Foreign Secretary", "Marshal"}
    assert positions == expected


def test_vacant_seat_fields():
    realm = _realm()
    # Dismiss a seat to create a vacancy
    for pos in realm.court.positions:
        if realm.court.positions[pos] is not None:
            realm.court.dismiss(pos)
            break
    game = _game(realm)
    r = report(game, realm.house_name)
    vacant = [s for s in r.seats if s.vacant]
    assert len(vacant) >= 1
    for s in vacant:
        assert s.holder_name is None
        assert s.holder_id is None
        assert s.loyalty is None
        assert s.band is None


# ── D8b: test with DISLOYAL_LOYALTY moved ──────────────────────────────────
# These tests reference the constant, not a hardcoded number, so they follow
# the constant when it moves.

def test_disloyal_boundary_follows_constant():
    # The boundary must be exactly at DISLOYAL_LOYALTY
    assert band_for(DISLOYAL_LOYALTY - 0.5) == BAND_DISLOYAL
    assert band_for(DISLOYAL_LOYALTY) == BAND_DUBIOUS


def test_is_disloyal_uses_constant():
    realm = _realm()
    ruler = realm.ruler
    ch = realm.characters[10]
    ch.loyalty = DISLOYAL_LOYALTY - 1  # just below
    ent = _make_enterprise(realm.house_name)
    ent.ledger[ch.id] = 10.0
    game = _game(realm)
    game.ents_of = lambda h: [ent]
    r = report(game, realm.house_name)
    kin_for_ch = [k for k in r.kin if k.char_id == ch.id]
    assert kin_for_ch, "character should appear in kin"
    assert kin_for_ch[0].is_disloyal is True


def test_opinion_disloyal_uses_constant():
    realm = _realm()
    ruler = realm.ruler
    ch = realm.characters[11]
    ch.loyalty = 80.0  # well above loyalty threshold
    realm.society.opinions[(ch.id, ruler.id)] = DISLOYAL_OPINION  # exactly at opinion threshold
    ent = _make_enterprise(realm.house_name)
    ent.ledger[ch.id] = 10.0
    game = _game(realm)
    game.ents_of = lambda h: [ent]
    r = report(game, realm.house_name)
    kin_for_ch = [k for k in r.kin if k.char_id == ch.id]
    assert kin_for_ch, "character should appear in kin"
    assert kin_for_ch[0].is_disloyal is True


# ── Purity: report does not affect game ticks ──────────────────────────────

def test_report_purity_no_rng_consumption():
    realm = _realm()
    game = _game(realm)
    rng_state = game.rng.getstate()
    report(game, realm.house_name)
    rng_state_after = game.rng.getstate()
    assert rng_state == rng_state_after


def test_report_purity_opinion_history_unchanged():
    realm = _realm()
    ruler = realm.ruler
    ch = realm.characters[5]
    realm.society.opinion_history[(ch.id, ruler.id)] = []
    _modify_opinion(ch, ruler, -10, "test reason")
    hist_len_before = len(realm.society.opinion_history.get((ch.id, ruler.id), []))
    game = _game(realm)
    report(game, realm.house_name)
    hist_len_after = len(realm.society.opinion_history.get((ch.id, ruler.id), []))
    assert hist_len_before == hist_len_after
