# Copyright 2020 John Reese
# Licensed under the MIT license

import logging
import os.path
from importlib import import_module, reload
from pathlib import Path
from types import ModuleType
from typing import List, Set

LOG = logging.getLogger(__name__)
MODULES: Set[ModuleType] = set()


def import_units(root: Path = None) -> List[ModuleType]:
    """Find and import units in this path."""
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
        MODULES.add(module)
    return list(MODULES)


def reload_units() -> List[ModuleType]:
    """Reload any previously imported modules"""
    old_modules = list(MODULES)
    MODULES.clear()

    for module in old_modules:
        LOG.debug(f"reloading {module}")
        new_module = reload(module)
        LOG.debug(f"new module {module}")
        MODULES.add(new_module)

    return list(MODULES)
