# Mission C3 — The World Pushes Back — COMPLETE

BASE: 9c4b773 (C2 landed: set_ambition/agendas/ambitions.status)

## Marker

Mission C3 is complete. The four Orders — Crown, Treasury, Guilds, Church —
are first-class actors with the SAME anatomy as a House: a real Character
head with a private want and stance, a live goal on a House, a treasury,
and reach. A House stake that crosses an Order's goal meets the Order's
opposition.

## Deliverables

| Deliverable | Location | Verified |
|---|---|---|
| The four Orders as first-class actors: Character head (private want + stance), live `agenda.Goal` on a House, `treasury`, `reach` | `gilded/orders.py` (`Order`, `init_orders`, `tick_orders`) | `test_orders_exist_with_their_anatomy` |
| `ambitions.wants(order_name)` returns the head's private want with the same keys as a House adult | `gilded/ambitions.py` (`wants`) | `test_wants_accept_order_names` |
| Determinism: two boots of one seed see identical Orders (heads seeded without shifting the world RNG) | `gilded/orders.py` (rng snapshot/restore) | `test_wants_are_deterministic_across_boots` |
| Clash: a House stake whose target crosses an Order's goal records `status().opposed_by` and logs the `ambitions.order_clash` beat | `gilded/ambitions.py` (`_order_clash`, `set_ambition`) | `test_clash_records_the_order_that_stands_in_the_way`, `test_clash_is_none_when_no_order_presses_the_target` |
| Turn loop: `tick_orders` re-aims lapsed Orders and refreshes reach | `gilded/chassis.py` (wired after `end_turn`) | `test_tick_reaims_a_lapsed_order_and_refreshes_reach` |
| Intel: Order fog is driven purely by the informant lever | `gilded/intel.py` (Order path in `report`) | `test_intel_fog_is_driven_purely_by_the_informant` |
| Contract tests | `gilded/tests/test_c3_orders.py` | 7/7 pass |

## Verification

- Full suite: `python -m pytest gilded` → **2018 passed, 0 failures**
- Multi-seed probe (7/11/13): anatomy, determinism, clash, 100-turn tick,
  and the C2 regression grid all hold; the world does not shift
- Committed as: c7ad8dd (scaffolding), 5a73e37 (C3 complete + contract
  tests), 4355fad (clash test robust across house populations)
