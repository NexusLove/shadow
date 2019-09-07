"""Implement URI resolvers for discord messages.
"""
import asyncio
import re
import traceback
import threading
from typing import Dict, Union, Callable, Optional, Tuple

import discord

from shadow import Plugin

__all__ = ('URI',)

_RE_URI = re.compile(
    r'([A-Za-z]+)://([=\-+*&^%$£"!`A-Za-z0-9-~\[\(\)\]\{\};@\'#?.><|]+)'
)
_RE_REF_PATH = re.compile(r'([A-Za-z_]+|[0-9]{18,20})(([~\-+=])([0-9]+|[A-Za-z_]+))?')
_RE_QUOTE_PATH = re.compile(r'([A-Za-z_]+|[0-9]{18,20})')
_RE_TRACE_PATH = re.compile(r'(set|clear|enable|disable)')


class ReThread(threading.Thread):
    """A thread that resolves and substitutes message contents.

    Attributes
    ----------
    lock : :class:`threading.Lock`
        A lock specific to this threads data.
    """
    def __init__(self, message, plugin):
        super().__init__()
        self.lock = threading.Lock()
        self.__message = message
        self.__plugin = plugin
        self.__matches = 0
        self.__complete = False
        self.__result = None

    def _match_once(self, match):
        start, stop = match.span()
        protocol, path = match.groups()

        try:
            callback = getattr(self.__plugin, f'_{protocol}')
        except AttributeError:
            return match.group(0)

        _uri = f'URI<protocol={protocol!r}, path={path!r}, span=<start={start!r}, stop={stop!r}>>'
        self.__plugin.logger.info('Parsing %s', _uri)

        future = asyncio.run_coroutine_threadsafe(callback(self.__message, path), self.__plugin.client.loop)

        try:
            sub = future.result()
        except Exception:  # pylint: disable=broad-except
            traceback.print_exc()

        if sub is None:
            self.__plugin.logger.error('Failed to parse %s', _uri)
            sub = match.group(0)
        else:
            self.__matches += 1

        return sub

    @property
    def complete(self) -> bool:
        """:class:`bool` - True if parsing completed."""
        with thread.lock:
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
        self.__result = (content, self.__matches)
        with thread.lock:
            self.__complete = True


@Plugin.with_flags(exposed=True)
class URI(Plugin):
    """A plugin to expand custom uri's."""

    __table: Dict[str, discord.Message] = {
        'HEAD': {},
        'head': {},
    }

    # Internal helpers

    async def __fetch_message(
        self,
        channel: discord.TextChannel,
        predicate: Union[
            Callable[[discord.Message], bool], int, discord.User, discord.ClientUser
        ],
        step: int = 100,
    ) -> discord.Message:
        before = None

        if isinstance(predicate, int):
            snowflake = predicate
            predicate = lambda message: message.id == snowflake

        elif isinstance(predicate, (discord.User, discord.ClientUser)):
            author = predicate
            predicate = lambda message: message.author == author

        while True:
            async for message_ in channel.history(limit=step, before=before):
                if predicate(message_):
                    return message_

                before = message_

    async def __fetch_message_by_offset(
        self, pivot: discord.Message, offset: int
    ) -> Optional[discord.Message]:
        count = 1

        kwargs = {
            'oldest_first': offset > 0
        }

        if offset < 0:
            kwargs['before'] = pivot
        else:
            kwargs['after'] = pivot

        offset = abs(offset)

        async for message in pivot.channel.history(limit=(offset + 1), **kwargs):
            if count == offset:
                return message

            count += 1

    async def __resolve_identifier(self, ident: str, channel: discord.TextChannel) -> Optional[discord.Message]:
        fetch_message = self.__fetch_message

        if ident.isdigit():
            target = await fetch_message(channel, int(ident))
        else:
            target = self.__table.get(ident, None)

            if isinstance(target, dict):
                if channel.id not in target:
                    target[channel.id] = target = await fetch_message(channel, (lambda _: True))
                else:
                    target = target[channel.id]

        return target

    # Protocol handlers

    async def _trace(self, message, path) -> str:
        match = _RE_TRACE_PATH.fullmatch(path)

        if match is None:
            return

        flag = match[1]

        destructive = flag not in ('set', 'enable')

        for key in ('HEAD', 'head'):
            if destructive:
                self.__table[key].pop(message.channel.id)
            else:
                self.__table[key][message.channel.id] = message

        return 'Tracing' if not destructive else 'Ignoring'

    async def _quote(self, message, path: str) -> str:
        match = _RE_QUOTE_PATH.fullmatch(path)

        if match is None:
            return

        channel = message.channel
        ident, = match.groups()

        target = self.__resolve_identifier(ident, channel)

        if target is None:
            return

        content = target.content

        return '\n'.join(f'> {line}' for line in content.splitlines())

    async def _ref(self, message, path: str) -> str:
        match = _RE_REF_PATH.fullmatch(path)

        if match is None:
            return

        base, _, operator, tail = match.groups()

        target = self.__resolve_identifier(base, message.channel)

        if target is None:
            return

        if operator == '=':
            self.__table[key] = tail
            return path

        # operator is either `None` or in '+-~'
        # If it is None, do nothing to the target
        # Otherwise perform the operator on the target
        if operator is not None:
            offset = int(tail)

            if operator in '-~':
                offset = -offset

            target = await self.__fetch_message_by_offset(base, offset)

        return f'<{target.jump_url}>'

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

        while True:
            await asyncio.sleep(0.1)

            if thread.complete:
                break

        content, matches = thread.result()

        if not matches:
            return

        self.logger.info('%s URI matches occurred, editing the original message...', matches)
        await message.edit(content=''.join(content))
