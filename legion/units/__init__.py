# Copyright 2020 John Reese
# Licensed under the MIT license

import logging
import os.path
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import List

LOG = logging.getLogger(__name__)


def import_units(root: Path = None) -> List[ModuleType]:
    """Find and import units in this path."""
    modules: List[ModuleType] = []

    if root is None:
        root = Path(__file__)
    if not root.is_dir():
        root = Path(root.parent)  # appease mypy, Path.parents -> PurePath

    LOG.debug(f"Searching for units in {root}...")
    for path in root.glob("*.py"):
        name = path.stem
        if name.startswith("_"):
            continue
        LOG.debug(f"Loading unit {name}")
        module = import_module(f"{__name__}.{name}")
        modules.append(module)
    return modules
