# Copyright 2020 John Reese
# Licensed under the MIT license

import logging
import sys
import time

from humanize import naturaldelta
from discord import Message

from legion.unit import ALL_UNITS, COMMANDS
from legion.unit import Unit, command
from legion.units import reload_units

LOG = logging.getLogger(__name__)


class Core(Unit):
    @command(args="", description="reload units", admin_only=True)
    async def reload(self, message: Message) -> str:
        LOG.info("deconstituting units")
        units = self.bot.units.copy()
        self.bot.units.clear()
        for unit in units.values():
            LOG.info(f"stopping unit {unit}")
            await unit.stop()

        LOG.info("clearing ALL_UNITS and COMMANDS")
        ALL_UNITS.clear()
        COMMANDS.clear()

        LOG.info("reloading unit modules")
        new_modules = reload_units()
        LOG.info(f"{len(new_modules)} fresh modules: {new_modules}")

        LOG.info("reconstituting units")
        unit_types = Unit.load()
        units = {ut.__name__: ut(self.bot, self.bot.client) for ut in unit_types}
        for unit in units.values():
            LOG.info(f"starting unit {unit}")
        self.bot.units = units

        return "Shepard-Commander"

    @command(args="", description="bot uptime")
    async def uptime(self, message: Message) -> str:
        duration = time.monotonic() - self.bot.start_time
        return f"up {naturaldelta(duration)}"