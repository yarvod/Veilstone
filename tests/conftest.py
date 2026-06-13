from __future__ import annotations

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        suite = pytest.mark.integration if "integration" in item.path.parts else pytest.mark.unit
        item.add_marker(suite)
