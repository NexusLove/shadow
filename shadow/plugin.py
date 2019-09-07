"""Plugin implementation source file.

This module implements the Plugin base class,
PluginFlag enum and the PluginListnerType enum.

The Plugin base class is the main export of the module
as it is used by user code to satisfy an interface constraint
the shadow client places on extensions.
"""
import asyncio
import inspect
import re
from typing import Set, List, Callable, Any, Iterable, Union, Iterator, Optional, Tuple
from enum import IntEnum


_RE_INFERED_EVENT_NAME = re.compile(r"on_([A-Za-z_]+)")
_RE_INFERED_SUB = re.compile(r"(_|^)([A-Za-z])")
_RE_CAMEL_CASE = re.compile(r'([a-z])?([A-Z])')

__all__ = ("Plugin", "PluginFlag", "PluginListnerType")


class PluginFlag(IntEnum):
    """An enum of feature flags for a plugin."""

    Exposed = 0


class PluginListnerType(IntEnum):
    """An enum of all discord.py supported events.

    refrence: https://discordpy.readthedocs.io/en/latest/api.html#event-reference
    """

    Connect = 1
    Disconnect = 2
    Ready = 3
    ShardReady = 4
    Resumed = 5
    Error = 6
    SocketRawReceive = 7
    SocketRawSend = 8
    Typing = 9
    Message = 10
    MessageDelete = 11
    BulkMessageDelete = 12
    RawMessageDelete = 13
    RawBulkMessageDelete = 14
    MessageEdit = 15
    RawMessageEdit = 16
    ReactionAdd = 17
    RawReactionAdd = 18
    ReactionRemove = 19
    RawReactionRemove = 20
    ReactionClear = 21
    RawReactionClear = 22
    PrivateChannelDelete = 23
    PrivateChannelCreate = 24
    PrivateChannelUpdate = 25
    PrivateChannelPinsUpdate = 26
    GuildChannelCreate = 27
    GuildChannelDelete = 28
    GuildChannelUpdate = 29
    GuildIntegrationsUpdate = 30
    WebhooksUpdate = 31
    MemberJoin = 32
    MemberRemove = 33
    MemberUpdate = 34
    UserUpdate = 35
    GuildJoin = 36
    GuildRemove = 37
    GuildUpdate = 38
    GuildRoleCreate = 39
    GuildRoleDelete = 40
    GuildRoleUpdate = 41
    GuildEmojisUpdate = 42
    GuildAvailable = 43
    GuildUnavailable = 44
    VoiceStateUpdate = 45
    MemberBan = 46
    MemberUnban = 47
    GroupJoin = 48
    GroupRemove = 49
    RelationshipAdd = 50
    RelationshipRemove = 51
    RelationshipUpdate = 52


