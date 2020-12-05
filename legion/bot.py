# Copyright 2020 John Reese
# Licensed under the MIT license

import asyncio
import logging
import re
import time
import signal
from functools import wraps
from typing import Union, Callable, Optional, Match

from discord import (
    Client,
    Intents,
    Message,
    Reaction,
    Member,
    User,
    DMChannel,
    RawReactionActionEvent,
)

from legion.config import Config
from legion.unit import Unit, COMMANDS

try:
    import uvloop
except ImportError:
    uvloop = None


LOG = logging.getLogger(__name__)


def dispatch(fn):
    name = fn.__name__

    @wraps(fn)
    async def wrapped(self, *args, **kwargs):
        result = await fn(self, *args, **kwargs)
        if result is not False:
            for unit in self.units.values():
                method = getattr(unit, name, None)
                if asyncio.iscoroutinefunction(method):
                    try:
                        LOG.debug(f"dispatch {name} to {method}")
                        await method(*args, **kwargs)
                    except Exception:
                        LOG.exception(f"error from unit {unit}.{name}")

    return wrapped


class Bot:
    loop: asyncio.AbstractEventLoop

    def __init__(self, config: Config):
        self.config = config
        self.client = Client(intents=Intents.default())

        unit_types = Unit.load()
        self.units = {ut.__name__: ut(self, self.client) for ut in unit_types}

        if uvloop and config.bot.uvloop:
            LOG.info("enabling uvloop")
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

        self.loop = asyncio.get_event_loop()
        if config.bot.debug:
            self.loop.set_debug(True)

    def start(self):
        LOG.debug("starting bot event loop")
        self.loop.add_signal_handler(signal.SIGINT, self.sigterm)
        self.loop.add_signal_handler(signal.SIGTERM, self.sigterm)

        self.start_time = time.monotonic()
        self.task = asyncio.ensure_future(self.run(), loop=self.loop)
        self.loop.run_forever()

    def sigterm(self) -> None:
        """Handle Ctrl-C or SIGTERM by stopping the event loop nicely."""
        LOG.warning("Signal received, stopping execution")
        asyncio.ensure_future(self.stop(), loop=self.loop)

    async def run(self):
        for key in dir(self):
            if key.startswith("on_"):
                prop = getattr(self, key, None)
                LOG.debug(f"hooking {key}: {prop}")
                if asyncio.iscoroutinefunction(prop):
                    self.client.event(prop)

        LOG.info("starting discord client")
        await self.client.start(self.config.discord.token)
        LOG.info("discord client started")

    async def stop(self):
        try:
            for unit in list(self.units.values()):
                LOG.info(f"stopping {unit}")
                await unit.stop()
                self.units.pop(unit)

            LOG.info("closing discord client")
            await self.client.close()
        finally:
            self.loop.stop()
            LOG.info("does this... unit... have...")

    def check_command(self, message: Message) -> Optional[Match]:
        if message.author.id == self.client.user.id:
            return False

        name = self.client.user.name
        nick = name

        if isinstance(message.channel, DMChannel):
            match = re.match(
                rf"(?P<mention>@?{name}:?)?\s*(?P<command>\w+)(?:\s+(?P<args>.+))?",
                message.clean_content,
                re.IGNORECASE,
            )
            if match:
                return match

            return False

        if message.guild:
            nick = message.guild.me.display_name

        match = re.match(
            rf"(?P<mention>@?(?:{name}|{nick}):?)\s+(?P<command>\w+)(?:\s+(?P<args>.+))?",
            message.clean_content,
            re.IGNORECASE,
        )
        if match:
            return match

        return False

    async def dispatch_command(self, message: Message, match: Match):
        mention, name, args = match.groups()
        name = name.casefold()

        if name not in COMMANDS:
            LOG.debug(
                f"unknown command from {message.author} on {message.channel}: "
                f"{name!r} {args!r}"
            )
            return

        command = COMMANDS[name]

        if command.admin_only and message.author.id not in self.config.bot.admins:
            LOG.warning(
                f"user {message.author}/{message.author.id} "
                f"requested admin command {name}"
            )
            await message.channel.send(f"user {message.author.id} is not an admin")
            return

        if command.class_name not in self.units:
            LOG.error(f"unknown unit {command.class_name!r}")
            return

        unit = self.units[command.class_name]
        method = getattr(unit, command.method_name, None)
        if method is None:
            LOG.error(f"unknown unit method {command.class_name}.{command.method_name}")
            return

        match = command.args.fullmatch(args or "")
        if not match:
            await message.channel.send(
                f"{message.author.mention} invalid arguments for {name!r}"
            )
            return

        kwargs = match.groupdict()
        if kwargs:
            LOG.debug(f"COMMAND {method.__qualname__}({message}, **{kwargs})")
            response = await method(message, **kwargs)
        else:
            pargs = match.groups()
            LOG.debug(f"COMMAND {method.__qualname__}({message}, *{pargs})")
            response = await method(message, *pargs)

        if response:
            await message.channel.send(response)

    async def on_ready(self):
        LOG.info(f"discord client ready as user {self.client.user}")

        for unit in self.units.values():
            if not unit.started:
                LOG.debug(f"starting unit {unit}")
                await unit.start()

    @dispatch
    async def on_message(self, message: Message) -> None:
        LOG.debug(f"message received: {message}")

        match = self.check_command(message)
        if match:
            await self.dispatch_command(message, match)
            return False

    @dispatch
    async def on_reaction_add(self, reaction: Reaction, user: User) -> None:
        LOG.debug(f"reaction added by {user}: {reaction}")

    @dispatch
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent) -> None:
        LOG.debug(f"raw reaction: {payload}")
