# Gilded — A Dynasty & Industry Simulation

Gilded is a turn-based dynasty and industry simulation played through a
broadsheet newspaper, not a hex-map 4X. Each turn the game resolves economy,
politics, war, and society behind the scenes; at the start of the next turn you
read what happened in *The Continental Gazette*.

## Run the game

```
python -m gilded
```

Requires Python 3.10+ and `pygame` (see `requirements.txt`).

## Run the tests

```
python -m pytest gilded/tests -q
```

943 passing tests at time of writing.

## Code map

| module | what it does |
|---|---|
| `chassis.py` | The game object and turn loop. Owns wiring and the event log, nothing else. Calls system modules in a fixed order each turn and converts their messages into events that the papers report. |
| `papers.py` | `compose()` reads the chassis event log through one House's eyes — the gazette carries public news, the ledger and letters carry private accounts. `format_broadsheet()` sets plain text for console and tests. |
| `ui/app.py` | The pygame loop. Opens "The Gilded Machine" window, holds a live `GildedGame` and `BroadsheetView`, translates clicks into moves (rule a petition, end the turn). |
| `ui/broadsheet.py` | Seven-tab view: Briefing (delta feed, turn papers, docket agenda), Gazette, Ledger, Letters, Docket, Policies, Atlas, House. A HUD strip rides above every tab showing the four axes, Tide, era, and rank. |
| `ui/widgets.py` | Reusable pygame widgets (buttons, sliders, petition cards). |
| `ui/atlas_view.py` | Province map renderer. Traces boundaries into screen polygons, fills by owner colour, overlays endowment glyphs, rail lines, and war fronts. |
| `society/` | Events, characters, court, ideology, labor, marriages, schemes — the life of the realm. |
| `saga/` | Director and narrator. Decides which events fire and how they are told. |

## Specs & plans

`docs/superpowers/specs/` and `docs/superpowers/plans/`.

## Legacy

The earlier CivKings prototype (hex-map 4X with pygame client) now lives under
`legacy/civkings/`. It is archived, unmaintained, and not imported by the game.