class Plugin:
    """The plugin base class.

    Plugins are classes which inherit from this base class.

    >>> @Plugin.exposed  # Allow our client to automatically load the plugin.
    ... class Cool(Plugin):
    ...     \"\"\"A cool plugin.\"\"\"
    ...
    ...    @Plugin.event_listener
    ...    async def on_message(self, message):
    ...        if message.author != self.client.user:
    ...            return
    ...
    ...        elif message.content == 'cool':
    ...            await message.edit(content='cool, cool cool cool.')
    ...
    >>> # Now we have a cool exposed plugin!

    Attributes
    ----------
    client : :class:`discord.Client`
        The discord client this plugin is associated with.
    """

    __flags: Set[PluginFlag] = set()

    def __init__(self, client):
        self.client = client

    def __repr__(self) -> str:
        flags = ', '.join(f'{flag.name.lower()}=True' for flag in self.__flags)
        return f'<shadow.Plugin: name={self.__class__.__name__!r} flags=<{flags}>>'

    # Internals

    @staticmethod
    def __name_from_plugin_flag(flag: PluginFlag) -> str:
        def to_snake_case(match: re.Match) -> str:
            left, right = match.groups()
            return f'{left}_{right}'

        return _RE_CAMEL_CASE.sub(to_snake_case, flag.name)

    @staticmethod
    def __plugin_flag_from_name(name: str) -> PluginFlag:
        try:
            return getattr(PluginFlag, name.title())
        except AttributeError as err:
            raise ValueError from err

    @staticmethod
    def __iter_cast_flags(flags: Iterable[Union[PluginFlag, str]]) -> Iterator:
        for flag in flags:
            if isinstance(flag, str):
                flag = __class__.__plugin_flag_from_name(flag)

            elif not isinstance(flag, PluginFlag):
                raise TypeError(
                    'Expected flag argument to be a string or member of `PluginFlag` enum.'
                )

            yield flag

    # Plugin class decorators

    @staticmethod
    def with_flags(**flags):
        r"""Configure the plugins default flags.

        Parameters
        ----------
        \*\*flags: Dict[:class:`str`, :class:`bool`]
            The flags to configure.

        Raises
        ------
        KeyError
            If any invalid flags are provided this will be raised.
        """
        valid_flags = {
            attr_name.lower(): getattr(PluginFlag, attr_name)
            for attr_name in dir(PluginFlag)
            if attr_name[0] != "_"
        }

        for name in filter((lambda name: name not in valid_flags), flags.keys()):
            raise KeyError(f'Invalid flag name: {name}')

        def decorator(klass):
            assert isinstance(klass, type) and issubclass(klass, Plugin)

            plugin_unload_handler = next(
                (
                    value
                    for _, value in inspect.getmembers(klass)
                    if hasattr(value, '_Plugin__unload_handler')
                ),
                None,
            )

            if plugin_unload_handler is not None:
                setattr(klass, '__Plugin_unload__', plugin_unload_handler)

            for name, enabled in flags.items():
                if enabled:
                    flag = getattr(PluginFlag, name.title())
                    klass._Plugin__flags.add(flag)

            return klass

        return decorator

    # Plugin method decorators

    @staticmethod
    def unload_handler(method: Callable[..., Any]) -> Callable[..., Any]:
        """A method decorator that marks the plugins unload callback.

        >>> # Example usage
        >>> @Plugin.with_flags(reloadable=True)
        ... class Foo(Plugin):
        ...     @Plugin.unload_handler
        ...     def __unload(self):
        ...         print(f'Unloading {self!r}')

        Parameters
        ----------
        method : Callable[:class:`...`, Any]
            The method to mark.
        """
        setattr(method, '_Plugin__unload_handler', None)
        return method

    @staticmethod
    def event_listener(
        _method: Optional[Callable[..., Any]] = None, *, event: Optional[str] = None
    ) -> Callable[..., Any]:
        """A method decorator to mark event listeners.

        This decorator can be applied over a method directly
        or called with an `event` kwarg taking a string argument
        as the name of the event to listen for.

        if applied directly note that the target event will be
        inferred from the method name from the "on_{event}" format
        using the regex `r"on_([A-Za-z_]+)"`.

        If a name cannot be inferred an `AssertionError` will be raised.

        >>> # Example usage
        >>> Class Foo(Plugin):
        ...    \"\"\"Baz Bar\"\"\"
        ...
        ...    @Plugin.event_listener(event="on_ready")  # Explicitly declare target event.
        ...    async def _ready_handle(self):
        ...        self.client.log.info("Client is ready!")
        ...
        ...    @Plugin.event_listener
        ...    async def on_message(self, message):  # Target event is inferred from the method name "on_message".
        ...        self.client.log.debug("Saw message: %s", message)

        Parameters
        ----------
        _method : Optional[:class:`Callable[..., ...]`]
            The method to be marked as an event listener,
            this allows the method to handle fired events.
        event : Optional[:class:`str`]
            The event to listen for.
            Must be a string in the "on_{event}" format such as:
            "on_message", "on_ready", or "on_reaction_add".

        Raises
        ------
        AssertionError
            This will be raised when failing to infer
            the event target from the method name.
        ValueError
            This will be raised when no method was passed
            nor event name was explicitly specified.
        """

        def infered_substitution_callback(match: re.Match) -> str:
            return match.group(2).upper()

        if _method is not None:
            match = _RE_INFERED_EVENT_NAME.match(_method.__name__)

            if match is None:
                raise AssertionError(
                    f'Failed to infer event target from method name ({_method.__name__!r}) '
                    'please make sure it follows the "on_{event}" format'
                )

            method_name = match.group(1)

            listener_type_name = _RE_INFERED_SUB.sub(
                infered_substitution_callback, method_name
            )
            listener_type = getattr(PluginListnerType, listener_type_name)

            setattr(_method, '_Plugin__event_listener', listener_type)

            return _method

        if event is None:
            raise ValueError('An `event` argument is required.')

        def decorator(method: Callable[..., Any]) -> Callable[..., Any]:
            assert event is not None

            listener_type_name = _RE_INFERED_SUB.sub(infered_substitution_callback, event)
            listener_type = getattr(PluginListnerType, listener_type_name)

            setattr(method, '_Plugin__event_listener', listener_type)

            return method

        return decorator

    # Plugin flag methods

    def set_flags(self, *flags: List[Union[PluginFlag, str]]) -> None:
        r"""Enable the specified flags.

        It is a no-op if you set an already enabled flag.

        Parameters
        ----------
        \*flags : List[Union[:class:`PluginFlag`, :class:`str`]]
            The plugin flags to enable.

        Raises
        ------
        ValueError
            This is raised if a string flag is passed
            but there is not valid PluginFlag member named so.
        TypeError
            If a flag argument is anything other
            than a string or PluginFlag member.
        """
        for flag in self.__iter_cast_flags(flags):
            self.__flags.add(flag)

    def clear_flags(self, *flags: List[Union[PluginFlag, str]]) -> None:
        r"""Clear the specified flags.

        it is a no-op if you clear an already cleared flag.

        Parameters
        ----------
        \*flags : List[Union[:class:`PluginFlag`, :class:`str`]]
            The plugin flags to clear.

        Raises
        ------
        ValueError
            This is raised if a string flag is passed
            but there is not valid PluginFlag member named so.
        TypeError
            If a flag argument is anything other
            than a string or PluginFlag member.
        """
        for flag in self.__iter_cast_flags(flags):
            if flag in self.__flags:
                self.__flags.remove(flag)

    def check_flag(
        self, flag: Union[PluginFlag, str], present: Optional[bool] = True
    ) -> bool:
        """Check if a specified flag is enabled or disabled.

        Parameters
        ----------
        flag : Union[:class:`PluginFlag`, :class:`str`]
            The flag to check. Can be either a PluginFlag
            member or a regular name e.g. PluginFlag.Exposed
            is equivalent to the string "exposed"
        present : Optional[:class:`bool`]
            The presence state of the flag to check against.
            by default it's set to True in order to
            check if a flag is enabled, but can be set
            to False to expicitly check for absence.

        Raises
        ------
        ValueError
            This is raised if a string flag is passed
            but there is not valid PluginFlag member named so.
        TypeError
            If the flag argument is anything other
            than a string or PluginFlag member.

        Returns
        -------
        result: :class:`bool`
            Wether or not the flag match the present state.
        """
        if isinstance(flag, str):
            flag = self.__plugin_flag_from_name(flag)

        elif not isinstance(flag, PluginFlag):
            raise TypeError(
                'Expected `flag` argument to be a string or member of `PluginFlag` enum.'
            )

        is_present = flag in self.__flags

        return present == is_present

    # Generic

    def dispatch(self, event, *args, **kwargs):
        r"""Dispatch an event to the plugins event handlers.

        Parameters
        ----------
        event : :class:`str`
            The name of the event to dispatch.
        \*args : List[Any]
            The args to pass to the event handler.
        \*\*kwargs : Dict[Any, Any]
            The kwargs to pass to the event handler.
        """

        def infered_substitution_callback(match: re.Match) -> str:
            return match.group(2).upper()

        plugin_listner_name = _RE_INFERED_SUB.sub(infered_substitution_callback, event)

        try:
            plugin_listner_type = getattr(PluginListnerType, plugin_listner_name)
        except AttributeError:
            return

        handlers = (
            value
            for value in (getattr(self, name) for name in dir(self))
            if inspect.ismethod(value)
            and (getattr(value, '_Plugin__event_listener', None) == plugin_listner_type)
        )

        for handler in handlers:
            self.client.schedule_event(handler, f'on_{event}', *args, **kwargs)
