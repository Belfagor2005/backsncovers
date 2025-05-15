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

# Standard library
from base64 import b64decode
from os.path import exists
from os import mkdir
from re import escape, sub, I, S, search as re_search
from shutil import copy, rmtree
import subprocess

# Third-party
from twisted.internet import defer

# Enigma2 - Components
from Components.AVSwitch import AVSwitch
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.ConfigList import ConfigListScreen
from Components.GUIComponent import GUIComponent
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components.config import config, configfile, getConfigListEntry

# Enigma2 - Screens
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
import skin

# Enigma2 - Tools
from Tools.Directories import fileExists

# Enigma2 - enigma
from enigma import (
	RT_HALIGN_LEFT,
	RT_VALIGN_CENTER,
	RT_WRAP,
	eListbox,
	eListboxPythonMultiContent,
	ePicLoad,
	eServiceCenter,
	gFont
)

# Local imports
from . import _
from . import tmdbsimple as tmdb


tmdb.API_KEY = b64decode('M2MzZWZjZjQ3YzM1Nzc1NTg4MTJiYjlkNjQwMTlkNjU=')

pname = _("backsNcovers")
pdesc = _("Find Backdrops and Covers for Movielist")
pversion = "v.1.0-r0"
pdate = "20250515"
tempDir = "/tmp/backsNcovers/"


def cleanFile(text):
	cutlist = [
		'x264', '720p', '1080p', '1080i', 'PAL', 'GERMAN', 'ENGLiSH', 'WS', 'DVDRiP', 'UNRATED',
		'RETAIL', 'Web-DL', 'DL', 'LD', 'MiC', 'MD', 'DVDR', 'BDRiP', 'BLURAY', 'DTS', 'UNCUT', 'ANiME',
		'AC3MD', 'AC3', 'AC3D', 'TS', 'DVDSCR', 'COMPLETE', 'INTERNAL', 'DTSD', 'XViD', 'DIVX', 'DUBBED',
		'LINE.DUBBED', 'DD51', 'DVDR9', 'DVDR5', 'h264', 'AVC', 'WEBHDTVRiP', 'WEBHDRiP', 'WEBRiP',
		'WEBHDTV', 'WebHD', 'HDTVRiP', 'HDRiP', 'HDTV', 'ITUNESHD', 'REPACK', 'SYNC'
	]

	extensions = ['.wmv', '.flv', '.ts', '.m2ts', '.mkv', '.avi', '.mpeg', '.mpg', '.iso', '.mp4']

	# Remove extensions
	for ext in extensions:
		text = text.replace(ext, '')

	# Remove words in cutlist preceded or followed by separator or string edges
	for word in cutlist:
		pattern = r'(^|[\._\-\+])' + escape(word) + r'([\._\-\+]|$)'
		text = sub(pattern, ' ', text, flags=I)

	# Replace separators with spaces and clean multiple spaces
	text = sub(r'[.\-_+]', ' ', text)
	text = sub(r'\s+', ' ', text).strip()

	return text


def cleanEnd(text):
	text = text.replace('.wmv', '').replace('.flv', '').replace('.ts', '').replace('.m2ts', '').replace('.mkv', '').replace('.avi', '').replace('.mpeg', '').replace('.mpg', '').replace('.iso', '').replace('.mp4', '')
	return text


def cleanFileBotPattern(text):
	text = sub(r'\(\d\d\d\d\)', '', text)
	return text


class PicLoader:
	def __init__(self, width, height, sc=None):
		self.picload = ePicLoad()
		if (not sc):
			sc = AVSwitch().getFramebufferScale()
		self.picload.setPara((width, height, sc[0], sc[1], False, 1, "#00000000"))

	def load(self, filename):
		self.picload.startDecode(filename, 0, 0, False)
		data = self.picload.getData()
		return data

	def destroy(self):
		del self.picload


