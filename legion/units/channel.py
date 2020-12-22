# Copyright 2020 John Reese
# Licensed under the MIT license

from typing import Optional

from discord import DMChannel, Message, DiscordException

from legion.unit import Unit, command


class Channel(Unit):
    @command(usage="<topic>", description="set channel topic")
    async def topic(self, message: Message, topic: str) -> Optional[str]:
        if isinstance(message.channel, DMChannel):
            return ("Your operating system is unstable. You will fail.",)

        topic = topic.strip()
        user = message.author
        reason = f"{user.mention} sent !topic {topic!r}"

        try:
            await message.channel.edit(topic=topic)
            return f"_set topic to {topic!r}_"
        except DiscordException as e:
            LOG.error(f"!topic by {user.id} failed: {e}")
            return str(e)
