"""pytest hooks to run intel tests first (so -x exits early during mutation testing)."""
import re


def pytest_collection_modifyitems(items):
    """Sort test items so intel tests run first for faster mutation kills."""
    def sort_key(item):
        f = item.fspath.basename
        if f.startswith("test_intel"):
            return (0, f, item.name)
        return (1, f, item.name)
    items.sort(key=sort_key)
