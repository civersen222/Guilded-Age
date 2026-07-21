# Play the Game End-to-End — Design

**Date:** 2026-07-21
**Goal (user's words):** "make a plan to play the game. i need screenshots and you need to be able to play the game end to end. it should match the length of a crusader kings or civilization game to be a success in that regard."
**Revision:** after the playability audit found the game structurally unwinnable and save/load broken, the user directed: fix the game to a playable state first, then play it.

## Success criteria

1. A complete campaign is played on a **Huge (96x96) map** — turn budget 1000, victories unlocked from turn 300 — ending in an actual victory screen (any type) or a time-victory at the budget.
2. **Claude makes every strategic decision** for the player civ, every turn (not an autopilot).
3. A **screenshot album** of real game-UI captures: one every ~10 turns plus every milestone (wars, weddings, successions, era changes, religion founding, victory), roughly 100-150 images, plus a written campaign log.
4. The run is **off-screen** (SDL dummy driver); the user reviews the album and log afterward.
5. All game-code changes are made by **CynCo missions only** — Claude never edits game source. Smoke tests in C:/tmp are read-only verification; pytest baseline must not regress.

## Audit findings (2026-07-21, drives Phase 1)

Method: 1100-turn Huge-map soak, 450-turn Small-map victory telemetry, 300-turn diplomacy probe, off-screen UI sweep of all popups, save/load round-trip test, static trace of every player action handler. Scripts preserved in C:/tmp (audit_soak.py, audit_victory.py, audit_probe.py, audit_ui_sweep.py, audit_saveload.py).

### Game-breaking

- **G1 — The game cannot be won, by anyone, ever.**
  - Legitimacy death spiral: late-game tide drain (`LEGITIMACY_TIDE_DRAIN` 0.6/turn at full tide, ideology.py:73) exceeds max recovery (+0.4/turn, ideology.py:70); every House (player included) hits 0 legitimacy by mid-game.
  - `_check_victory` (game.py:1445-1447) skips any civ below 40 legitimacy for every victory type except Conquest.
  - Conquest is dead because wars never happen (G3).
  - The 1000-turn budget triggers nothing when reached — no time victory, no scoring, no end.
  - Evidence: 1100 soaked turns, `victory=None`, `game_over=False`; all civs at 0 legitimacy from ~turn 150.
- **G2 — Save/load broken in three places.**
  - Save button (game_screen.py:341) calls the 4-field stub `Game.save_game` (game.py:1988) instead of the real serializer in save_system.py (which only the Load screen uses).
  - `Game.load_game` (game.py:1999) is uncallable: stacked `@staticmethod @classmethod` raises `TypeError: 'classmethod' object is not callable`.
  - `Game.from_dict` (game.py:1812) predates the deep-systems waves: drops realms, courts, schemes, marriages (module globals in marriages.py), tide, legitimacy, event chains, enterprises, and `city.climate_zone` — a loaded game **crashes on its next process_turn** (KeyError None, city.py:519). Round-trip evidence: courtiers 236→45, realms 4→2, crash at turn 22.
- **G3 — Wars never happen.** Relations only ever rise (marriage bonuses every 5 AI turns; no friction source ever pushes below the −30 war threshold). The M75 war gate never opens; all battle/siege/capture/peace machinery goes unexercised. Evidence: 0 war events in 1850+ soaked turns; relations pinned 67-100.

### Degrades-play

- **D1 — AI economy is a zombie.** AI gold and faith pinned at exactly 0 forever; no AI ever founds a religion (Religion victory dead in practice); prestige resets to 0 on succession and never accrues for AI civs (Dynasty victory max observed 137/1500 — sync at game.py:1082-1089 reads only the living ruler's prestige, and dynastic prestige only for the player).
- **D2 — Unit pileup.** ~6 units/turn accumulate forever on Huge (6,748 alive at t1100); no cap, nothing dies.
- **D3 — Expansion sprint then stasis.** All 7 AIs hit their 17-city fair-share cap by turn 25 of a 1000-turn budget; the map is fully carved up in the first 4% of the campaign.
- **D4 — Console spam.** `[PROMOTION]` per unit per turn (AI never resolves promotions); `[game_screen]` debug prints in the shipped UI.
- **D5 — Silent no-op buttons.** Player scheme/marriage actions return silently when realm lookup fails (scheme_menu.py:77, realm_popup.py:188) — no feedback.

### Cosmetic

Raw enum in popup HTML (`<character_deepening.focus>` warning), clipped labels, font-preload warnings.

### Verified working

Engine speed 0.1s/turn at 6,000 units; zero crashes in 1850+ soaked turns; all 13 popups open cleanly through the real UI; victory screen exists (game_screen.py:307); unit/city/tech/appointment actions route to real logic; `pygame.image.save` captures the real screen off-screen (dummy SDL driver).

## Phase 1 — Fix wave (CynCo missions M77-M82)

Each mission follows the established discipline: byte-for-byte brief, read-only C:/tmp smoke, worktree pre-validation, tamper grep, full smoke suite, pytest baseline ("1 failed, 70 passed" — if a fix legitimately changes the baseline the brief states the new expected line), commit hash reported.

- **M77 — A winnable game.** Rebalance legitimacy so recovery can outpace tide drain for a well-run House (scale recovery with happiness/stability; cap effective tide drain; AI legitimacy management on the existing dial/relief surface). Add **time victory**: at `turn_budget`, score all civs (cities, techs, culture, prestige, gold, legitimacy) and declare the winner via the existing victory pipeline so the victory screen fires. Smoke: a soaked game ends by the budget with a winner; a content, well-run House holds legitimacy ≥ 40.
- **M78 — One true save system.** Wire the Save button to save_system.py; delete/bypass the `Game.save_game`/`load_game` stubs; extend save_system to serialize and restore everything from_dict drops: realms (rulers, courts, courtiers), scheme_manager, marriages module state, tide, legitimacy, chain_manager, enterprises/ledgers, `city.climate_zone` and any other field whose absence crashes a loaded game. Smoke: play 50 turns → save → load → run 20 more turns crash-free → key invariants (courtier counts, relations, wars, researched techs, legitimacy, marriages) survive the round trip.
- **M79 — War friction.** Relations decay toward a neutral baseline each turn; sources of negative pressure (border tension between adjacent empires, rivalry grudges, scheme exposure); cap marriage-bonus stacking. Tune so the M75 strength-gated war check actually fires. Smoke: in a 200-turn soak, at least one war is declared, fought, and ended by the existing peace machinery.
- **M80 — AI economy, faith, and prestige repair.** AI treasuries hold reserves instead of pinning at 0; AI accrues faith and founds religions when able; prestige accrues from deeds and survives succession (house-level accumulation, not just the living ruler), for AI civs as well as the player. Smoke: by turn 150 some AI has gold > 0 sustained, a religion exists, and some House's prestige exceeds its ruler's lifetime contribution.
- **M81 — Military hygiene.** Army cap tied to city count/upkeep so units stop accumulating forever; AI resolves pending promotions; remove `[PROMOTION]`/`[game_screen]` stdout spam. Smoke: 300-turn soak keeps living units under a map-scaled bound; no spam lines in captured stdout.
- **M82 — Expansion pacing.** Stretch the land grab across the campaign arc (settler cost/cadence scaling, or a growth-gated city cap that rises over eras) so the map is not fully carved up by turn 25 on Huge. Smoke: on a Huge map, AIs reach their final city count no earlier than ~turn 200.

D5 and the cosmetic items ride along in whichever mission touches the nearest file, or a small cleanup mission if they don't fit.

**Phase 1 exit gate:** re-run the audit scripts. Required: a soaked Huge game **ends with a victory by turn ≤ 1000**; at least one war occurs; save/load round-trips; unit counts bounded; AI treasuries alive. Only then does the marathon start.

## Phase 2 — Play console (CynCo mission M83)

A repo tool (`play_console.py`) that lets Claude play the real game from a terminal:

- **Construction:** builds a game exactly as NewGameDialog does (civ, difficulty, Huge map, 7 AI opponents), boots the real `GameScreen` off-screen with `SDL_VIDEODRIVER=dummy`.
- **Protocol:** line-based commands on stdin, structured replies on stdout:
  - `state` — compact JSON report: turn, my cities (yields, production, unrest), units, treasury, research, diplomacy relations/wars, court/characters, schemes, threats, victory progress for all civs.
  - Action commands mapping to the same engine calls the UI popups make: `build <city> <item>`, `research <tech>`, `move <unit> <hex>` / `attack` / `fortify`, `found <unit>`, `war <civ>` / `peace <civ>`, `marry <a> <b>`, `scheme <type> <target>`, `appoint <pos> <char>`, `dial <name> <value>`.
  - `end_turn` — advances via the GameScreen path, returns turn events.
  - `shot <name>` — renders the current frame (optionally opening a named popup first: `shot t100_diplomacy diplomacy`) and saves a PNG to the run directory.
  - `save <name>` — checkpoint via save_system (autosaved every turn regardless).
- **Crash safety:** every turn autosaves; if the process dies, a new console resumes from the last checkpoint (this is why M78 precedes M83).
- Smoke: scripted session plays 30 turns through the console issuing every command class, saves screenshots, kills the process, resumes from checkpoint, plays 5 more.

## Phase 3 — The marathon

- **Setup:** Huge map, 7 AI opponents, Standard difficulty; run directory `C:/tmp/campaign_<date>/` holding screenshots, autosaves, and `campaign_log.md`.
- **Play loop (Claude, every turn):** `state` → decide (economy, research, military, diplomacy, court, schemes) → issue commands → `end_turn` → log notable events; `shot` every 10 turns and at every milestone.
- **Strategy intent:** play the character game and the map game together; pick a victory path mid-campaign based on how the world develops; fight wars when they come (post-M79 they will).
- **Bug protocol:** if the game crashes or a system misbehaves mid-campaign, diagnose from the traceback and logs, author a CynCo hotfix mission, verify it, resume from the last checkpoint. The campaign log records every incident. (Covered by the user's standing autonomous-dispatch authorization.)
- **Deliverable:** the screenshot album + campaign log telling the full story from turn 1 to the victory screen, with the final shot being the victory itself.

## Risks

- **Tuning misses:** M77/M79 are balance work; the exit-gate soak may need a second tuning pass — budgeted as brief revisions, not new scope.
- **Marathon wall-clock:** ~1000 turns with Claude deciding each one is a long session; checkpoints make it resumable across sessions.
- **Deep-turn unknowns:** turns 300-1000 with wars active is territory no soak has exercised with a *playing* player; the bug protocol is the safety net.
