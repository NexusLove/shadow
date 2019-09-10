from re import compile as _re_compile
from typing import Optional

from discord import Message

from .core import URIProtocol

_RE_TRACE_PATH = _re_compile(r'(set|clear|enable|disable)')


class Trace(URIProtocol):
    base: str = 'trace'

    async def resolve(self) -> Optional[str]:
        match = _RE_TRACE_PATH.fullmatch(self.path)

        if match is None:
            return

        message = self.message
        flag = match[1]

        destructive = flag not in ('set', 'enable')

        for key in ('HEAD', 'head'):
            if destructive:
                self.plugin.table[key].pop(message.channel.id)
            else:
                self.plugin.table[key][message.channel.id] = message

        return 'Tracing' if not destructive else 'Ignoring'
