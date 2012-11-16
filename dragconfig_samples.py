#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Pattern 0: watch all files, act on changes


# Pattern 1: watch some files, act on changes, each pattern maps to a certain action

def styl_action():
    pass

WATCHES_ACTIONS = [
    ('*.styl', styl_action),
]

ASYNC = False


# Pattern 2: watch some files, act on changes

def do_make():
    pass

WATCHES = ['*.md']

ASYNC = False

GLOBAL_ACTION = do_make


# Pattern 3: watch all except the ignored ones, act on changes

def do_compile():
    pass

IGNORES = ['dir0/dir1/*.py', 'dir2/']

# FORCE_FOCUSES = ['.o']

GLOBAL_ACTION = do_compile

ASYNC = False
