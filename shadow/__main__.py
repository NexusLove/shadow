import sys
import os
from typing import Iterable

import click

from . import Client, utils

LOGGER = utils.get_colored_logger(__name__)


@click.command()
@click.argument("token")
@click.option("--use", multiple=True)
@click.option("--discard", multiple=True)
def main(token: str, use: Iterable[str], discard: Iterable[str]):
    """A selfbot designed to enrich the discord experience."""
    plugins = set(('builtins', *set(use).difference(set(discard))))

    if 'builtins' in discard:
        plugins.remove('builtins')

    client = Client()

    for plugin in plugins:
        client.load_plugin_module(f'shadow.ext.{plugin}')

    if client.plugins:
        client.log.info(
            'Loaded %d plugins: %s', len(client.plugins), repr(client.plugins)
        )

    client.run(token, bot=False)


if __name__ == "__main__":
    if not os.geteuid():
        sys.exit("Refusing to run as root.")

    utils.get_colored_logger("discord", "WARN")

    main()  # pylint: disable=no-value-for-parameter
