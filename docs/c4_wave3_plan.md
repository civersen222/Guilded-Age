# C4 Wave 3 — Finish the Living UI

BASE: ad934c5. 11 pre-existing failures at base (font-routing metric shifts +
atlas floor regression). Mission goal: 3-spine world + probe + ACCENTS +
test_c4_contract.py, no NEW failures.

## Gate consumes exactly
- G4.1a.tabs: broadsheet.TABS == ["House","Powers","Atlas"]
- G4.1a.old_tabs: no dissolved tab name in any TABS var under gilded/ui
- G4.3: gilded.ui.probe exists; registry.ACCENTS exists

## Deliverables
1. broadsheet.TABS = ("House","Powers","Atlas")
2. draw() dispatch re-routed to 3 spines; dissolved content re-homed
3. gilded/ui/probe.py: render_screen(state, screen) -> Surface (real draw code)
4. view populates _accent_log during draw; registry.ACCENTS reads it
5. gilded/tests/test_c4_contract.py (exact content from mission)
6. C3 residuals: power_row_title(), Powers no-overlap test, pin C3 constants
7. Rewrite tab tests to 3-spine world (test_ui_broadsheet tab tests)

## Pre-existing (do NOT need to fix, but must not worsen)
- test_heir_controls::test_heir_picker_offers_men_in_succession_order
- test_ui_atlas_layout::test_rule5_glyph_floor_seed42_1280x900
- test_ui_broadsheet::test_R5_page_level_button_opens_chooser
- test_ui_broadsheet::test_every_tab_draws_its_measured_number_of_regions
- test_ui_broadsheet::test_every_control_on_every_tab_explains_itself
- test_ui_paper::test_rule3_exact_594_at_18pt (+3 others)
- test_ui_powers::test_overflow_at_40_rows, test_no_overflow_at_30_rows
