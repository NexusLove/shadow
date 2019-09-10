import abc
import re
from dataclasses import dataclass
from typing import Optional, Union, Callable

from discord import Message, TextChannel, User, ClientUser
from shadow import Plugin

__all__ = ('URIProtocol',)


@dataclass
class URIProtocol(metaclass=abc.ABCMeta):
    plugin: Plugin
    match: re.Match
    message: Message

    def __repr__(self) -> str:
        start, stop = self.span
        return f'<URI<protocol={self.base!r}, path={self.path!r}, span=<start={start!r}, stop={stop!r}>>>'

    # Properties

    @property
    def span(self):
        return self.match.span()

    @property
    def path(self):
        return self.match.group(2)

    @property
    def protocol(self):
        return self.base

    # Interface

    @abc.abstractmethod
    async def resolve(self) -> Optional[str]:
        pass

    # Helpers

    async def fetch_message(
        self,
        channel: TextChannel,
        predicate: Union[
            Callable[[Message], bool], int, User, ClientUser
        ],
        step: int = 100,
    ) -> Message:
        """Scroll a messageable's history indefinitely until the predicate returns true for a given message.

        Parameters
        ----------
        channel : :class:`TextChannel`
        predicate : Optional[Callable[[str, Any], bool]]
        step : :class:`int`

        Returns
        -------
        message : :class:`discord.Message`
        """
        before = None

        if isinstance(predicate, int):
            snowflake = predicate
            predicate = lambda message: message.id == snowflake

        elif isinstance(predicate, (User, ClientUser)):
            author = predicate
            predicate = lambda message: message.author == author

        while True:
            async for message_ in channel.history(limit=step, before=before):
                if predicate(message_):
                    return message_

                before = message_

    async def resolve_identifier(self, ident: Union[str, int], channel: TextChannel) -> Message:
        """Resolve an indentifier into a :class:`discord.Message`.

        Parameters
        ----------
        ident : Union[:class:`str`, :class:`int`]
            The identifier to resolve.
        channel : :class:`discord.TextChannel`
            The channel to resolve for.

        Returns
        -------
        message : :class:`discord.Message`
            The resolved message.

        Raises
        ------
        KeyError
            If the identifier could not be resolved.
        """
        if isinstance(ident, int):
            target = await self.fetch_message(channel, ident)
        else:
            target = self.plugin.table.get(ident, None)

            if isinstance(target, dict):
                if channel.id not in target:
                    target[channel.id] = target = await self.fetch_message(channel, (lambda _: True))
                else:
                    target = target[channel.id]

        if target is None:
            raise KeyError

        return target

