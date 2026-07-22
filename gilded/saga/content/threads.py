"""The Chronicle (Gilded Saga §4.B): emergent named threads detected from the
FactStore, promoted when a pattern crosses a threshold, resolved at payoff.
Deterministic: threshold + tie-break by bid; capped for legibility."""

from gilded.saga.beats import Beat, Predicate

MAX_ACTIVE_THREADS = 3
SCANDAL_MIN = 2


def candidate_threads(facts, houses):
    """Return list of (bid, fact_count, Beat) for patterns not yet promoted."""
    out = []
    for h in sorted(houses):
        n = facts.count("committed_atrocity", subject=("house", h))
        if n >= SCANDAL_MIN:
            bid = f"thread_scandal_{h}"
            beat = Beat(bid=bid, source="chronicle",
                        title=f"The Shame of House {h}", load_bearing=True,
                        completion=Predicate(kind="any", parts=[
                            Predicate(kind="fact_exists", predicate="suffered_revolution",
                                      subject_kind="house", subject_id=h),
                            Predicate(kind="fact_exists", predicate="transformed",
                                      subject_kind="house", subject_id=h)]),
                        foreshadow=f"House {h}'s sins mount; the workers are counting",
                        payoff=f"House {h} answers for its sins.")
            out.append((bid, n, beat))
    out.sort(key=lambda t: (-t[1], t[0]))
    return out
