"""Tests for gilded.society.relationships and house_ai (mission G11)."""

import random

from gilded.society.characters import ATTRIBUTES, Secret, SocietyState
from gilded.society.house_ai import tick_realm
from gilded.society.realm import create_house_realm
from gilded.society.relationships import (
    get_relation,
    get_state,
    modify_opinion,
    opinion_of,
    set_state,
    tick_relationships,
)
from gilded.society.schemes import SchemeManager


class QuietRng:
    """Chance rolls never fire; every other draw is deterministic."""

    def random(self):
        return 0.99

    def randint(self, a, b):
        return a

    def choice(self, seq):
        return seq[0]

    def sample(self, seq, k):
        return list(seq)[:k]

    def shuffle(self, seq):
        pass

    def gauss(self, mu, sigma):
        return mu


class EagerRng(QuietRng):
    """Every chance roll fires."""

    def random(self):
        return 0.0


def _realm(seed, house="Vantrell"):
    random.seed(seed)
    rng = random.Random(seed)
    society = SocietyState(rng)
    return create_house_realm(house, society)


def test_opinion_helpers_and_relation_thresholds():
    ra = _realm(70)
    set_state(ra.society, {})
    a, b = ra.characters[0], ra.characters[1]
    assert opinion_of(a, b) == 0 and get_relation(a, b) == "neutral"
    modify_opinion(a, b, -25)
    assert opinion_of(a, b) == -25 and get_relation(a, b) == "rival"
    modify_opinion(a, b, 50)
    assert opinion_of(a, b) == 25 and get_relation(a, b) == "friend"
    assert opinion_of(b, a) == 0                    # opinions are directed


def test_succession_grievances_fire_only_on_ruler_change():
    ra = _realm(71)
    set_state(ra.society, {})
    mgr = SchemeManager()
    realms = {"Vantrell": ra}
    tick_relationships(realms, mgr, 1, QuietRng())  # registers the sitting ruler
    old = ra.ruler
    heir = next(c for c in ra.characters
                if c.is_alive and c.age >= 16 and c.id != old.id)
    ra.dynasty.all_characters[heir.id] = heir
    ra.ruler = heir
    ra.court.ruler = heir
    tick_relationships(realms, mgr, 2, QuietRng())
    assert opinion_of(old, heir) == -15             # passed over (QuietRng randint -> 15)
    tick_relationships(realms, mgr, 3, QuietRng())  # same ruler: no repeat grievance
    assert opinion_of(old, heir) == -15


def test_grievance_makes_rival_and_seated_rival_plots_coup():
    ra = _realm(72)
    set_state(ra.society, {})
    mgr = SchemeManager()
    seated = next(c for c in ra.court.positions.values()
                  if c is not None and c.is_alive)
    modify_opinion(seated, ra.ruler, -20)
    tick_relationships({"Vantrell": ra}, mgr, 1, EagerRng())
    assert get_relation(seated, ra.ruler) == "rival"
    ours = [s for s in mgr.schemes if s.agent.id == seated.id]
    assert ours and ours[0].scheme_type == "coup"
    assert ours[0].target.id == ra.ruler.id


def test_foreign_rival_ruler_plots_assassination():
    random.seed(73)
    rng0 = random.Random(73)
    society = SocietyState(rng0)
    ra = create_house_realm("Vantrell", society)
    rb = create_house_realm("Karsgate", society)
    set_state(society, {})
    mgr = SchemeManager()
    modify_opinion(ra.ruler, rb.ruler, -30)
    tick_relationships({"Vantrell": ra, "Karsgate": rb}, mgr, 1, EagerRng())
    ours = [s for s in mgr.schemes if s.agent.id == ra.ruler.id]
    assert ours and ours[0].scheme_type == "assassination"
    assert ours[0].target.id == rb.ruler.id


def test_courtiers_discover_secrets():
    ra = _realm(74)
    set_state(ra.society, {})
    subject = next(c for c in ra.court.positions.values()
                   if c is not None and c.is_alive)
    secret = Secret("vice", subject.id, "a hidden vice", 30)
    subject.secrets.append(secret)
    tick_relationships({"Vantrell": ra}, SchemeManager(), 1, EagerRng())
    assert any(h != subject.id for h in secret.holders)


def test_state_roundtrip():
    ra = _realm(75)
    set_state(ra.society, {})
    a, b = ra.characters[0], ra.characters[1]
    modify_opinion(a, b, -40)
    snapshot = get_state(ra.society)
    set_state(ra.society, {})
    assert opinion_of(a, b) == 0
    set_state(ra.society, snapshot)
    assert opinion_of(a, b) == -40


def test_succession_installs_adult_heir():
    ra = _realm(76)
    old = ra.ruler
    heir = next(c for c in ra.characters
                if c.is_alive and c.age >= 16 and c.id != old.id)
    ra.dynasty.all_characters[heir.id] = heir
    old.is_alive = False
    msgs, born = tick_realm(ra, 1, QuietRng(), None)
    assert ra.ruler.id == heir.id and ra.court.ruler.id == heir.id
    assert any("now rules Vantrell" in m for m in msgs)
    assert all(ch is None or ch.id != heir.id
               for ch in ra.court.positions.values())


def test_births_arrive_on_the_child_interval():
    ra = _realm(77)
    ra.ruler.age = 30
    msgs, born = tick_realm(ra, 8, QuietRng(), None)
    assert any(m.startswith("A child,") for m in msgs)
    child = next(c for c in born if c.age == 0)
    assert child.id in ra.dynasty.all_characters
    assert all(c in ra.characters for c in born)
    msgs2, born2 = tick_realm(ra, 9, QuietRng(), None)
    assert not any(m.startswith("A child,") for m in msgs2)


def test_court_replenishment_fills_dead_seats():
    ra = _realm(78)
    seated = [c for c in ra.court.positions.values() if c is not None]
    seated[0].is_alive = False
    tick_realm(ra, 1, QuietRng(), None)
    for ch in ra.court.positions.values():
        assert ch is not None and ch.is_alive


def test_children_get_guardians_and_education_tracks():
    ra = _realm(79)
    tick_realm(ra, 1, QuietRng(), None)
    kids = [c for c in ra.characters if c.is_alive and c.age < 16]
    assert kids
    for k in kids:
        assert k.guardian is not None
        assert k.education_track in ATTRIBUTES


def test_feast_at_interval_warms_opinions():
    ra = _realm(80)
    set_state(ra.society, {})
    other = next(c for c in ra.characters
                 if c.is_alive and c.age >= 16 and c.id != ra.ruler.id)
    before = opinion_of(other, ra.ruler)
    msgs, born = tick_realm(ra, 12, QuietRng(), None)
    assert any("hosts a great feast" in m for m in msgs)
    assert opinion_of(other, ra.ruler) >= before + 3