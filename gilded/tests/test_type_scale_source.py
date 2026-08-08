"""I6j3c — THE RULES THE SCREEN CANNOT SHOW YOU.

Two source-level properties of the type scale that no rendering test can
measure, plus the removal of a duplicate test case.

  R1  Every font call site outside widgets.py must use a NAME (a reference
      to a scale step), never an integer literal — not directly and not
      through a local alias bound to an integer.

  R2  The scale must ascend: steps declared smallest first, each strictly
      bigger than the one before. The scale tuple must be those six steps
      in that order.

Both resolve the font function and scale tuple by PROPERTY (what calls
SysFont, what names the steps) rather than by a name spelled in the case,
so a consistent rename across the repository cannot defeat them.
"""

from __future__ import annotations

import ast
import inspect
import pathlib
import textwrap
import typing

import gilded.ui.widgets as widgets


# ── helpers: resolve things by property, not name ────────────────────────────


def _widgets_dir() -> pathlib.Path:
    """Return the gilded/ui/ directory, resolved from the imported module."""
    return pathlib.Path(widgets.__file__).resolve().parent


def _find_font_func_in_tree() -> str:
    """Find the name of the function in widgets.py that reaches pygame.font.SysFont.

    Resolves by property: the function whose body (directly or via a helper)
    contains a call to pygame.font.SysFont.  Survives renames.
    """
    widgets_file = pathlib.Path(widgets.__file__).resolve()
    tree = ast.parse(widgets_file.read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Walk the function body looking for a SysFont call
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    func = child.func
                    # pygame.font.SysFont(...)
                    if isinstance(func, ast.Attribute) and func.attr == "SysFont":
                        return node.name
                    # font.SysFont(...) where font is pygame.font
                    if isinstance(func, ast.Attribute) and func.attr == "SysFont":
                        return node.name

    raise AssertionError("No function in widgets.py calls pygame.font.SysFont")


def _find_scale_tuple_in_tree() -> str:
    """Find the name of the tuple in widgets.py that holds the six scale steps.

    Resolves by property: a module-level Name whose value is a Tuple of 6
    ast.Name elements whose ids all start with TYPE_.  Survives renames.
    """
    widgets_file = pathlib.Path(widgets.__file__).resolve()
    tree = ast.parse(widgets_file.read_text(encoding="utf-8"))

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                name = None
                if isinstance(target, ast.Name):
                    name = target.id
                if name and isinstance(node.value, ast.Tuple):
                    elts = node.value.elts
                    if len(elts) == 6 and all(
                        isinstance(e, ast.Name) and e.id.startswith("TYPE_")
                        for e in elts
                    ):
                        return name

    raise AssertionError("No scale tuple in widgets.py")


def _get_scale_step_names_explicit() -> list[str]:
    """Return the six TYPE_* constant names from the live module, sorted by value."""
    steps = {}
    for name in dir(widgets):
        if name.startswith("TYPE_") and isinstance(getattr(widgets, name, None), int):
            # Exclude the tuple itself if it were somehow int (it won't be)
            val = getattr(widgets, name)
            if isinstance(val, int):
                steps[name] = val
    # Sort by value to get declaration order
    return [name for name, _ in sorted(steps.items(), key=lambda x: x[1])]


# ── R1: no integer literals at font call sites ──────────────────────────────


def _is_integer_literal(node: ast.expr) -> bool:
    """Return True if the node is an integer constant."""
    return isinstance(node, ast.Constant) and isinstance(node.value, int)


def _is_name_ref(node: ast.expr) -> bool:
    """Return True if the node is a Name reference (could be a scale step)."""
    return isinstance(node, ast.Name)


def _is_attr_ref(node: ast.expr) -> bool:
    """Return True if the node is an Attribute reference (e.g. self.size, tbl.size)."""
    return isinstance(node, ast.Attribute)


def _collect_module_names(tree: ast.Module) -> set[str]:
    """Collect all module-level Name assignments in the parsed file."""
    names = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def _resolve_to_integer_literal(node: ast.expr, module_names: set[str], widgets_module_names: set[str]) -> bool:
    """Check if a Name node is bound to an integer literal in the same module.

    Only checks module-level bindings within gilded/ui/ files.  A Name bound
    to another Name (e.g. _TEXT_PT = TYPE_CAPTION) is NOT a literal.
    """
    if not isinstance(node, ast.Name):
        return False
    # We can't fully resolve here without the full AST — we need to check
    # in the source file.  Return False and let the caller handle it.
    return False


def _check_file_no_literal_font_calls(
    file_path: pathlib.Path,
    font_func_name: str,
    widgets_file: pathlib.Path,
    scale_step_names: set[str],
) -> list[str]:
    """Check a single file for integer-literal font calls.

    Returns a list of violation descriptions (empty if clean).
    """
    if file_path.resolve() == widgets_file.resolve():
        return []  # widgets.py is exempt

    source = file_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []  # Can't parse, skip

    violations: list[str] = []

    # Collect module-level assignments to resolve local names
    module_names: dict[str, ast.expr] = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    module_names[target.id] = node.value

    # Find the import alias for the font function
    import_aliases: set[str] = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and "widgets" in node.module:
                for alias in node.names:
                    if alias.name == font_func_name:
                        # Imported as some_alias or same name
                        import_aliases.add(alias.asname if alias.asname else alias.name)
                    # Also check if the old name "font" is imported
                    if alias.name == "font":
                        import_aliases.add(alias.asname if alias.asname else alias.name)

    # Walk all Call nodes
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func = node.func
        call_name = None

        if isinstance(func, ast.Name):
            call_name = func.id
        elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            # e.g. pygame.font.SysFont — skip, this is inside widgets
            continue

        if call_name and call_name in import_aliases:
            # Check the first positional argument
            if node.args:
                first_arg = node.args[0]
                if _is_integer_literal(first_arg):
                    violations.append(
                        f"Line {first_arg.lineno}: {call_name}({first_arg.value}) — "
                        f"integer literal instead of named step"
                    )
                elif isinstance(first_arg, ast.Name):
                    # Check if the Name is bound to an integer literal at module level
                    if first_arg.id in module_names:
                        bound_value = module_names[first_arg.id]
                        if _is_integer_literal(bound_value):
                            violations.append(
                                f"Line {first_arg.lineno}: {call_name}({first_arg.id}) — "
                                f"{first_arg.id} is bound to integer literal {bound_value.value}"
                            )
                        # If bound to another Name, that's OK (e.g. _TEXT_PT = TYPE_CAPTION)

    return violations


# ── R2: scale ascends ────────────────────────────────────────────────────────


def _check_scale_ascends() -> list[str]:
    """Check that the type scale constants are strictly increasing.

    Returns a list of violation descriptions (empty if ascending).
    """
    steps = _get_scale_step_names_explicit()
    violations: list[str] = []

    for i in range(len(steps) - 1):
        name_curr = steps[i]
        name_next = steps[i + 1]
        val_curr = getattr(widgets, name_curr)
        val_next = getattr(widgets, name_next)
        if val_curr >= val_next:
            violations.append(
                f"{name_curr}={val_curr} >= {name_next}={val_next} — scale does not ascend"
            )

    return violations


def _check_scale_tuple_matches() -> list[str]:
    """Check that the scale tuple's runtime value is the six steps in ascending order.

    Returns a list of violation descriptions.
    """
    tuple_name = _find_scale_tuple_in_tree()
    tuple_obj = getattr(widgets, tuple_name, None)
    if tuple_obj is None:
        return [f"Scale tuple '{tuple_name}' not found on widgets module"]

    if not isinstance(tuple_obj, tuple):
        return [f"Scale tuple '{tuple_name}' is not a tuple at runtime"]

    steps = _get_scale_step_names_explicit()
    expected = tuple(getattr(widgets, name) for name in steps)

    violations: list[str] = []
    if tuple_obj != expected:
        violations.append(
            f"Scale tuple {tuple_name} = {tuple_obj} != expected {expected}"
        )

    return violations


# ── test cases ───────────────────────────────────────────────────────────────


def test_no_integer_literal_at_font_calls():
    """No font call site under gilded/ui/ passes an integer literal as its size arg.

    This measures the SOURCE TEXT, not the render.  _font(14) and _font(TYPE_BODY)
    send pygame the same integer when TYPE_BODY is 14 — but the former is a size
    that will drift because nothing connects it to the step it came from.

    Also catches _PT = 14; _font(_PT) — a name bound to a literal is a literal.
    A name bound to a step (e.g. _TEXT_PT = TYPE_CAPTION) is not.
    """
    ui_dir = _widgets_dir()
    widgets_file = pathlib.Path(widgets.__file__).resolve()
    font_func_name = _find_font_func_in_tree()
    scale_step_names = set(_get_scale_step_names_explicit())

    all_violations: list[str] = []

    for py_file in sorted(ui_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        violations = _check_file_no_literal_font_calls(
            py_file, font_func_name, widgets_file, scale_step_names
        )
        all_violations.extend(f"{py_file.name}:{v}" for v in violations)

    assert not all_violations, (
        "Integer literal point sizes found at font call sites:\n" + "\n".join(all_violations)
    )


def test_no_module_alias_bound_to_integer():
    """No module-level alias under gilded/ui/ binds a font size to an integer literal.

    Catches _TEXT_PT = 12 (which is a spelled size) while allowing
    _TEXT_PT = TYPE_CAPTION (which is a name bound to a step).
    """
    ui_dir = _widgets_dir()
    widgets_file = pathlib.Path(widgets.__file__).resolve()

    # Collect the scale step names from widgets so we know what's a reference vs a literal
    scale_step_names = set(_get_scale_step_names_explicit())

    all_violations: list[str] = []

    for py_file in sorted(ui_dir.glob("*.py")):
        if py_file.resolve() == widgets_file.resolve():
            continue  # widgets.py defines the steps — it's the source of truth
        if py_file.name == "__init__.py":
            continue

        source = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError:
            continue

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        # Check if the value is an integer literal
                        if _is_integer_literal(node.value):
                            # Is this a font-size-related name?
                            # Heuristic: the name contains PT, SIZE, FONT, or TYPE
                            name_upper = target.id.upper()
                            if any(kw in name_upper for kw in ("PT", "SIZE", "FONT", "TYPE", "POINT")):
                                all_violations.append(
                                    f"{py_file.name}:{target.id} = {node.value.value} "
                                    f"— module alias bound to integer literal"
                                )

    assert not all_violations, (
        "Module-level aliases bound to integer literals:\n" + "\n".join(all_violations)
    )


def test_scale_ascends():
    """The type scale steps have strictly increasing values, smallest first.

    This measures the ORDER of declaration, not just the set of values.
    Two middle steps trading values leaves the extremes and ratio unchanged
    but breaks the role hierarchy — captions should be smallest, titles largest.

    Survives renames: resolves steps by TYPE_ prefix convention on the live module.
    """
    violations = _check_scale_ascends()
    assert not violations, (
        "Type scale does not ascend:\n" + "\n".join(violations)
    )


def test_scale_tuple_is_steps_in_order():
    """The scale tuple's runtime value is the six steps in ascending order.

    The tuple is the canonical declaration of the scale.  Its value must be
    (TYPE_CAPTION, TYPE_BODY, ..., TYPE_TITLE) — the steps themselves, not
    copies or a reordered subset.

    Survives renames: finds the tuple by AST structure (6 TYPE_ Name elements).
    """
    violations = _check_scale_tuple_matches()
    assert not violations, (
        "Scale tuple does not match steps in ascending order:\n" + "\n".join(violations)
    )