class backsNcoversConfigScreen(Screen, ConfigListScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["backsNcoversConfigScreen", "Setup"]
		self.setup_title = _("backsNcovers Setup")

		self.onChangedEntry = []
		self.list = []
		ConfigListScreen.__init__(self, self.list, session=session, on_change=self.changedEntry)

		self["actions"] = ActionMap(
			["bNcActions"],
			{
				"cancel": self.keyCancel,
				"save": self.keyOK,
				"red": self.keyCancel,
				"green": self.keyGreen
			},
			-2
		)

		self["key_green"] = StaticText(_("OK"))
		self["key_red"] = StaticText(_("Cancel"))

		self.list = []
		self.createConfigList()
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(pname + " (" + pversion + " - " + pdate + ")")

	def createConfigList(self):
		self.list = []
		self.list.append(getConfigListEntry(_("Picture resolution:"), config.plugins.backsNcovers.themoviedb_coversize))
		self.list.append(getConfigListEntry(_("Language:"), config.plugins.backsNcovers.language))
		self.list.append(getConfigListEntry(_("Start with Backdrops:"), config.plugins.backsNcovers.backdrops))
		self.list.append(getConfigListEntry(_("FileBot Pattern:"), config.plugins.backsNcovers.filebot))
		self.list.append(getConfigListEntry(_("Close after selection:"), config.plugins.backsNcovers.closeafter))
		self["config"].list = self.list
		self["config"].setList(self.list)

	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def keyGreen(self):
		for x in self["config"].list:
			x[1].save()
		configfile.save()
		self.close()

	def keyOK(self):
		self.keyGreen()


class backsNcoversScreen(Screen, HelpableScreen):
	skin = """
		<screen position="40,40" size="1200,1080" title=" " >
			<widget name="searchinfo" position="10,10" size="1180,50" font="Regular;24" foregroundColor="#00fff000" noWrap="1"/>
			<widget name="list" position="10,65" size="1180,900" scrollbarMode="showOnDemand"/>
			<widget name="key_red" position="50,990" size="260,30" transparent="1" font="Regular;20"/>
			<widget name="key_green" position="350,990" size="260,30" transparent="1" font="Regular;20"/>
			<widget name="key_yellow" position="630,990" size="260,30" transparent="1" font="Regular;20"/>
			<widget name="key_blue" position="910,990" size="260,30" transparent="1" font="Regular;20"/>
			<ePixmap position="10,993" size="260,30" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/backsNcovers/pic/button_red.png" transparent="1" alphatest="on"/>
			<ePixmap position="310,993" size="260,30" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/backsNcovers/pic/button_green.png" transparent="1" alphatest="on"/>
			<ePixmap position="590,993" size="260,30" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/backsNcovers/pic/button_yellow.png" transparent="1" alphatest="on"/>
			<ePixmap position="870,993" size="260,30" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/backsNcovers/pic/button_blue.png" transparent="1" alphatest="on"/>
			<eLabel text="EPG" position="1130,990" size="50,30" transparent="1" font="Regular;20"/>
		</screen>"""

	def __init__(self, session, service, parent, args=0):
		Screen.__init__(self, session, parent=parent)
		self.session = session

		if exists(tempDir) is False:
			mkdir(tempDir)

		self.isDirectory = False
		serviceHandler = eServiceCenter.getInstance()
		info = serviceHandler.info(service)
		path = service.getPath()
		self.savePath = path
		self.dir = '/'.join(path.split('/')[:-1]) + '/'
		self.file = self.baseName(path)
		if path.endswith("/") is True:
			path = path[:-1]
			self.file = self.baseName(path)
			self.text = self.baseName(path)
			self.isDirectory = True
		else:
			self.text = cleanFile(info.getName(service))
			self.isDirectory = False

		if self.text == "":
			self.text = _("virtual folder not possible!")

		HelpableScreen.__init__(self)
		self["actions"] = HelpableActionMap(self, "bNcActions", {
			"ok": (self.ok, _("Save Cover or Backdrop")),
			"cancel": (self.cancel, _("Exit")),
			"green": (self.goGreen, _("Search Text ...")),
			"yellow": (self.goYellow, _("Find Series")),
			"blue": (self.goBlue, _("Find Movies")),
			"red": (self.goRed, _("Show Backdrops or Covers")),
			"eventview": (self.search4all, _("Find all movies or series")),
			"menu": (self.goMenu, _("Setup"))
		}, -1)

		self.type = 0  # 0 = movies, 1 = tv
		self.max = 40  # No. of results, TMDB rule, 40 possible every 10 sec.
		self.backdrop = config.plugins.backsNcovers.backdrops.value
		self.lang = config.plugins.backsNcovers.language.value
		if self.lang == "all":
			self.lang = ""
		self.filebot = config.plugins.backsNcovers.filebot.value
		self.closeafter = config.plugins.backsNcovers.closeafter.value
		self.anz = 0

		if self.backdrop:
			self.text1 = _("Backdrops")
			self.text2 = _("Covers")
		else:
			self.text1 = _("Covers")
			self.text2 = _("Backdrops")

		self['searchinfo'] = Label(_("TMDb search"))
		self['key_red'] = Label(self.text2)
		self['key_green'] = Label(_("Search Text ..."))
		self['key_yellow'] = Label(_("Find Series"))
		self['key_blue'] = Label(_("Find Movies"))
		self['list'] = createbacksNcoversList()

		self.setTitle(pname)
		self.onLayoutFinish.append(self.onFinish)

	def onFinish(self):
		self.setTitle((pname + " [%s]") % self.lang)
		if re_search(r'[Ss][0-9]+[Ee][0-9]+', self.text):
			self.text = sub('[Ss][0-9]+[Ee][0-9]+.*[a-zA-Z0-9_]+', '', self.text, flags=S | I)
			print("[backsNcovers] ", self.text)
			self.type = 1
			self.getCoverMovie()
		else:
			if self.filebot:
				self.text = cleanFileBotPattern(self.text)
			try:
				search = tmdb.Search()
				json_data = search.multi(query=self.text, language=self.lang)
				for entries in json_data['results']:
					try:
						# title = str(entries['title'])
						self.type = 0
						break
					except:
						self.type = 1
						break
				self.getCoverMovie()
			except:
				self['searchinfo'].setText(_("TMDb does not respond, try again later!"))

	def onRelaunch(self):
		self.setTitle((pname + " [%s]") % self.lang)
		self['searchinfo'].setText(_("TMDb search, %s for %s") % (self.text1, self.text))
		self.getCoverMovie()

	def goRed(self):
		if self.backdrop:
			self.backdrop = False
			self['key_red'].setText(self.text1)
			self.text1 = _("Covers")
		else:
			self.backdrop = True
			self['key_red'].setText(self.text1)
			self.text1 = _("Backdrops")
		self.onRelaunch()

	def goGreen(self):
		self.manSearch()

	def goYellow(self):
		self.text = sub('[Ss][0-9]+[Ee][0-9]+.*[a-zA-Z0-9_]+', '', self.text, flags=S | I)
		self.type = 1
		self.getCoverMovie()

	def goBlue(self):
		self.type = 0
		self.getCoverMovie()

	def goMenu(self):
		self.session.open(backsNcoversConfigScreen)

	def search4all(self):
		if self.lang == "":
			self.lang = config.plugins.backsNcovers.language.value
		else:
			self.lang = ""
		self.onRelaunch()

	def manSearch(self):
		self.session.openWithCallback(self.manSearchCB, VirtualKeyBoard, title=(_("Search for:")), text=self.text)

	def manSearchCB(self, text):
		if text:
			self.text = text
			self.getCoverMovie()

	def getCoverMovie(self):
		try:
			if self.lang == "":
				self.max = 6
			else:
				self.max = 40
			search = tmdb.Search()
			self['searchinfo'].setText(_("Loading %s for %s") % (self.text1, self.text) + " ...")

			if self.type == 0:
				search.movie(query=self.text, language=self.lang)
			elif self.type == 1:
				search.tv(query=self.text, language=self.lang)

			if not search.results:
				self['searchinfo'].setText(_("No results found for %s!") % self.text)
				return

			self.piclist = []
			urls = []
			self['list'].setList([], 'Empty')
			x = 1

			for movies in search.results:
				if self.type == 0:
					identity = tmdb.Movies(movies['id'])
					self.field = "title"
				else:
					identity = tmdb.TV(movies['id'])
					self.field = "name"

				images = identity.images(language=self.lang)

				if self.backdrop:
					for results in images['backdrops']:
						if results is not []:
							id = str(movies['id']) + "-" + str(x)
							title = str(movies[self.field])
							coverPath = str(results['file_path'])
							coverUrl = "http://image.tmdb.org/t/p/%s%s" % (config.plugins.backsNcovers.themoviedb_coversize.value, coverPath)
							urls.append((title, coverUrl, id))
							x += 1
							if x > self.max:
								x = 1
								break
				else:
					for results in images['posters']:
						if results is not []:
							id = str(movies['id']) + "-" + str(x)
							title = str(movies[self.field])
							coverPath = str(results['file_path'])
							coverUrl = "http://image.tmdb.org/t/p/%s%s" % (config.plugins.backsNcovers.themoviedb_coversize.value, coverPath)
							urls.append((title, coverUrl, id))
							x += 1
							if x > self.max:
								x = 1
								break

			if len(urls) != 0:
				self.anz = len(urls)
				ds = defer.DeferredSemaphore(tokens=self.max)
				downloads = [ds.run(self.download, url, title, id).addCallback(self.buildList, title, url, id, "movie").addErrback(self.dataError) for title, url, id in urls]
				defer.DeferredList(downloads).addErrback(self.dataError).addCallback(self.dataFinish)
			else:
				if self.type == 0:
					self['searchinfo'].setText(_("No movie results, %s for %s") % (self.text1, self.text))
				elif self.type == 1:
					self['searchinfo'].setText(_("No series results, %s for %s") % (self.text1, self.text))
				else:
					self['searchinfo'].setText(_("No results, %s for %s") % (self.text1, self.text))
				if not self.lang == "":
					self.lang = ""
					self.onRelaunch()
		except Exception as e:
			self['searchinfo'].setText(_("Error: {0}").format(str(e)))
			print("[backsNcovers] API Error:", str(e))

	def download(self, url, title, id):
		if self.backdrop:
			subprocess.call(["wget", "-q", "--no-use-server-timestamps", "--no-clobber", "--timeout=5", url, "-O", tempDir + title + '_' + id + '-bdp' + '.jpg'])
		else:
			subprocess.call(["wget", "-q", "--no-use-server-timestamps", "--no-clobber", "--timeout=5", url, "-O", tempDir + title + '_' + id + '.jpg'])

	def buildList(self, data, title, url, id, type):
		if self.backdrop:
			path = tempDir + title + '_' + id + '-bdp.jpg'
		else:
			path = tempDir + title + '_' + id + '.jpg'

		if exists(path):
			self.piclist.append(((title, path, id, type),))
		else:
			print(f"Image {path} not found!")

		self['list'].setList(self.piclist, type)

	def ok(self):
		check = self['list'].getCurrent()
		if check is None:
			return

		bild = self['list'].getCurrent()[1]
		# idx = self['list'].getCurrent()[2]
		# type = self['list'].getCurrent()[3]
		checkPath = self.savePath
		savePath = cleanEnd(self.savePath)

		if fileExists(bild) and fileExists(checkPath):
			try:
				if self.backdrop:
					if self.isDirectory:
						copy(bild, savePath + "folder.bdp.jpg")
					else:
						copy(bild, savePath + ".bdp.jpg")
				else:
					if self.isDirectory:
						copy(bild, savePath + "folder.jpg")
					else:
						copy(bild, savePath + ".jpg")
			except:
				print("[backsNcovers] User rights are not sufficiently!")
				self.session.open(MessageBox, _("Error saving image:\nUser rights insufficient."), MessageBox.TYPE_ERROR)
				return
		else:
			self['searchinfo'].setText(_("TMDb result, %s") % (self.text1) + _(" ... not saved!"))
			if not self.closeafter:
				self.session.open(MessageBox, _("Image not saved.\nMissing source or target path."), MessageBox.TYPE_ERROR)
			return

		if self.closeafter:
			self.okDelete()
			self.close(False)
		else:
			self['searchinfo'].setText(_("TMDb result, %s") % (self.text1[:-1]) + _(" ... saved!"))
			self.session.open(MessageBox, _("Image successfully saved."), MessageBox.TYPE_INFO)

	def okDelete(self):
		try:
			rmtree(tempDir)
		except:
			pass

	def dataError(self, error):
		print("[backsNcovers] " + "ERROR:", error)

	def dataFinish(self, res):
		if self.type == 0:
			self['searchinfo'].setText(_("TMDb movie results, %s %s for %s") % (self.anz, self.text1, self.text))
		elif self.type == 1:
			self['searchinfo'].setText(_("TMDb series results, %s %s for %s") % (self.anz, self.text1, self.text))
		else:
			pass

	def cancel(self):
		self.okDelete()
		self.close(False)

	def baseName(self, str):
		name = str.split('/')[-1]
		return name


class createbacksNcoversList(GUIComponent, object):
	GUI_WIDGET = eListbox

	def __init__(self):
		GUIComponent.__init__(self)
		self.listbox = eListboxPythonMultiContent()
		font, size = skin.parameters.get("backsNcoversListFont", ('Regular', 23))
		self.listbox.setFont(0, gFont(font, size))
		self.listbox.setItemHeight(int(skin.parameters.get("backsNcoversItemHeight", (300,))[0]))
		self.listbox.setBuildFunc(self.buildList)

	def buildList(self, entry):
		# width = self.l.getItemSize().width()
		_ = self.listbox.getItemSize().width()
		(title, bild, id, type) = entry
		res = [None]

		x, y, w, h = skin.parameters.get("backsNcoversCover", (0, 0, 450, 300))
		self.picloader = PicLoader(w, h)
		bild = self.picloader.load(bild)
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, x, y, w, h, bild))
		self.picloader.destroy()

		x, y, w, h = skin.parameters.get("backsNcoversName", (500, 100, 670, 100))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER | RT_WRAP, str(title)))
		return res

	def getCurrent(self):
		cur = self.listbox.getCurrentSelection()
		return cur and cur[0]

	def postWidgetCreate(self, instance):
		instance.setContent(self.listbox)
		# self.instance.setWrapAround(True)

	def preWidgetRemove(self, instance):
		instance.setContent(None)

	def setList(self, list, type):
		self.type = type
		self.listbox.setList(list)

	def moveToIndex(self, idx):
		self.instance.moveSelectionTo(idx)

	def getSelectionIndex(self):
		return self.listbox.getCurrentSelectionIndex()

	def getSelectedIndex(self):
		return self.listbox.getCurrentSelectionIndex()

	def selectionEnabled(self, enabled):
		if self.instance is not None:
			self.instance.setSelectionEnable(enabled)

	def pageUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageUp)

	def pageDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageDown)

	def up(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)

	def down(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)
