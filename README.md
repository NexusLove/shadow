# shadow
## A plugin based selfbot designed to enrich the discord experience

Shadow is an application that provides discord selfbot functionality.
Specifically it's intended to improve a users discord experience through the use of plugins.

Quickly an efficient perform complex calculations, browse youtube, imgur or reddit with the use of the builtins.

## Install

All you'll need is pip and git:

 - `pip install git+https://github.com/mental32/shadow#egg=shadow`

## Plugins

Plugs provide the ability to easily extend the functionality of shadow to your own needs.
On the surface, plugins are regular python packages that you can install via pip, poetry, pipenv etc.
What makes a package a plugin is that it's a namespaced package, more specifically it's located in `shadow.ext.NAME`

Onced you've installed the plugin package, you can enable it by adding the option `--use PLUGIN_NAME`.

### *builtins*

The builtins package comes, you guessed it, built in.
It aims to provide commonly used utilities and helper plugins.

The builtins package is enabled by default, in order to disable it pass the `--discard builtins` option.
