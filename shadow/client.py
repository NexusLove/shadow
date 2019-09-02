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

    __plugins: Set[Plugin] = set()

    async def _plugin_dispatch_reactor(
        self,
        event: str,
        args: List[Any],
        kwargs: Dict[Any, Any],
        tasks: List[asyncio.Task],
    ) -> None:
        """React and dispatch exceptions from plugin dispatch tasks.

        Parameters
        ----------
        event : :class:`str`
            The event being dispatched.
        args : List[Any]
            Dispatch handler args.
        kwargs : Dict[Any, Any]
            Dispatch handler kwargs.
        tasks : List[:class:`asyncio.Task`]
            The active tasks to observe and react to.
        """
        bucket = tasks

        while bucket:
            await asyncio.sleep(0.1)
            bucket = []

            for task in tasks:
                done = err = task.done() and task.exception()

                if not isinstance(err, Exception) and not done:
                    bucket.append(task)
                    continue

                LOGGER.error('Dispatch task=%s with reason %s', repr(task), repr(err))

                self._direct_dispatch('dispatch_error', err, event, args, kwargs)

            tasks = bucket

    _direct_dispatch = discord.Client.dispatch

    def dispatch(self, event, *args, **kwargs):
        tasks: List[asyncio.Task] = [
            list(plugin.dispatch(event, *args, **kwargs)) for plugin in self.__plugins
        ]

        self.loop.create_task(self._plugin_dispatch_reactor(event, args, kwargs, tasks))

        super().dispatch(event, *args, **kwargs)

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
                LOGGER.info('Attempting to load exposed plugin: %s', value)
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
