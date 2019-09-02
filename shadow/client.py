"""Source implementation for the application client."""
import asyncio
import sys
import importlib
import inspect
from typing import Set, Dict, List, Any

import discord

from .plugin import Plugin, PluginFlag
from .utils import get_colored_logger

LOGGER = get_colored_logger(__name__)


class Client(discord.Client):
    """A modified discord Client tailored for the applications usage."""

    @property
    def plugins(self):
        return self.__plugins

    __plugins: Set[Plugin] = set()
    log = logger = LOGGER

    schedule_event = discord.Client._schedule_event

    def dispatch(self, event, *args, **kwargs):
        super().dispatch(event, *args, **kwargs)

        for plugin in self.plugins:
            plugin.dispatch(event, *args, **kwargs)

    def load_plugin_module(self, name: str) -> None:
        """Loads a plugin module.

        Parameters
        ----------
        name : :class:`str`
            The name of the plugin module to load.
        """
        spec = importlib.util.find_spec(name)
        lib = importlib.util.module_from_spec(spec)

        sys.modules[name] = lib

        try:
            spec.loader.exec_module(lib)
        except Exception:
            del sys.modules[name]
            raise

        for _, value in inspect.getmembers(lib):
            if (
                isinstance(value, type)
                and issubclass(value, Plugin)
                and Plugin.check_flag(value, PluginFlag.Exposed)
            ):
                self.logger.info('Attempting to load exposed plugin: %s', value)
                self.load_plugin(value)

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

    def load_plugin(self, klass: Plugin) -> None:
        """Load an individual plugin.

        Parameters
        ----------
        klass : :class:`Plugin`
            The plugin to load.
        """
        self.__plugins.add(klass(self))
