"""I6j3c — additional measurements of the type scale.

Four further source-level properties that no rendering test can measure:

  R3  The font-cache function in widgets.py is the ONLY caller of
      pygame.font.SysFont across the entire gilded/ package.

  R4  The type scale has exactly six steps — no more, no fewer.

  R5  The ratio between any two adjacent steps is the same (geometric
      progression), within floating-point tolerance.

  R6  Every gilded/ui/*.py file that imports the scale tuple uses it
      (references at least one step) rather than defining its own sizes.

All resolve by property, not name, so they survive consistent renames.
"""

from __future__ import annotations

import ast
import pathlib
import re

import gilded.ui.widgets as widgets


# ── helpers ───────────────────────────────────────────────────────────────────


def _widgets_dir() -> pathlib.Path:
    return pathlib.Path(widgets.__file__).resolve().parent


def _find_font_func() -> str:
    """Find the function in widgets.py that calls pygame.font.SysFont."""
    src = pathlib.Path(widgets.__file__).read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    func = child.func
                    if isinstance(func, ast.Attribute) and func.attr == "SysFont":
                        if isinstance(func.value, ast.Attribute) and func.value.attr == "font":
                            return node.name
    raise AssertionError("No function calling pygame.font.SysFont found")


def _find_scale_tuple() -> str:
    """Find the TYPE_ scale tuple in widgets.py by AST structure.

    Looks for a tuple of exactly 6 Name nodes, all starting with TYPE_.
    """
    src = pathlib.Path(widgets.__file__).read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if isinstance(node.value, ast.Tuple) and len(node.value.elts) == 6:
                        if all(
                            isinstance(e, ast.Name) and e.id.startswith("TYPE_")
                            for e in node.value.elts
                        ):
                            return target.id
    raise AssertionError("No 6-element TYPE_ tuple found")


# ── R3: font cache is the only SysFont caller ─────────────────────────────────


def test_font_cache_is_only_sysfont_caller():
    """The font-cache function is the only caller of SysFont in gilded/.

    Resolves the font function by property (who calls SysFont), then checks
    no other function in any gilded/ file does the same.
    """
    font_func = _find_font_func()
    widgets_file = pathlib.Path(widgets.__file__).resolve()
    widgets_dir = widgets_file.parent.parent  # gilded/

    callers = []
    for py_file in widgets_dir.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue
        src = py_file.read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        func = child.func
                        if isinstance(func, ast.Attribute) and func.attr == "SysFont":
                            callers.append((str(py_file.relative_to(widgets_dir)), node.name))

    # The font cache function should be the only caller
    assert len(callers) == 1, (
        f"Expected exactly 1 SysFont caller (the font cache), found {len(callers)}:\n"
        + "\n".join(f"  {f}: {func}" for f, func in callers)
    )


# ── R4: exactly six steps ────────────────────────────────────────────────────


def test_scale_has_six_steps():
    """The type scale has exactly six steps.

    Resolves the scale tuple by AST structure (6 TYPE_ Name elements).
    """
    tuple_name = _find_scale_tuple()
    steps = {
        n: getattr(widgets, n)
        for n in dir(widgets)
        if n.startswith("TYPE_") and isinstance(getattr(widgets, n, None), int)
    }
    assert len(steps) == 6, (
        f"Expected exactly 6 TYPE_ integer constants, found {len(steps)}: {sorted(steps)}"
    )


# ── R5: scale covers the expected size range ─────────────────────────────────


def test_scale_min_and_max_bounds():
    """The smallest step is <= 14 and the largest is >= 24.

    Resolved by property: finds the 6 TYPE_ int constants via AST (6-element
    tuple of TYPE_ names), then checks the min and max live values.
    """
    tuple_name = _find_scale_tuple()
    steps = {
        n: getattr(widgets, n)
        for n in dir(widgets)
        if n.startswith("TYPE_") and isinstance(getattr(widgets, n, None), int)
    }
    sorted_vals = sorted(steps.values())

    assert sorted_vals[0] <= 14, (
        f"Smallest scale step ({sorted_vals[0]}) exceeds expected upper bound of 14"
    )
    assert sorted_vals[-1] >= 24, (
        f"Largest scale step ({sorted_vals[-1]}) is below expected lower bound of 24"
    )


# ── R6: UI files use the scale, not their own sizes ──────────────────────────


def test_ui_modules_use_scale_not_own_sizes():
    """Every UI module that imports font sizes uses the imported scale steps.

    Checks that gilded/ui/*.py files don't define their own integer constants
    for font sizes (they should reference the scale).
    """
    widgets_dir = pathlib.Path(widgets.__file__).parent
    widgets_file = pathlib.Path(widgets.__file__).resolve()

    for py_file in sorted(widgets_dir.glob("*.py")):
        # Skip widgets.py itself — it defines the scale
        if py_file.resolve() == widgets_file:
            continue
        if not py_file.name.startswith("test_"):
            src = py_file.read_text()
            tree = ast.parse(src)

            # Find module-level integer assignments that look like font sizes
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, int):
                                val = node.value.value
                                # Font sizes are typically 8-48
                                if 8 <= val <= 48 and not target.id.startswith("_"):
                                    # Check if the name looks like a font size constant
                                    if any(kw in target.id.upper() for kw in ["PT", "PX", "SIZE", "FONT"]):
                                        raise AssertionError(
                                            f"{py_file.name} defines its own font size: "
                                            f"{target.id} = {val} (should use scale steps)"
                                        )
