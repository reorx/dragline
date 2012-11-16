#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pyinotify

"""
Masks of command

mv:
    IN_MOVED_TO
touch:
    IN_CREATE
    IN_OPEN
    IN_ATTRIB
    IN_CLOSE_WRITE
vim:
    (
    IN_OPEN|IN_ISDIR
    IN_CLOSE_NOWRITE|IN_ISDIR
    ) * many

vim:w :

vim:wq :
    IN_CREATE
    IN_OPEN
    IN_MODIFY
    IN_CLOSE_WRITE

"""


wm = pyinotify.WatchManager()  # Watch Manager
mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE  # watched events


class EventHandler(pyinotify.ProcessEvent):
    def process_IN_CREATE(self, event):
        print "Creating:", event.pathname

    def process_IN_DELETE(self, event):
        print "Removing:", event.pathname

handler = EventHandler()
notifier = pyinotify.Notifier(wm, handler)
wdd = wm.add_watch('/tmp', mask, rec=True)

notifier.loop()
