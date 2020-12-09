# Copyright 2020 John Reese
# Licensed under the MIT License

from pathlib import Path
from typing import Any, Mapping, Optional, List, Dict

import tomlkit
from attr import dataclass, field, fields


@dataclass
class BotConfig:
    admins: List[int] = field(factory=list)
    debug: bool = False
    log: Optional[Path] = field(default=Path("output.log"), converter=Path)
    log_megabytes: int = 64
    log_count: int = 2
    uvloop: bool = False


@dataclass
class ChatlogConfig:
    root: str = "logs"
    path: str = "{server}/{channel}/{date}.log"
    format: str = "[{time}] <{user}> {message}\n"


@dataclass
class DiscordConfig:
    token: str


@dataclass
class TwitterConfig:
    consumer_key: str = ""
    consumer_secret: str = ""
    access_key: str = ""
    access_secret: str = ""
    timeline_channels: Dict[str, List[str]] = field(factory=dict)


@dataclass
class QuotesConfig:
    db_path: Optional[Path] = field(default=Path("quotes.db"), converter=Path)
    grab_reactions: List[str] = ["💭"]
    tweet_grabs: bool = True
    tweet_format: str = "{text}"


@dataclass
class Config:
    bot: BotConfig
    chatlog: ChatlogConfig
    discord: DiscordConfig
    twitter: TwitterConfig
    quotes: QuotesConfig


def load_config(path: Path) -> Config:
    if path.is_file():
        document = tomlkit.loads(path.read_text())
    else:
        document = {}

    data: Dict[str, Any] = {}

    for cf in fields(Config):
        if cf.name in document:
            data[cf.name] = cf.type(**document[cf.name])  # type: ignore

        else:
            data[cf.name] = cf.type()  # type: ignore

    return Config(**data)
