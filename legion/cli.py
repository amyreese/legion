# Copyright 2020 John Reese
# Licensed under the MIT License

import logging
from pathlib import Path

import click
from discord import Client

from legion import __version__
from legion.bot import Bot
from legion.config import load_config, Config
from legion.log import init_logger

LOG = logging.getLogger(__name__)


@click.group()
@click.pass_context
@click.version_option(__version__, "-V", "--version", prog_name="legion")
@click.help_option("-h", "--help")
@click.option("--debug", is_flag=True, help="Enable verbose/debug logging")
@click.option(
    "--config",
    type=click.Path(dir_okay=False, resolve_path=True),
    default="config.toml",
    help="path to config.toml",
)
def main(ctx: click.Context, debug: bool, config: str):
    """Discord bot with user quotes, Seinfeld scripts, and more"""
    config_obj = load_config(Path(config))
    ctx.obj = config_obj

    init_logger(
        stdout=True,
        file_path=config_obj.bot.log,
        debug=debug or config_obj.bot.debug,
        log_megabytes=config_obj.bot.log_megabytes,
        log_count=config_obj.bot.log_count,
    )


@main.command()
@click.pass_context
def run(ctx: click.Context):
    """Start the bot"""
    config: Config = ctx.obj
    bot = Bot(config)
    bot.start()

    return
    client = Client()

    @client.event
    async def on_ready():
        print(f"ready as user {client.user}")

    client.run(config.discord.token)
