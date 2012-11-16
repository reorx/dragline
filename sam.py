#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import sys
from dragline import conditional_walk


_abspath = os.path.abspath


for dirpath, dirnames, filenames in conditional_walk(sys.argv[1], []):
    print 'dirpath: %s' % dirpath
    print _abspath(dirpath)
    print '----dirnames:'
    for i in dirnames:
        print i
    print '----filenames'
    for i in filenames:
        print i
    print '====\n'
