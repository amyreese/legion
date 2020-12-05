# Copyright 2020 John Reese
# Licensed under the MIT license

import asyncio
import logging
import time
from typing import Optional, List, Any

from discord import Message
from munch import Munch
from peony import PeonyClient
from peony.exceptions import PeonyException

from legion.unit import Unit, command

LOG = logging.getLogger(__name__)


class Twitter(Unit):
    async def start(self) -> None:
        await super().start()

        self.config = self.bot.config.twitter
        self.task = None
        if not all(
            [
                self.config.consumer_key,
                self.config.consumer_secret,
                self.config.access_key,
                self.config.access_secret,
            ]
        ):
            LOG.warning("missing twitter credentials")
            return

        # logging.getLogger("peony").setLevel(logging.WARNING)
        self.twitter = PeonyClient(
            consumer_key=self.config.consumer_key,
            consumer_secret=self.config.consumer_secret,
            access_token=self.config.access_key,
            access_token_secret=self.config.access_secret,
        )

        self.task = asyncio.ensure_future(self.timeline())

    async def stop(self) -> None:
        if self.task:
            self.task.cancel()

    async def timeline(self) -> None:
        """Run loop, poll for updates and push new posts to slack."""

        if not self.config.timeline_channels:
            LOG.info(f"no twitter timeline channels configured")
            return

        LOG.debug("connecting to twitter API")
        me = await self.twitter.user
        LOG.info(f"connected to twitter as @{me.screen_name}")

        since_id = None

        while True:
            ts = time.time()

            try:
                kwargs = {"count": 20, "include_entities": False}
                if since_id is None:
                    kwargs["count"] = 1
                else:
                    kwargs["since_id"] = since_id

                LOG.debug("checking timeline for updates")
                tweets = await self.twitter.api.statuses.home_timeline.get(**kwargs)
                if tweets:
                    LOG.info(f"timeline:")
                    for tweet in reversed(tweets):
                        LOG.info(f" @{tweet.user.screen_name}: {tweet.text}")
                    tweet = tweets[-1]

                    if (
                        since_id is not None
                        and tweet.user.screen_name != me.screen_name
                    ):
                        await self.announce(tweet)

                    since_id = tweet.id_str

                else:
                    LOG.debug(f"timeline empty")

            except PeonyException:
                LOG.exception("timeline update failed")

            except Exception:
                LOG.exception(r"¯\_(ツ)_/¯")

            finally:
                wait = (ts + 90) - time.time()
                if wait > 0:
                    LOG.debug(f"sleeping for {wait}s")
                    await asyncio.sleep(wait)

    def tweet_url(self, tweet: Any) -> str:
        return f"🐓 https://twitter.com/{tweet.user.screen_name}/status/{tweet.id_str}"

    async def announce(self, tweet: Any) -> None:
        LOG.info(f"twitter announce {tweet}")
        text = self.tweet_url(tweet)
        for guild in self.client.guilds:
            channels = self.config.timeline_channels.get(guild.name, [])
            for channel in (c for c in guild.channels if c.name in channels):
                await channel.send(text)

    async def update(self, status: str) -> Optional[Munch]:
        try:
            response = await self.twitter.api.statuses.update.post(status=status)
            return response

        except PeonyException:
            LOG.exception("failed to update status")
            return None

    @command(usage="<status>", description="twitter a new tweet")
    async def tweet(self, message: Message, status: str) -> str:
        tweet = await self.update(status)
        if tweet is not None:
            return self.tweet_url(tweet)
