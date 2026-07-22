"""The Rival arc (Gilded Saga §4.A): a rising three-beat antagonist arc whose
predicates key off @self - the real AI house bound as the Rival. No invented
entities; @self binds to a house that already exists."""

from gilded.saga.beats import Beat, Predicate


def rival_beats(rival_name: str):
    """Templated beats bound to the rival via cast={'self': rival_name}."""
    cast = {"self": rival_name}

    def war():
        return Predicate(kind="fact_exists", predicate="went_to_war",
                         subject_kind="house", subject_id="@self")

    def atrocities(n):
        return Predicate(kind="fact_exists", predicate="committed_atrocity",
                         subject_kind="house", subject_id="@self", min_count=n)

    first = Beat(bid="rival_first_blood", source="rival",
                 title=f"House {rival_name} Draws Steel", load_bearing=True,
                 completion=war(), cast=cast,
                 foreshadow=f"House {rival_name} sharpens its ambitions",
                 payoff=f"House {rival_name} goes to war - the rivalry turns bloody.",
                 next_bids=["rival_bloody_hands"])
    second = Beat(bid="rival_bloody_hands", source="rival",
                  title=f"The Sins of House {rival_name}", load_bearing=True,
                  completion=atrocities(3), cast=cast,
                  foreshadow=f"the price of House {rival_name}'s rise is paid in the provinces",
                  payoff=f"House {rival_name}'s hands are bloody - three atrocities on the ledger.",
                  next_bids=["rival_menace"])
    third = Beat(bid="rival_menace", source="rival",
                 title=f"House {rival_name} Ascendant", load_bearing=True,
                 completion=atrocities(6), cast=cast,
                 foreshadow=f"House {rival_name} looms over the age",
                 payoff=f"House {rival_name} stands ascendant and unrepentant.")
    return [first, second, third]
