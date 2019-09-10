from re import compile as _re_compile
from typing import Optional, Union, Callable

from .core import URIProtocol

_RE_QUOTE_PATH = _re_compile(r'([A-Za-z_]+|[0-9]{18,20})')


class Quote(URIProtocol):
    base: str = 'quote'

    async def resolve(self) -> Optional[str]:
        match = _RE_QUOTE_PATH.fullmatch(self.path)

        if match is None:
            return

        channel = self.message.channel
        ident, = match.groups()

        if ident.isdigit():
            ident = int(ident)

        try:
            target = await self.resolve_identifier(ident, channel)
        except KeyError:
            target = None

        if target is None:
            return

        content = target.content

        return '\n'.join(f'> {line}' for line in content.splitlines())
