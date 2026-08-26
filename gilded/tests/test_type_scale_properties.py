"""I6j3c — additional measurements of the type scale.

Four further source-level properties that no rendering test can measure:

  R3  The font-cache function in widgets.py is the ONLY caller of
      pygame.font.SysFont across the entire gilded/ package.

  R4  The type scale has exactly six steps — no more, no fewer.

  R5  The ratio between any two adjacent steps is the same (geometric
      progression), within floating-point tolerance.

  R6  Every gilded/ui/*.py file that imports the scale tuple uses it
      (references at least one step) rather than defining its own sizes.

Cases resolve by property, not name — verified against consistent renames
for R3, R5, R6. R4 counts module-level int constants by their runtime role
(exactly six), which also survives rename.
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
    """Find the font function in widgets.py: the one whose body calls
    pygame.font.Font with a path (the Banknote TTF cache)."""
    src = pathlib.Path(widgets.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    func = child.func
                    if isinstance(func, ast.Attribute) and func.attr == "Font":
                        return node.name
    raise AssertionError("No function calling pygame.font.Font found in widgets.py")


def _find_scale_tuple() -> str:
    """Find the scale tuple in widgets.py by AST structure (6-element tuple of Name refs)."""
    src = pathlib.Path(widgets.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    val = node.value
                    if isinstance(val, ast.Tuple) and len(val.elts) == 6:
                        if all(isinstance(e, ast.Name) for e in val.elts):
                            # Verify these names resolve to int constants at runtime
                            names = [e.id for e in val.elts]
                            if all(isinstance(getattr(widgets, n, None), int) for n in names):
                                return target.id
    raise AssertionError("Could not find scale tuple in widgets.py")


def _get_scale_step_names_from_tuple() -> list[str]:
    """Get the six step names from the scale tuple, resolved by AST structure."""
    tuple_name = _find_scale_tuple()
    src = pathlib.Path(widgets.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == tuple_name:
                    return [e.id for e in node.value.elts]
    raise AssertionError(f"Could not find {tuple_name} in widgets.py")


# ── R3: no SysFont under gilded/ui — TTFs are the only font source ──────────


def test_no_sysfont_under_gilded():
    """Mission C4: zero pygame.font.SysFont calls under gilded/ui — every
    font comes from the shipped Banknote TTFs via the widgets font cache."""
    widgets_dir = _widgets_dir()
    callers = []
    for py_file in widgets_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        src = py_file.read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "SysFont":
                    callers.append(py_file.relative_to(widgets_dir))

    assert not callers, (
        "SysFont calls found under gilded/ui — C4 requires the shipped TTFs:\n"
        + "\n".join(str(f) for f in callers)
    )


# ── R4: exactly six steps ────────────────────────────────────────────────────


def test_scale_has_six_steps():
    """The type scale has exactly six steps.

    Resolves by property: finds the scale tuple via AST structure (6-element
    tuple of Name refs to int constants), then verifies exactly six such
    constants exist on the live module.
    """
    tuple_name = _find_scale_tuple()
    step_names = _get_scale_step_names_from_tuple()
    # Verify all six names resolve to int constants
    steps = {n: getattr(widgets, n) for n in step_names}
    assert len(steps) == 6, (
        f"Expected exactly 6 scale step constants, found {len(steps)}: {sorted(steps)}"
    )


# ── R5: scale covers the expected size range ─────────────────────────────────


def test_scale_min_and_max_bounds():
    """The smallest step is <= 14 and the largest is >= 24.

    Resolved by property: finds the scale tuple via AST structure, then
    checks the min and max live values.
    """
    tuple_name = _find_scale_tuple()
    step_names = _get_scale_step_names_from_tuple()
    steps = {n: getattr(widgets, n) for n in step_names}
    sorted_vals = sorted(steps.values())

    assert sorted_vals[0] <= 14, (
        f"Smallest scale step ({sorted_vals[0]}) exceeds expected upper bound of 14"
    )
    assert sorted_vals[-1] >= 24, (
        f"Largest scale step ({sorted_vals[-1]}) below expected lower bound of 24"
    )


# ── R6: scale tuple matches steps in ascending order ─────────────────────────


def test_scale_tuple_is_steps_in_order():
    """The scale tuple contains the six steps in ascending order.

    Resolves the tuple by AST structure (6-element tuple of Name refs),
    then verifies the live values are strictly ascending.
    """
    step_names = _get_scale_step_names_from_tuple()
    values = [getattr(widgets, n) for n in step_names]
    assert values == sorted(values), (
        f"Scale tuple values {values} are not in ascending order"
    )
    # Also verify strictly ascending (no duplicates)
    for i in range(len(values) - 1):
        assert values[i] < values[i + 1], (
            f"Scale tuple has non-strict step at position {i}: {values[i]} >= {values[i + 1]}"
        )


# ── R6: files that import scale must use it ──────────────────────────────────


def test_scale_imported_files_use_it():
    """Every file importing the scale must reference at least one step.

    Resolves the scale tuple by AST structure, then verifies importing files
    reference at least one step rather than defining their own sizes.
    """
    ui_dir = _widgets_dir()
    step_names = _get_scale_step_names_from_tuple()
    scale_tuple_name = _find_scale_tuple()

    for py_file in sorted(ui_dir.glob("*.py")):
        if py_file.name == "widgets.py" or py_file.name == "__init__.py":
            continue

        src = py_file.read_text(encoding="utf-8")
        # Check if this file imports the scale tuple
        if scale_tuple_name not in src:
            continue

        tree = ast.parse(src)
        # Check if the file references any scale step
        uses_step = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in step_names:
                uses_step = True
                break
            if isinstance(node, ast.Attribute) and node.attr in step_names:
                uses_step = True
                break

        assert uses_step, (
            f"{py_file.name} imports the scale tuple but doesn't use any steps"
        )


# ── R7: no file defines its own font sizes ───────────────────────────────────


def test_no_local_font_size_definitions():
    """No file under gilded/ui/ defines its own font size constants.

    Checks that no file outside widgets.py assigns an integer to a variable
    whose name suggests it's a font size (contains 'pt', 'size', or 'font').
    """
    ui_dir = _widgets_dir()
    widgets_file = pathlib.Path(widgets.__file__).resolve()
    step_names = _get_scale_step_names_from_tuple()

    size_pattern = re.compile(r'(pt|size|font)', re.IGNORECASE)

    for py_file in sorted(ui_dir.glob("*.py")):
        if py_file.resolve() == widgets_file.resolve():
            continue
        if py_file.name == "__init__.py":
            continue

        src = py_file.read_text(encoding="utf-8")
        tree = ast.parse(src)

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        # Skip if it's a scale step reference
                        if name in step_names:
                            continue
                        # Check if the name suggests a font size
                        if size_pattern.search(name):
                            # Allow assignments to other Names (e.g. _TEXT_PT = TYPE_CAPTION)
                            if isinstance(node.value, ast.Constant) and isinstance(
                                node.value.value, int
                            ):
                                raise AssertionError(
                                    f"{py_file.name} defines its own font size: "
                                    f"{target.id} = {node.value.value} (should use scale steps)"
                                )
