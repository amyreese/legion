# Copyright 2020 John Reese
# Licensed under the MIT license

import logging
import re
from types import FunctionType
from typing import (
    Set,
    List,
    Type,
    Any,
    Tuple,
    Dict,
    Pattern,
    TypeVar,
    Callable,
    TYPE_CHECKING,
)

from discord import Client, Message

from legion.units import import_units

if TYPE_CHECKING:
    from legion.bot import Bot

ALL_UNITS: Set[Type["Unit"]] = set()
COMMANDS: Dict[str, Tuple[str, str, Pattern, str]] = {}
LOG = logging.getLogger(__name__)

Event = Any

T = TypeVar("T", bound=FunctionType)


def command(
    args: str = r"(.*)", name: str = "", description: str = ""
) -> Callable[[T], T]:
    """Decorator for automating command/args declaration and dispatch."""

    def wrapper(fn: T) -> T:
        if fn.__name__ == fn.__qualname__:
            # TODO: maybe handle raw functions
            raise ValueError("@command takes class methods only")

        cmd = name.casefold() if name else fn.__name__.casefold()
        if cmd in COMMANDS:
            unit, _regex, _description = COMMANDS[name]
            raise ValueError(f'command "{cmd}" already claimed by {unit.__name__}')

        cls_name = fn.__qualname__.split(".")[0]
        fn_name = fn.__name__

        COMMANDS[cmd] = (cls_name, fn_name, re.compile(args), description)

        return fn

    return wrapper


class Unit:
    ENABLED = True

    def __init_subclass__(cls):
        ALL_UNITS.add(cls)

    def __init__(self, bot: "Bot", client: Client):
        self.bot = bot
        self.client = client
        self.started = False

    @classmethod
    def load(cls, *, enabled_only: bool = True) -> List[Type["Unit"]]:
        """Return a fresh instance of all available units"""
        import_units()

        if enabled_only:
            units = {u for u in ALL_UNITS if u.ENABLED}
        else:
            units = ALL_UNITS

        return list(units)

    async def start(self) -> None:
        """
        The main entry point for units to run background tasks.

        This will only be called once by the main Edi framework, so any
        ongoing processing will require implementation of a run loop or
        dependence on another source of events.
        """
        self.started = True
        LOG.debug("unit %s ready", self)

    async def stop(self) -> None:
        """
        Signal that any async work should be stopped.

        This will be called by the main Edi framework when the service needs
        to exit.  Units should keep track of any async tasks currently pending
        and cancel them here.  Edi assumes this unit is completely stopped
        once this coroutine is completed."""
        pass

    async def dispatch(self, event: Event) -> None:
        """
        Entry point for events received from the Slack RTM API.

        Any messages from the RTM API will be sent here, to be dispatched
        appropriately.  Default behavior is to look for a matching "on_event"
        method for the given message type, and will call that if found.
        """

        method = getattr(self, f"on_{event.type}", self.on_default)
        await method(event)

    async def on_default(self, event: Event) -> None:
        """Default message handler when specific handlers aren't defined."""
        pass
