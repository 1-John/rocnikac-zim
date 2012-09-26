from __future__ import with_statement

import gobject

import os
import re
import sys
import shutil
import errno
import codecs
import logging

import zim
from zim.errors import Error, TrashNotSupportedError, TrashCancelledError
from zim.parsing import url_encode, url_decode
from zim.async import AsyncOperation, AsyncLock



import gtk
from zim.plugins import PluginClass
import logging
from zim.fs import File
from zim.notebook import Path, Page#todelete
from string import rfind
logger = logging.getLogger('zim.plugins.splitjoin')

ui_actions = (
	# name, stock id, label, accelerator, tooltip, readonly
	('split_file', gtk.STOCK_CUT, _('Split page'),  '', 'Splits current page on more on its level by divisor "-----"',True), # T: menu item
	('join_file', gtk.STOCK_CONNECT, _('Join pages'),  '', 'Apends childrens to current father', True), # T: menu item
)#FIXME odmacknout po kliknuti

#toolbar icon
ui_xml = '''
<ui>
	<menubar name='menubar'>
		<menu action='edit_menu'>
			<placeholder name='plugin_items'>
				<menuitem action='split_file'/>
				<menuitem action='join_file'/>
			</placeholder>
		</menu>
	</menubar>
	<toolbar name='toolbar'>
		<placeholder name='tools'>
			<toolitem action='split_file'/>
			<toolitem action='join_file'/>
		</placeholder>
	</toolbar>
</ui>
'''


class SplittingPlugin(PluginClass):

	plugin_info = {
		'name': _('Split & Join'), # T: plugin name
		'description': _('''\
Split & Join
This plugin is still under development.
'''), # T: plugin description
		'author': 'Jan Pacovsky',
		#~ 'help': 'Plugins:SplitJoinPlugin',
	}
	#dline = '-----' #dividing line
	
	def initialize_ui(self, ui):
		self.ui.add_actions(ui_actions, self)
		self.ui.add_ui(ui_xml, self)

	def get_path_context_from_self(self,a):
		try:
			b = a.ui._get_path_context() 
		except AttributeError: #old zim compatibility
			b = a.ui.get_path_context() 
		finally:
			return b

	def compare_namespaces(self,a,b):
		x=a.basename
		y=b.basename
		if x < y:
			
			return -1
		if y < x:
			return 1
		return 0

	def is_heading(self,string):
		if string[-2:] == "==":
			if string[0:2] == "==":
				return True
		return False

	def fix_headings(self,string):
		i=3
		while (string[-i]  == "=") & (string[i-1] == "="):
			i+=1
		return string[0:-i+1]# [0:-i+1] vs [0:-i] TODO check

	def join_file(self):
		self.join_file_try_with_fix_heading_and_then_append()
		
		

	def join_file_try_with_fix_heading_and_then_append(self):
		path = self.get_path_context_from_self(self)
		if not path.haschildren:
			#TODO error msg 	
			return

		namespace = path + ":"
		pages = list(self.ui.notebook.get_pagelist(namespace))
		text = ""
		pages.sort( self.compare_namespaces)#grab it as it seems in the tree
	
		#end = -6 #how many end position should be taken (5 + dos endling 2pos unix, rest 1 pos)
		end =1 
		if self.ui.page.source.endofline == 'dos': 
			end = 2
		headings = []
		for page in pages:
			self.ui.open_page(page)
			lines = page.source._content[4:] # skip the heading info -format
			fileText = ""
			for line in lines:
				if self.is_heading(line[:-end]):
					headings = headings + [line]
					line = self.fix_headings(line[:-end]) + line[-end:] #+ ending \r \n or both
				fileText += line
			text +=  '-----\n' + fileText
			#or TODO: text +=  dline + '\n' + fileText
		self.ui.open_page(path)	
		self.fin(text)
#		self.disconnect()
		self.ui.open_page(path)		
		self.ui.append_text_to_page(path, text)
		#self.ui.open_page(path)		

	def fin(self,writeBuffer):
		context = self.get_path_context_from_self(self)
		fileOnDisk = context.source.path
		
		f = open(fileOnDisk, 'a')
		f.write(writeBuffer)
		f.close()

	def join_file_append_to_parent(self):
		action = self.actiongroup.get_action('join_file')
		path = self.get_path_context_from_self(self)
		if path.haschildren:
			namespace = path + ":"
			pages = list(self.ui.notebook.get_pagelist(namespace))
		text = ""
		pages.sort( self.compare_namespaces)#grab it as it seems in the tree
			 
		for page in pages:
			self.ui.open_page(page)
			lines = page.source._content[4:] # skip the heading info -format
			fileText = ""
			for line in lines:
				fileText += line
			text +=  '-----\n' + fileText
			#or TODO: text +=  dline + '\n' + fileText
				
		self.ui.append_text_to_page(path, text)
		self.ui.open_page(path)
		#TODO error msg in else
		
		
	
		
			
	def split_file_verze_s_delenim_na_uroven_pres_zim(self):

		action = self.actiongroup.get_action('split_file')
		namespace = self.get_path_context_from_self(self)
		namespace.name = namespace.name + ":"
		
		if not self.ui.page.hascontent:
			#TODO error msg (nedel prazdou str)
			return

		lines = self.ui.page.source._content[4:] # skip the heading info -format
		
		writeBuffer = ""
		end = -6 #how many end position should be taken (5 + dos endling 2pos unix, rest 1 pos) 
		if self.ui.page.source.endofline == 'dos': 
			end = -7
		int = 0
		for line in lines:

			line_end= line[end:]
			is_split_delimiter_found = line_end[:5] == "-----" #or dline

			if is_split_delimiter_found:

				writeBuffer += line_end[:5]
				self.ui.new_page_from_text(writeBuffer,name=namespace)
				writeBuffer = ''
			else:
				writeBuffer += line
				
		if writeBuffer != "":	
			self.ui.new_page_from_text(writeBuffer,namespace)
	
	def new_page_from_text_podle_me(self,writeBuffer,namespace,int=0):#zatim jen kostra TODO
		
		int+=1
		fint= 'D:\\Temp\\zPLIT' + int.__str__() + '.txt'
		f = open(fint, 'w')
		f.write(writeBuffer)
		f.close()
		file = File(fint)
		dialog = zim.gui.ImportPageDialog(self.ui)
		dialog.set_file(file)
		self.do_response_ok(file)

	
	def split_file(self):
		page = self.ui.page
		soruce = page.source
		self.split_file_verze_s_delenim_na_uroven_pres_zim()

	def do_response_ok(self, file):

		basename = file.basename
		if basename.endswith('.txt'):
			basename = basename[:-4]

		path = self.ui.notebook.resolve_path(basename)
		page = self.ui.notebook.get_page(path)
		if page.hascontent:
			path = self.ui.notebook.index.get_unique_path(path)
			page = self.ui.notebook.get_page(path)
			#assert not page.hascontent

		page.parse('wiki', file.readlines())
		self.ui.notebook.store_page(page)
		self.ui.open_page(page)
		return True
