"""Source implementation for the application client."""
import asyncio
import sys
import importlib
import inspect
import logging
from typing import Set, Dict, List, Any, Type, Union, Optional, Callable, Tuple
from types import ModuleType, MappingProxyType

import discord

from .plugin import Plugin, PluginFlag
from .utils import get_colored_logger

LOGGER = get_colored_logger(__name__)


def _exposed(pair: Tuple[str, Any]) -> bool:
    _, value, = pair
    return (
        isinstance(value, type)
        and issubclass(value, Plugin)
        and Plugin.check_flag(value, PluginFlag.Exposed)
    )


class Client(discord.Client):
    """An augmented :class:`discord.Client` subclass.

    Attributes
    ----------
    log : :class:`logging.Logger`
        The logger instance attached to the client.
    logger : :class:`logging.Logger`
        Same as :attr:`log`
    """

    @property
    def plugins(self):
        """Mapping[Type[:class:`Plugin`], :class:`Plugin`]: A read-only mapping of plugin class to plugin instance."""
        return MappingProxyType(self.__plugins)

    __plugins: Dict[Type[Plugin], Plugin] = {}

    log = logger = LOGGER

    schedule_event = discord.Client._schedule_event

    def dispatch(self, event, *args, **kwargs):
        for plugin in self.plugins.values():
            plugin.dispatch(event, *args, **kwargs)

        super().dispatch(event, *args, **kwargs)

    def load_plugin_module(
        self,
        target: Union[ModuleType, str],
        predicate: Optional[Callable[[str, Any], bool]] = None,
        logger_cb: Optional[Callable[[Type[Plugin]], None]] = None,
    ) -> None:
        """Loads or reinitalizes a plugin module.

        >>>  # Import and initialize.
        >>> client.load_plugin_module('shadow.ext.builtins')

        >>>  # Only initialize.
        >>> import shadow.ext.builtins
        >>> client.load_plugin_module(shadow.ext.builtins)

        >>> # Import, filter and log
        >>> import logging
        >>> from typing import Type
        >>> from shadow import Plugin
        >>> def logging_cb(logger: logging.Logger, value: Type[Plugin]):
        ...     logger.info('Loading plugin: %s', value)
        >>>
        >>> def startswith_a(plugin: Type[Plugin]) -> bool:
        ...     return plugin.__name__.startswith('a')
        >>>
        >>> # Import the package `shadow.ext.foo` inspect it for
        >>> # exposed plugins and load only those whose name starts with 'a'
        >>> client.load_plugin_module('shadow.ext.foo', predicate=startswith_a, logging_cb=logging_cb)

        .. warning::

            It is **not recommended** to call this method with
            an already loaded Plugin module. Doing so will not
            call the plugin desctructors and will lead to unkown behavior.

        Parameters
        ----------
        target : Union[ModuleType, str]
            The name of the plugin module to load.
            or the plugin instance to reinitalize.
        predicate : Optional[Callable[[str, Any], bool]]
            The predicate to respect for initalization.
            It must be a callable that takes in a Plugin class instance
            and returns True if it should be loaded or False otherwise.
            The predicate may be None to load all plugins.
        logger_cb : Optional[Callable[[Type[Plugin]], None]]
            The callback that should be used for handling logging.
            it must be a callable that takes in a logging.Logger instance
            and a Plugin class instance.

        Raises
        ------
        TypeError
            This will be raised when the target is not a module nor a string instance.
        """
        if isinstance(target, str):
            name = target
            spec = importlib.util.find_spec(name)
            lib = importlib.util.module_from_spec(spec)

            sys.modules[name] = lib

            try:
                spec.loader.exec_module(lib)
            except Exception:
                del sys.modules[name]
                raise

        elif not isinstance(target, ModuleType):
            raise TypeError(
                f'Expected a string, or module instance. Instead got: {type(target)}.'
            )

        else:
            lib = target

        if predicate is not None and not callable(predicate):
            raise TypeError(f'The predicate is neither callable nor None.')

        if logger_cb is None:
            def logger_cb(logger: logging.Logger, plugin: Type[Plugin]) -> None:
                logger.info('Attempting to load plugin: %s', plugin)

        if not callable(logger_cb):
            raise TypeError(
                f'The logger must be callable and accept two arguments: the logger instance and the plugin class instance.'
            )

        for _, plugin in filter(_exposed, inspect.getmembers(lib)):
            if predicate is None or predicate(plugin):
                logger_cb(self.logger, plugin)
                self.load_plugin(plugin)

    def unload_plugin_module(self, name: str) -> int:
        """Unload a plugin module.

        Parameters
        ----------
        name : :class:`str`
            The name of the plugin module to unload.

        Returns
        -------
        refcount : :class:`int`
            The amount of refrences held to the module after unloading.
            It is essentially `sys.getrefcount(module) - 2` and should
            be zero if all refrences to the module have been dropped.
        """

    def load_plugin(self, klass: Type[Plugin]) -> None:
        """Load an individual plugin type.

        Parameters
        ----------
        klass : :class:`Plugin`
            The plugin to load.
        """
        self.__plugins[klass] = klass(self)

    def unload_plugin(self, plugin: Plugin) -> None:
        """Unload a plugin instance.

        Parameters
        ----------
        plugin : :class:`Plugin`
            The plugin instance to unload.
        """
        self.__plugins.pop(type(plugin))

    async def on_connect(self) -> None:
        self.log.info('Client has connected...')

    async def on_ready(self) -> None:
        self.log.info('Client is ready!')