# Copyright 2017 John Reese
# Licensed under the MIT license

import logging
import random
import textwrap

from discord import Message, Reaction, User, RawReactionActionEvent

from legion.unit import Unit, COMMANDS, command

LOG = logging.getLogger(__name__)

# http://masseffect.wikia.com/wiki/Legion/Unique_dialogue
HUMOR = [
    "These facilities are inadequate.",
    "Metal detectors are inconvenient.",
    "Tactical disadvantage. Recommend orbital fire support.",
    "This platform is not available for experimentation.",
    "Your operating system is unstable. You will fail.",
    "The first thing a god masters is itself.",
    "Our analysis of organic humour suggests an 87.3% chance "
    'that you expect us to respond with, "You are only human."',
    "Does this unit have a soul?",
]
REACTION = "This platform is immune to organic disease."


class Help(Unit):
    @command(description="show command details", usage="[command]")
    async def help(self, message: Message, phrase: str) -> str:
        phrase = phrase.strip().lower()
        detail = bool(phrase)
        if not phrase:
            command_list = list(COMMANDS.keys())
        else:
            names = phrase.split()
            command_list = [c for c in COMMANDS if c in names]
            if not command_list:
                return "No matching commands"

        helps = []
        for name in sorted(command_list):
            command = COMMANDS[name]
            description = textwrap.dedent(command.description)
            usage = command.usage
            if detail:
                helps.extend(
                    [
                        f"{name} {usage}",
                        f"  {description}",
                        f"  argument regex: {command.args.pattern!r}",
                    ]
                )
            elif not command.admin_only:
                description = description.splitlines()[0].strip()
                if usage:
                    helps.append(f"{name} {usage}: {description}")
                else:
                    helps.append(f"{name}: {description}")

        text = "\n".join(helps)
        text = f"```\n{text}\n```"

        if len(text) > 1000:
            # todo: IM user with full list of commands
            return ""

        return text

    @command(description="<insert witty help text here>")
    async def hello(self, message: Message, phrase: str) -> str:
        return random.choice(HUMOR)

    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        if payload.emoji.name not in ["💩", "🦠", "🤢", "🤮"]:
            return

        channel = self.client.get_channel(payload.channel_id)
        message = await channel.history().get(id=payload.message_id)
        if message.author.id == self.client.user.id and len(message.reactions) < 2:
            await message.channel.send(REACTION)
