# Copyright 2020 John Reese
# Licensed under the MIT License

from pathlib import Path
from typing import Any, Mapping, Optional, List, Dict

import tomlkit
from attr import dataclass, field, fields


@dataclass
class BotConfig:
    debug: bool = False
    log: Optional[Path] = field(default=Path("output.log"), converter=Path)
    log_megabytes: int = 64
    log_count: int = 2
    uvloop: bool = False


@dataclass
class DiscordConfig:
    token: str


@dataclass
class TwitterConfig:
    consumer_key: str = ""
    consumer_secret: str = ""
    access_key: str = ""
    access_secret: str = ""
    timeline_channels: List[str] = field(factory=list)


@dataclass
class QuotesConfig:
    db_path: Optional[Path] = field(default=Path("quotes.db"), converter=Path)
    tweet_grabs: bool = True
    tweet_format: str = "{text}"


@dataclass
class Config:
    bot: BotConfig
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
            data[cf.name] = cf.type(**document[cf.name])

        else:
            data[cf.name] = cf.type()  # type: ignore

    return Config(**data)
