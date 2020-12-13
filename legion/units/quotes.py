# Copyright 2020 John Reese
# Licensed under the MIT license


import logging
import time
from contextlib import AsyncExitStack
from datetime import datetime
from typing import List

import aiosqlite
from attr import dataclass
from discord import Message, User, DMChannel, RawReactionActionEvent

from legion.config import QuotesConfig
from legion.unit import Unit, command

LOG = logging.getLogger(__name__)


@dataclass
class Quote:
    id: int
    server: str
    channel: str
    username: str
    added_by: str
    added_at: datetime
    text: str

    @classmethod
    def new(
        cls, server: str, channel: str, username: str, added_by: str, text: str
    ) -> "Quote":
        now = datetime.now()
        now = now.replace(microsecond=0)
        return Quote(
            id=0,
            server=server,
            channel=channel,
            username=username,
            added_by=added_by,
            added_at=now,
            text=text,
        )


class QuoteDB:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def __aenter__(self) -> "QuotesDB":
        async with self.db.cursor() as cursor:
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS quotes (
                    id INTEGER PRIMARY KEY,
                    server INTEGER,
                    channel TEXT,
                    username TEXT,
                    added_by TEXT,
                    added_at TIMESTAMP,
                    quote TEXT
                )
                """
            )
            await cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS quote_server
                ON quotes (server)
                """
            )
            await cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS quote_channel
                ON quotes (channel)
                """
            )
            await cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS quote_username
                ON quotes (username)
                """
            )

        return self

    async def __aexit__(self, *args) -> None:
        pass

    async def add(self, quote: Quote) -> int:
        query = """
            INSERT INTO quotes
            VALUES (NULL, ?, ?, ?, ?, ?, ?)
        """

        async with self.db.execute(
            query,
            [
                quote.server,
                quote.channel,
                quote.username,
                quote.added_by,
                quote.added_at,
                quote.text,
            ],
        ) as cursor:
            quote.id = cursor.lastrowid
            return quote.id

    async def get(self, server: int, qid: int) -> Quote:
        query = """
            SELECT * FROM quotes
            WHERE server = ? AND id = ?
        """
        async with self.db.execute(query, [server, qid]) as cursor:
            if not cursor.rowcount:
                raise KeyError(f"quote id {qid} not found")
            row = await cursor.fetchone()
            return Quote(*row)

    async def find(
        self,
        server: int,
        channel: str,
        username: str = "",
        fuzz: bool = False,
        limit: int = 0,
    ) -> List[Quote]:
        if username:
            query = """
                SELECT * FROM quotes
                WHERE server = ? AND channel = ? AND username LIKE ?
                ORDER BY id DESC
            """
            params = [server, channel, f"{username[:5]}%" if fuzz else username]
        else:
            query = """
                SELECT * FROM quotes
                WHERE server = ? AND channel = ?
                ORDER BY id DESC
            """
            params = [server, channel]

        if limit > 0:
            query += " LIMIT ? "
            params += [limit]

        async with self.db.execute(query, params) as cursor:
            result: List[Quote] = []
            async for row in cursor:
                result.append(Quote(*row))
            return result

    async def random(
        self, server: int, channel: str, username: str = "", fuzz: bool = False
    ) -> Quote:
        if username:
            query = """
                SELECT * FROM quotes
                WHERE server = ? AND channel = ? AND username LIKE ?
                ORDER BY random()
                LIMIT 1
            """
            params = [server, channel, f"{username[:5]}%" if fuzz else username]
        else:
            query = """
                SELECT * FROM quotes
                WHERE server = ? AND channel = ?
                ORDER BY random()
                LIMIT 1
            """
            params = [server, channel]

        async with self.db.execute(query, params) as cursor:
            if not cursor.rowcount:
                return Quote.new(
                    server, channel, "nobody", "nobody", "say something funny"
                )
            row = await cursor.fetchone()
            return Quote(*row)


class Quotes(Unit):
    async def start(self) -> None:
        self.stack = AsyncExitStack()
        conn = await self.stack.enter_async_context(
            aiosqlite.connect(
                self.bot.config.quotes.db_path,
                isolation_level=None,  # autocommit
            )
        )
        LOG.debug(f"Quotes conn: {conn}")
        self.db: QuoteDB = await self.stack.enter_async_context(QuoteDB(conn))

    async def stop(self) -> None:
        await self.stack.aclose()

    @command(
        args=r"(?:#?(?P<qid>\d+)|@?(?P<username>\S+))?",
        usage="[<id> | <username>]",
        description="""show recent quotes

        id: integer - show a specific quote by ID
        username: string - only show quotes for the given username
        """,
    )
    async def quote(
        self, message: Message, *, qid: str = "", username: str = "", limit: str = ""
    ) -> str:
        if isinstance(message.channel, DMChannel):
            return "quotes not supported over DM"

        server = message.guild.id

        try:
            if qid:
                quote_id = int(qid)
                quote = await self.db.get(server, quote_id)

            else:
                quote = (
                    await self.db.find(
                        server, message.channel.name, username, fuzz=True, limit=1
                    )
                )[0]

            return f"#{quote.id} [{quote.added_at}] <{quote.username}> {quote.text}"

        except Exception:
            return "error: no quotes found"

    @command(
        args=r"@?(?P<username>\S+)",
        usage="<username>",
        description="grab the user's last message",
    )
    async def grab(self, message: Message, username: str) -> str:
        if isinstance(message.channel, DMChannel):
            return "quotes not supported over DM"

        quoted = await message.channel.history().get(author__name=username)
        if not quoted:
            quoted = await message.channel.history().get(author__display_name=username)
        if not quoted:
            return f"error: no message found for user {username!r}"

        return await self.grab_quote(quoted, message.author)

    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        channel = self.client.get_channel(payload.channel_id)
        if isinstance(channel, DMChannel):
            return

        if payload.emoji.name not in self.bot.config.quotes.grab_reactions:
            return

        message = await channel.history().get(id=payload.message_id)
        user = payload.member

        response = await self.grab_quote(message, user)
        if response:
            await channel.send(response)

    async def grab_quote(self, quoted: Message, quoter: User) -> str:
        if quoted.author.id == quoter.id:
            return "Adjust aim, Shepard-Commander."

        if quoted.author.id == self.client.user.id:
            return "We doubt your ability to accurately target."

        server = quoted.guild.id
        channel = quoted.channel.name
        username = quoted.author.display_name
        added_by = quoter.display_name
        text = quoted.clean_content

        q = Quote.new(server, channel, username, added_by, text)
        await self.db.add(q)

        if self.bot.config.quotes.tweet_grabs:
            status = self.bot.config.quotes.tweet_format.format(
                channel=channel, username=username, added_by=added_by, text=text
            )
            unit = self.bot.units.get("Twitter", None)
            LOG.debug(f"twitter unit: {unit}")
            if unit:
                LOG.debug(f"pushing quote to twitter: {status!r}")
                await unit.update(status)

        return f"quote #{q.id} saved"
