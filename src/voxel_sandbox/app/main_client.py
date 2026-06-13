from __future__ import annotations

import logging

from voxel_sandbox.app.bootstrap import describe_runtime
from voxel_sandbox.app.settings import AppSettings

LOGGER = logging.getLogger(__name__)


def run_client(settings: AppSettings, *, smoke_test: bool = False) -> int:
    LOGGER.info("Starting client shell: %s", describe_runtime(settings))
    if smoke_test:
        LOGGER.info("Client smoke test complete")
        return 0
    raise RuntimeError("Graphical client shell is installed by the next Phase 1 item")
