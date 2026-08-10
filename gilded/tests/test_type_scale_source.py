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
import pathlib

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
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    func = child.func
                    if isinstance(func, ast.Attribute) and func.attr == "SysFont":
                        return node.name

    raise AssertionError("No function in widgets.py calls pygame.font.SysFont")


def _find_scale_tuple_in_tree() -> str:
    """Find the name of the tuple in widgets.py that holds the six scale steps.

    Resolves by property: a module-level Name whose value is a Tuple of 6
    ast.Name elements that all resolve to int constants on the live module.
    Survives renames.
    """
    widgets_file = pathlib.Path(widgets.__file__).resolve()
    tree = ast.parse(widgets_file.read_text(encoding="utf-8"))

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Tuple):
                    elts = node.value.elts
                    if len(elts) == 6 and all(isinstance(e, ast.Name) for e in elts):
                        # Verify these names resolve to int constants at runtime
                        names = [e.id for e in elts]
                        if all(isinstance(getattr(widgets, n, None), int) for n in names):
                            return target.id

    raise AssertionError("No scale tuple in widgets.py")


def _get_scale_step_names_from_tuple() -> list[str]:
    """Return the six step names from the scale tuple, in tuple element order.

    Resolves the tuple by AST structure (6 Name elements resolving to int
    constants), then extracts the Name ids in the order they appear in the tuple.
    """
    widgets_file = pathlib.Path(widgets.__file__).resolve()
    tree = ast.parse(widgets_file.read_text(encoding="utf-8"))

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Tuple):
                    elts = node.value.elts
                    if len(elts) == 6 and all(isinstance(e, ast.Name) for e in elts):
                        names = [e.id for e in elts]
                        if all(isinstance(getattr(widgets, n, None), int) for n in names):
                            return names

    raise AssertionError("Could not find scale step names from tuple")


def _get_scale_step_names_from_source() -> list[str]:
    """Return the six step names in the order they are assigned in the source.

    Scans module-level assignments in source-file order.  A step is a Name
    assigned a constant integer, where the Name is also referenced by the
    scale tuple.  Returns them in declaration order.
    """
    tuple_name = _find_scale_tuple_in_tree()
    step_names_set = set(_get_scale_step_names_from_tuple())

    widgets_file = pathlib.Path(widgets.__file__).resolve()
    tree = ast.parse(widgets_file.read_text(encoding="utf-8"))

    declared_in_order: list[str] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in step_names_set:
                    if isinstance(node.value, ast.Constant) and isinstance(
                        node.value.value, int
                    ):
                        declared_in_order.append(target.id)

    return declared_in_order


# ── R1: no integer literals at font call sites ──────────────────────────────


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
        return []

    # Find imports of the font function
    import_aliases: set[str] = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and "widgets" in node.module:
                for alias in node.names:
                    if alias.name == font_func_name:
                        import_aliases.add(alias.asname or alias.name)

    # Collect module-level Name -> value mappings
    module_bindings: dict[str, ast.expr] = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    module_bindings[target.id] = node.value

    violations: list[str] = []

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
                if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, int):
                    violations.append(
                        f"Line {first_arg.lineno}: {call_name}({first_arg.value}) — "
                        f"integer literal instead of named step"
                    )
                elif isinstance(first_arg, ast.Name):
                    # Check if the Name is bound to an integer literal at module level
                    if first_arg.id in module_bindings:
                        bound_value = module_bindings[first_arg.id]
                        if isinstance(bound_value, ast.Constant) and isinstance(
                            bound_value.value, int
                        ):
                            violations.append(
                                f"Line {first_arg.lineno}: {call_name}({first_arg.id}) — "
                                f"{first_arg.id} is bound to integer literal {bound_value.value}"
                            )
                        # If bound to another Name, that's OK (e.g. _TEXT_PT = TYPE_CAPTION)

    return violations


# ── R2: scale ascends ────────────────────────────────────────────────────────


def _check_scale_tuple_matches() -> list[str]:
    """Check that the scale tuple's runtime value matches the six steps in declaration order.

    Declaration order is resolved from the source file (not the tuple), so this
    catches a tuple whose element order diverges from how the steps are declared.

    Returns a list of violation descriptions.
    """
    tuple_name = _find_scale_tuple_in_tree()
    tuple_obj = getattr(widgets, tuple_name, None)
    if tuple_obj is None:
        return [f"Scale tuple '{tuple_name}' not found on widgets module"]

    if not isinstance(tuple_obj, tuple):
        return [f"Scale tuple '{tuple_name}' is not a tuple at runtime"]

    decl_names = _get_scale_step_names_from_source()
    expected = tuple(getattr(widgets, name) for name in decl_names)

    violations: list[str] = []
    if tuple_obj != expected:
        violations.append(
            f"Scale tuple {tuple_name} = {tuple_obj} != expected {expected} "
            f"(from declaration order {decl_names})"
        )

    return violations


def _check_declaration_order_ascends() -> list[str]:
    """Check that the six steps are declared in ascending order by value.

    Resolves declaration order from the source file (not the tuple).

    Returns a list of violation descriptions.
    """
    decl_names = _get_scale_step_names_from_source()
    violations: list[str] = []
    for i in range(len(decl_names) - 1):
        name_curr = decl_names[i]
        name_next = decl_names[i + 1]
        val_curr = getattr(widgets, name_curr)
        val_next = getattr(widgets, name_next)
        if val_curr >= val_next:
            violations.append(
                f"Declaration order: {name_curr}={val_curr} precedes "
                f"{name_next}={val_next} — declarations must ascend"
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
    scale_step_names = set(_get_scale_step_names_from_tuple())

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
    scale_step_names = set(_get_scale_step_names_from_tuple())

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
                        name = target.id
                        if name in scale_step_names:
                            continue  # This is a step definition, not an alias
                        # Check if the value is an integer literal
                        if isinstance(node.value, ast.Constant) and isinstance(
                            node.value.value, int
                        ):
                            # Only flag if the name looks like a font-related size
                            if any(kw in name.lower() for kw in ("pt", "size", "font", "type")):
                                all_violations.append(
                                    f"{py_file.name}: {name} = {node.value.value} "
                                    f"(integer literal instead of scale step)"
                                )

    assert not all_violations, (
        "Module-level aliases bound to integer literals:\n" + "\n".join(all_violations)
    )


def test_scale_ascends():
    """The six scale steps must be declared in ascending order by value.

    Resolves declaration order from the source file (not the tuple), so
    this catches declarations written out of ascending order even when
    the tuple itself is correct.
    """
    violations = _check_declaration_order_ascends()
    assert not violations, "\n".join(violations)


def test_scale_tuple_is_steps_in_order():
    """The scale tuple must equal the six steps in their declaration order.

    Declaration order is resolved from the source file, not derived from
    the tuple itself.  This catches a tuple whose element order diverges
    from how the steps are declared in the source.
    """
    violations = _check_scale_tuple_matches()
    assert not violations, (
        "Scale tuple does not match steps in declaration order:\n" + "\n".join(violations)
    )
