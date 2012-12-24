#!/usr/bin/python
# coding: UTF-8
# 
# Copyright (C) 2010 - Edwin Stang
# Copyright (C) 2012 - Shikhar Mall <mall.shikhar.in@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301  USA.

from gi.repository import GObject, RB, Peas, GLib, Gdk, Notify
from Xlib import display, X, error
from urlparse import urlparse
import os
import Xlib
import urllib

Gdk.threads_init()

class DeleteFilePlugin(GObject.Object, Peas.Activatable):
  __gtype_name__ = 'DeleteFilePlugin'
  object = GObject.property(type=GObject.Object)

  CtrlModifier = Xlib.X.ControlMask
  ShiftModifier = Xlib.X.ShiftMask
  CapsLockModifier = Xlib.X.LockMask
  NumLockModifier = Xlib.X.Mod2Mask
  
  __BAD_ACCESS = error.CatchError(error.BadAccess)

  # Ctrl+Shift+'Delete'
  delete_key = 119

  modifier_combinations = (
    CtrlModifier | ShiftModifier,
    CtrlModifier | ShiftModifier | NumLockModifier,
    CtrlModifier | ShiftModifier | CapsLockModifier,
    CtrlModifier | ShiftModifier | NumLockModifier | CapsLockModifier)

  display = None
  root = None

  def __init__(self):
    '''
    init plugin
    '''
    super(DeleteFilePlugin, self).__init__()

  def do_activate(self):
    '''
    register hotkey, tell X that we want keyrelease events and start
    listening
    '''
    self.display = Xlib.display.Display()
    self.root = self.display.screen().root
    self.display.allow_events(Xlib.X.AsyncKeyboard, Xlib.X.CurrentTime)
    self.root.change_attributes(event_mask = Xlib.X.KeyReleaseMask)
    self.register_hotkey()
    self.listener_src = GObject.timeout_add(300, self.listen_cb)
    Notify.init('Delete Current File Plugin')

  def do_deactivate(self):
    '''
    stop listening, unregister hotkey and clean up
    '''
    GObject.source_remove(self.listener_src)
    self.unregister_hotkey()
    self.display.close()
    self.root = None
    self.display = None
    self.listener_src = None

  def register_hotkey(self):
    '''
    register the hotkey
    '''
    for modifier in self.modifier_combinations:
      self.root.grab_key(self.delete_key, modifier, True, Xlib.X.GrabModeAsync, Xlib.X.GrabModeAsync)

  def unregister_hotkey(self):
    '''
    unregister the hotkey
    '''
    for modifier in self.modifier_combinations:
      self.root.ungrab_key(self.delete_key, modifier)

  def listen_cb(self):
    '''
    callback for listening, checks if the hotkey has been pressed
    '''
    Gdk.threads_enter()
    if self.root.display.pending_events() > 0:
      event = self.root.display.next_event()
      if (event.type == Xlib.X.KeyRelease) and (event.detail == self.delete_key):
        self.delete()

    Gdk.threads_leave()
    return True

  def delete(self):
    '''
    Deletes the currently playing song
    '''
    sp = self.object.props.shell_player
    cur_entry = sp.get_playing_entry()
    if not cur_entry:
      return

    uri = urlparse(cur_entry.get_string(RB.RhythmDBPropType.LOCATION))
    if uri.scheme != 'file':
      return

    fPath = urllib.unquote(uri.path)
    notification = Notify.Notification.new('Rhythmbox', os.path.basename(fPath), 'user-trash-full')
    notification.show()
    try:
      sp.do_next()
    except GLib.GError:
      pass
      
    db = self.object.props.db
    db.entry_move_to_trash(cur_entry)

