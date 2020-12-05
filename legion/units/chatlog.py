# Copyright 2020 John Reese
# Licensed under the MIT license

from datetime import datetime
from pathlib import Path
from typing import Tuple

from discord import DMChannel, Message, RawReactionActionEvent

from legion.unit import Unit


class Chatlog(Unit):
    async def start(self):
        await super().start()
        self.root = self.bot.config.chatlog.root
        self.local = self.bot.config.chatlog.path
        self.template = self.bot.config.chatlog.format

    def log_path(self, **kwargs) -> Path:
        return self.root / Path(self.local.format(**kwargs))

    def format_dt(self, dt: datetime) -> Tuple[str, str]:
        date = dt.strftime(r"%Y-%m-%d")
        time = dt.strftime(r"%H:%M:%S")
        return date, time

    async def on_message(self, message: Message) -> None:
        if isinstance(message.channel, DMChannel):
            server = "dm"
            channel = message.author.display_name
        elif message.guild:
            server = message.guild.name
            channel = message.channel.name

        date, time = self.format_dt(message.created_at)
        user = message.author.display_name
        text = message.clean_content

        line = self.template.format(
            server=server,
            channel=channel,
            date=date,
            time=time,
            user=user,
            message=text,
        )

        filename = self.log_path(server=server, channel=channel, date=date)
        filename.parent.mkdir(parents=True, exist_ok=True)
        with open(filename, "a") as f:
            f.write(line)
