"""Implement URI resolvers for discord messages.
"""
import asyncio
import re
import traceback
import threading
from typing import Optional, Tuple

from discord import Message

from shadow import Plugin

__all__ = ('ReThread',)

_RE_URI = re.compile(
    r'([A-Za-z]+)://([=\-+*&^%$£"!`A-Za-z0-9-~\[\(\)\]\{\};@\'#?.><|]+)'
)


class ReThread(threading.Thread):
    """A thread that resolves and substitutes message contents.

    Attributes
    ----------
    lock : :class:`threading.Lock`
        A lock specific to this threads data.
    """
    __matches = 0
    __complete = False
    __result = None

    def __init__(self, message: Message, plugin: Plugin) -> None:
        super().__init__()
        self.lock = threading.Lock()
        self.__message = message
        self.__plugin = plugin

    def _match_once(self, match: re.Match):
        start, stop = match.span()
        protocol, path = match.groups()

        try:
            klass = self.__plugin.get_uri(protocol)
        except KeyError:
            return match.group(0)
        else:
            uri = klass(plugin=self.__plugin, match=match, message=self.__message)

        self.__plugin.logger.info('Parsing %s', repr(uri))

        future = asyncio.run_coroutine_threadsafe(uri.resolve(), self.__plugin.client.loop)

        try:
            sub = future.result()
        except Exception:  # pylint: disable=broad-except
            traceback.print_exc()

        if sub is None:
            self.__plugin.logger.error('Failed to parse %s', repr(uri))
            sub = match.group(0)
        else:
            self.__matches += 1

        return sub

    @property
    def complete(self) -> bool:
        """:class:`bool` - True if parsing completed."""
        with self.lock:
            return self.__complete

    def result(self) -> Tuple[str, int]:
        """Get the result of this threads processing.

        Returns
        -------
        result : :class:`Tuple[str, int]`
            A tuple of the parsed contents and the amount of matches."

        Raises
        ------
        RuntimeError
            If the parsing is not complete this will be raised.
        """
        if self.complete:
            return self.__result
        raise RuntimeError

    def run(self):
        content = _RE_URI.sub(self._match_once, self.__message.content)

        if content == self.__message.content:
            self.__matches = 0

        self.__result = (content, self.__matches)

        with self.lock:
            self.__complete = True
