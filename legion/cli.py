# Copyright 2020 John Reese
# Licensed under the MIT License

import logging

import click

from legion import __version__

LOG = logging.getLogger(__name__)


@click.group()
@click.version_option(__version__, "-V", "--version", prog_name="legion")
@click.help_option("-h", "--help")
@click.option(
    "-v", "--verbose", "--debug", is_flag=True, help="Enable verbose/debug logging"
)
def main(debug: bool):
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)


@main.command()
def run():
    LOG.info("Shepard Commander...")
