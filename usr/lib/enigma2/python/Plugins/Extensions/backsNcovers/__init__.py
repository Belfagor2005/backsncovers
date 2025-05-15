#!/usr/bin/python
# -*- coding: utf-8 -*-

from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from os import environ
import gettext

PluginLanguageDomain = "backsNcovers"
PluginLanguagePath = "Extensions/backsNcovers/locale"


def localeInit():
	lang = language.getLanguage()[:2]
	environ["LANGUAGE"] = lang
	print("[backsNcovers] set language to ", lang)
	gettext.bindtextdomain(PluginLanguageDomain, resolveFilename(SCOPE_PLUGINS, PluginLanguagePath))


def _(txt):
	t = gettext.dgettext(PluginLanguageDomain, txt)
	if t == txt:
		print("[backsNcovers] fallback to default Enigma2 Translation for", txt)
		t = gettext.gettext(txt)
	return t


localeInit()
language.addCallback(localeInit)
