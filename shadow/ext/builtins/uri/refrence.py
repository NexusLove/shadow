from re import compile as _re_compile
from typing import Optional

from discord import Message

from .core import URIProtocol

_RE_REF_PATH = _re_compile(r'([A-Za-z_]+|[0-9]{18,20})(([~\-+=])([0-9]+|[A-Za-z_]+))?')


class Refrence(URIProtocol):
    base: str = 'ref'

    async def resolve(self) -> Optional[str]:
        match = _RE_REF_PATH.fullmatch(self.path)

        if match is None:
            return

        base, _, operator, tail = match.groups()

        if base.isdigit():
            base = int(base)

        try:
            base = await self.resolve_identifier(base, self.message.channel)
        except KeyError:
            base = None

        if base is None:
            return

        if operator == '=':
            self.plugin.table[tail] = base
            return path

        # operator is either `None` or in '+-~'
        # If it is None, do nothing to the target
        # Otherwise perform the operator on the target
        if operator is not None:
            offset = int(tail)

            if operator in '-~':
                offset = -offset

            target = await self.fetch_message_by_offset(base, offset)

        return f'<{target.jump_url}>'

    async def fetch_message_by_offset(
        self, pivot: Message, offset: int
    ) -> Optional[Message]:
        """Fetch a :class:`discord.Message` by an offset of a pivot.

        Parameters
        ----------
        pivot : :class:`discord.Message`
            The message to pivot from.
        offset : :class:`int`
            The offset to translate by from the message.

        Returns
        -------
        message : Optional[:class:`discord.Message`]
            The resolved message, otherwise `None`
        """
        index = 0
        absolute_offset = abs(offset)

        kwargs = {
            'oldest_first': offset > 0,
            'limit': absolute_offset + 1,
        }

        if offset < 0:
            kwargs['before'] = pivot
        else:
            kwargs['after'] = pivot

        async for message in pivot.channel.history(**kwargs):
            if index == absolute_offset:
                return message
            else:
                index += 1
