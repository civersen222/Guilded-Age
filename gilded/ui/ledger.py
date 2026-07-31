"""Ledger model — pure data and formatting, no pygame."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from gilded.ui.figures import signed as _signed

HISTORY_SPAN = 8


@dataclass(frozen=True)
class LedgerRow:
    label: str
    amount: float


@dataclass(frozen=True)
class TurnLine:
    turn: int
    income: float
    outlay: float
    net: float


@dataclass(frozen=True)
class LedgerModel:
    turn: int
    treasury: float
    rows: Tuple[LedgerRow, ...]
    income: float
    outlay: float
    net: float
    history: Tuple[TurnLine, ...]
    summary: Tuple[LedgerRow, ...]
    notices: Tuple[str, ...]


def money(amount: float) -> str:
    """Format a signed amount using the shared figure formatter."""
    return _signed(amount)


def gold(amount: float) -> str:
    """Format a stock (treasury balance) — no sign for non-negative."""
    magnitude = round(amount)
    formatted = f"{magnitude:,}"
    if magnitude < 0:
        return f"-{-magnitude:,}"
    return formatted


def totals_line(model: LedgerModel) -> str:
    """Return the full totals bar string. Outlay is negated (it's a magnitude)."""
    income_str = _signed(model.income)
    outlay_str = _signed(-model.outlay)
    net_str = _signed(model.net)
    return f"Income: {income_str}  |  Outlay: {outlay_str}  |  Net: {net_str}"


def history_cells(line: TurnLine) -> list:
    """Return four cells for a history row: turn, income, outlay, net."""
    return [
        str(line.turn),
        _signed(line.income),
        _signed(-line.outlay),
        _signed(line.net),
    ]


def ledger_model(house, turn: int, notices: Tuple[str, ...] = ()) -> LedgerModel:
    """Build a LedgerModel from a House's journal for a given resolved turn."""
    flows = house.flows(turn)
    rows = tuple(LedgerRow(label, amount) for label, amount in flows)

    income = house.income(turn)
    outlay = house.outlay(turn)
    net = income - outlay
    treasury = house.treasury

    # History: HISTORY_SPAN turns ending at turn, oldest first
    hist_start = max(1, turn - HISTORY_SPAN + 1)
    history = []
    for t in range(hist_start, turn + 1):
        t_income = house.income(t)
        t_outlay = house.outlay(t)
        history.append(TurnLine(t, t_income, t_outlay, t_income - t_outlay))
    history = tuple(history)

    # Summary: aggregate across the same span as history
    summary_map: dict[str, float] = {}
    for t in range(hist_start, turn + 1):
        for label, amount in house.flows(t):
            summary_map[label] = summary_map.get(label, 0.0) + amount
    summary_rows = [
        LedgerRow(label, amount) for label, amount in summary_map.items()
    ]
    summary_rows.sort(key=lambda r: (-abs(r.amount), r.label))
    summary = tuple(summary_rows)

    return LedgerModel(
        turn=turn,
        treasury=treasury,
        rows=rows,
        income=income,
        outlay=outlay,
        net=net,
        history=history,
        summary=summary,
        notices=notices,
    )
