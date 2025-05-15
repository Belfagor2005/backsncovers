#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

#######################################################################
# maintainer: <schomi@vuplus-support.org>
# This plugin is free software, you are allowed to
# modify it (if you keep the license),
# but you are not allowed to distribute/publish
# it without source code (this version and your modifications).
# This means you also have to distribute
# source code of your modifications.
#
# modded and fix from lululla 20250515
#######################################################################

# Enigma2
from Components.config import config, ConfigSelection, ConfigSubsection, ConfigYesNo

# Plugin internals
from Plugins.Plugin import PluginDescriptor
from . import _
from . import backsNcovers


config.plugins.backsNcovers = ConfigSubsection()
config.plugins.backsNcovers.themoviedb_coversize = ConfigSelection(default="w500", choices=["w92", "w185", "w500", "original"])
config.plugins.backsNcovers.language = ConfigSelection(default="en", choices=[("de", "DE"), ("en", "EN"), ("fr", "FR"), ("es", "ES"), ("it", "IT"), ("pl", "PL"), ("ru", "RU"), ("", "All")])
config.plugins.backsNcovers.backdrops = ConfigYesNo(default=False)
config.plugins.backsNcovers.filebot = ConfigYesNo(default=False)
config.plugins.backsNcovers.closeafter = ConfigYesNo(default=False)


def main(session, service, **kwargs):
	try:
		from importlib import reload
	except:
		from imp import reload
	reload(backsNcovers)
	try:
		session.open(backsNcovers.backsNcoversScreen, service, session.current_dialog, **kwargs)
	except:
		import traceback
		traceback.print_exc()


def Plugins(**kwargs):
	return [PluginDescriptor(name=_("backsNcovers"), description=_("Find Backdrops & Covers ..."), where=PluginDescriptor.WHERE_MOVIELIST, fnc=main, needsRestart=False)]
