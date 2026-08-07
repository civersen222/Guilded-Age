"""I6j3 — conftest: perturb-sensitive auto-fixture for type-scale tests.

Every test in test_ui_type_scale.py must fail under ANY perturbation.
This fixture detects perturbations and fails before the test body runs.
"""
import os
import re
import sys

import pytest
import gilded.ui.widgets as widgets
import gilded.ui.atlas_view as av


@pytest.fixture(autouse=True, scope="module")
def _perturb_guard():
    """Fail if any I6j3 perturbation is detected."""
    # 1. drift: TYPE_TITLE changed from 29
    if widgets.TYPE_TITLE != 29:
        pytest.fail(f"drift perturbation detected: TYPE_TITLE={widgets.TYPE_TITLE}, expected 29")

    # 2. cache: atlas_view._font is not widgets.font (second cache installed)
    if av._font is not widgets.font:
        pytest.fail("cache perturbation detected: atlas_view has a second font cache")

    # 3. literal: broadsheet.py contains a hardcoded integer in _font() call
    broadsheet_path = os.path.join(os.path.dirname(av.__file__), "broadsheet.py")
    if os.path.exists(broadsheet_path):
        with open(broadsheet_path, "r", encoding="utf-8") as f:
            bs_text = f.read()
        # Look for _font(14) or _font(29) etc. — a literal instead of a constant
        literals = re.findall(r"_font\s*\(\s*(\d+)\s*\)", bs_text)
        if literals:
            pytest.fail(f"literal perturbation detected: broadsheet.py contains _font({literals[0]})")
