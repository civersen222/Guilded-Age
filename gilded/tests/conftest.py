"""Shared fixtures for peerage perturbation testing.

Each test in test_peerage.py measures exactly ONE property of the read-model.
When that property is perturbed on the report() return value, only that test fails.
This module provides helpers for the perturbation verification harness.
"""
from __future__ import annotations

import copy
from dataclasses import asdict, is_dataclass


def perturb_report(report, field_name, new_value):
    """Return a copy of *report* with *field_name* replaced by *new_value*.

    Works for CourtReport (top-level) and nested dataclasses.
    Used by the perturbation verification harness — not by the tests themselves.
    """
    data = asdict(report)
    data[field_name] = new_value
    # Reconstruct the report type
    return report.__class__(**data)


def perturb_kin(kin_list, index, field_name, new_value):
    """Return a copy of *kin_list* with kin[index].field replaced."""
    new_list = copy.deepcopy(kin_list)
    if 0 <= index < len(new_list):
        setattr(new_list[index], field_name, new_value)
    return new_list
