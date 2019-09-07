"""Implement functionality to perform interpolated code evauluation."""
import re
from typing import Optional

from jishaku.repl.compilation import AsyncCodeExecutor, Scope

from shadow import Plugin

__all__ = ('Eval',)

_RE_INTERPOLATED = re.compile(r'\$\{(.*)\}')


@Plugin.with_flags(exposed=True)
class Eval(Plugin):
    """Evaluate user input."""

    scope: Optional[Scope] = None

    async def __eval(self, source: str) -> str:
        scope = self.scope

        if scope is None:
            self.scope = scope = Scope()

        scope.update_globals({'_client': self.client})

        result = repr(None)

        async for result in AsyncCodeExecutor(source, scope):
            if not isinstance(result, str):
                # repr all non-strings
                result = repr(result)

        return result

    @Plugin.event_listener(event='message')
    async def __parse_eval(self, message):
        if message.author != self.client.user:
            return

        if _RE_INTERPOLATED.search(message.content) is not None:
            results = []

            for match in _RE_INTERPOLATED.finditer(message.content):
                try:
                    result = value = (await self.__eval(match.group(1).strip())).strip()
                except Exception as err:  # pylint: disable=broad-except
                    results.append(str(err))
                    continue

                if not result:
                    value = '\u200b'

                elif len(result) > 2000:
                    value = '<RESULT TOO LARGE>'

                results.append(value)

            stream = iter(results)

            def advance(_: re.Match) -> str:
                return next(stream)

            evaulated_content = _RE_INTERPOLATED.sub(advance, message.content)

            await message.edit(content=evaulated_content)
