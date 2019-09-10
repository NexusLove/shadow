import asyncio
from typing import Dict, Union, Callable, Optional, Tuple, List, Type

from discord import Message, User, ClientUser, TextChannel
from shadow import Plugin

from .thread import ReThread
from .protocol import URIProtocol

__all__ = ('URI',)


@Plugin.with_flags(exposed=True)
class URI(Plugin):
    """A plugin to expand custom URI's."""

    DEFAULT_PROTOCOLS: List[URIProtocol] = []

    __protocols: Dict[str, URIProtocol] = {}
    __table: Dict[str, Message] = {
        'HEAD': {},
        'head': {},
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.client.log.info('Registering default URIs: %s', repr(self.DEFAULT_PROTOCOLS))
        for uri_class in self.DEFAULT_PROTOCOLS:
            self.register_uri(uri_class)

    # Properties

    @property
    def table(self):
        """Dict[:class:`str`, Union[Dict[:class:`int`, :class:`discord.Message`], :class:`discord.Message`] - A namespace directory for aliasing."""
        return self.__table

    # Public methods

    def register_uri(self, uri: Type[URIProtocol]):
        """Register a URI protocol to scan for.

        Parameters
        ----------
            uri : Type[:class:`URIProtocol`]
            The URI protocol to register.
        """
        if not hasattr(uri, 'base'):
            raise AttributeError

        self.__protocols[uri.base] = uri

    def get_uri(self, protocol: str) -> URIProtocol:
        """Get a URI protocol class from a protocol string.

        Parameters
        ----------
        protocol : :class:`str`
            The protocol to lookup.

        Returns
        -------
        uri_protocol : :class:`URIProtocol`
            The URI protocol class instance.

        Raises
        ------
        KeyError
            This is raised if the protocol is not registered.
        """
        return self.__protocols[protocol]

    # Event handlers

    @Plugin.event_listener(event='message')
    async def __update_tracers(self, message):
        channel_id = message.channel.id
        authored = message.author == self.client.user
        objective_table, subjective_table = self.__table['HEAD'], self.__table['head']

        if channel_id in objective_table:
            self.__table['HEAD'][channel_id] = message

        if authored and channel_id in subjective_table:
            self.__table['head'][channel_id] = message

    @Plugin.event_listener(event='message')
    async def __parse_uri(self, message):
        if message.author != self.client.user:
            return

        thread = ReThread(message, self)
        thread.start()

        while not thread.complete:
            await asyncio.sleep(0.1)

        content, matches = thread.result()

        if not matches:
            return

        self.logger.info('%s URI matches occurred, editing the original message...', matches)
        await message.edit(content=''.join(content))
