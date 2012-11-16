#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import fnmatch
import logging
from subprocess import Popen
import shlex
import copy
import itertools
import inspect


_dragline_dirpath = os.path.abspath(os.path.dirname(__file__))
_dragline_filenames = filter(
    lambda x: os.path.isfile(x) and fnmatch.fnmatch(x, '*.py'),
    os.listdir(_dragline_dirpath))
_dragline_filepaths = [os.path.join(_dragline_dirpath, i) for i in _dragline_filenames]

logging.debug('dragline dirpath: %s' % _dragline_dirpath)
logging.debug('dragline filenames: %s' % _dragline_filenames)
logging.debug('dragline filepaths: %s' % _dragline_filepaths)


class ObjectDict(dict):
    """
    retrieve value of dict in dot style
    """
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError('Has no attribute %s' % key)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError(key)

    def __str__(self):
        return '<ObjectDict %s >' % dict(self)


# `_dir_ignores` overlooks relative path
# and only matches the name of directory
# so .git/ ignore any directory named '.git',
# if you want's to only ignore some/where/.git/,
# remove '.git/' in `_dir_ignores`
# and add 'some/where/.git/' in dragconfig.IGNORES
_dir_ignores = set(['.git/', '.hg/', '.svn/'])

_ext_ignores = set(['*.pyc', '.pyo', '.swp', '.swo', '.o'])


def run_cmd(cmd_str):
    cmd_list = shlex.split(cmd_str)

    p = Popen(cmd_list)

    return p


class ActionHandler(object):
    def added(self):
        raise NotImplementedError('no added method defined')

    def modified(self):
        raise NotImplementedError('no added method defined')

    def removed(self):
        raise NotImplementedError('no added method defined')


class Dragline(object):

    def __init__(self, root, ignores=[], watches=[], handlers=[], global_handler=None,
                 interval=300, recursive=True):
        """
        possible keywork arguments:
            None
                monitor all files
            global_handler
                monitor all files, call global_handler when change happens
            ignores
                monitor all files except that matches ignores
            ignores, global_handler
                call global_handler when change happens
            ignores, handlers
                call handlers for each matched file
            watches
                monitor files that matches watches
            watches, global_handler
                call global_handler when change happens
            watches, handlers
                call handlers for each matched file
            handlers
                monitor files that matches watches,
                call function for each watch rules
        """
        # check kwargs
        assert not (ignores and watches), 'ignores and watches could not both exist'

        # assign values
        self.root = root
        # NOTE is it nessessary to check path is legal or not ?
        self.ignores = ignores
        self.watches = watches
        #self.watches_handlers = watches_handlers
        self.handlers = handlers
        self.global_handler = global_handler
        self.interval = interval
        self.recursive = recursive

        # make walk function
        self._make_walk_func()

    def log_info(self, changes):
        log = 'Changes:\n'
        for t, l in changes.iteritems():
            if l:
                for i in l:
                    log += '[%s] %s\n' % (t, i)

        logging.debug(log)

    def start(self):
        """
        Start monitoring
        """
        last_paths = self.get_paths()

        while True:
            current_paths = self.get_paths()

            changes, change_list = self.get_changes(current_paths, last_paths)

            if change_list:
                self.log_info(changes)

                # reload if dragline package changed
                for i in change_list:
                    if i in _dragline_filepaths:
                        print 'dragline package files changed, reload the process..\n'
                        os.execv(sys.executable, [sys.executable] + sys.argv)
                        sys.exit(0)

                if not self.act is None:
                    logging.debug('Act on changes')
                    self.act(changes)

            last_paths = current_paths

            time.sleep(float(self.interval) / 1000)

    def get_paths(self):
        paths = {}
        for dirpath, dirnames, filenames, filepaths in self.walk():

            # skip getting directory path since we are only interested in files

            for i in filepaths:
                paths[i] = os.stat(i).st_mtime
        return paths

    def get_changes(self, current_paths, last_paths):
        changes = {
            'added': [],
            'modified': [],
            'removed': []
        }
        for path, mtime in current_paths.iteritems():
            if path in last_paths:
                if mtime != last_paths[path]:
                    changes['modified'].append(path)
            else:
                changes['added'].append(path)
        changes['removed'] = [i for i in last_paths if not i in current_paths]

        return changes, list(itertools.chain(*changes.itervalues()))

    def act(self, changes):

        if self.handlers:
            for _type, paths in changes.iteritems():
                for path in paths:
                    hdr = self.get_handler(path)
                    if not hdr:
                        continue
                    if inspect.isclass(hdr):
                        hdr_instance = hdr(self.root, path)
                        getattr(hdr_instance, _type)()
                    elif inspect.isfunction(hdr):
                        hdr(parse_path(self.root, path))
                    elif isinstance(hdr, (str, unicode)):
                        run_cmd(hdr)
                    else:
                        raise Exception('Handler type error, %s' % type(hdr))

        if self.global_handler:
            hdr = self.global_handler
            if inspect.isfunction(hdr):
                hdr()
            elif isinstance(hdr, (str, unicode)):
                run_cmd(hdr)
            else:
                raise Exception('Handler type error, %s' % type(hdr))

    def get_handler(self, path):
        for hdr in self.handlers:
            if fnmatch.fnmatch(path, hdr[0]):
                return hdr[1]
        return None

    def _make_walk_func(self):
        """
        generate a walk function (for efficiency purpose)

        `mode` takes effect only if conditions is not empty
        when `mode` is True, watch matches
        when False, ignore matches

        Determined by `watches`, `ignores`

        Conditions:
            watches [], ignores []
            watches [...]
            ignores [...]
        """

        def _rel_path(dirpath, name):
            rel_prefix = os.path.relpath(dirpath, self.root)
            if rel_prefix == '.':
                return name
            else:
                return os.path.join(rel_prefix, name)

        R = ObjectDict()
        R.dirs = set([])  # 'dir0/dir1/'
        R.exts = set([])  # '*.py'           priority high
        R.dir_exts = set([])  # 'dir0/*.py'  priority middle
        R.specs = set([])  # 'dir0/file.py'  priority low
        R.files = set([])  # conbination of exts | dir_exts | specs

        def analyse(rules):
            for i in rules:
                if i.endswith('/'):
                    # 'dir0/dir1/'
                    R.dirs.add(i[:-1])
                else:
                    dirpath, filename = os.path.split(i)
                    if filename.startswith('*.'):
                        if dirpath:
                            # 'dir0/*.py'
                            R.dir_exts.add(i)
                        else:
                            # '*.py'
                            R.exts.add(i)
                    else:
                        # 'dir0/file.py'
                        R.specs.add(i)

            R.files = R.exts | R.specs | R.dir_exts

            logging.debug('Rules:\ndirs: %s\nexts: %s\ndir_exts: %s\nspecs: %s' %
                          (R.dirs, R.exts, R.dir_exts, R.specs))

        def check_file(rel_path):
            # is_matched = False

            # for i in R.exts:
            #     if fnmatch.fnmatchcase(rel_path, i):
            #         is_matched = True
            #     break
            # if is_matched:
            #     return is_matched

            # for i in R.specs:
            #     if rel_path == i:
            #         is_matched = True
            #     break
            # if is_matched:
            #     return is_matched

            # for i in R.dir_exts:
            #     if fnmatch.fnmatchcase(rel_path, i):
            #         is_matched = True
            #     break

            # return is_matched

            if not os.path.isfile(rel_path):
                # this will ignore symbolic link file
                return False

            #if no R.files:
                #return True

            for i in R.files:
                if fnmatch.fnmatch(rel_path, i):
                    return True

            for i in R.dirs:
                if in_dir(rel_path, i):
                    return True

            return False

        def check_files(filenames, dirpath):
            _filenames = []
            _filepaths = []
            for i in filenames:
                rel_path = _rel_path(dirpath, i)
                if check_file(rel_path):
                    _filenames.append(i)
                    _filepaths.append(rel_path)
            return _filenames, _filepaths

        if self.watches:
            logging.debug('Detected Watch Mode, constructing walk function')

            analyse(self.watches)

            # cancel dir filtering
            if R.exts:
                def react(dirpath, dirnames, filenames):

                    # filenames[:] = [i for i in filenames
                    #                 if check_file(_rel_path(dirpath, i))]
                    filenames, filepaths = check_files(filenames, dirpath)
                    return dirpath, dirnames, filenames, filepaths
            else:
                allow_dirs = copy.copy(R.dirs)
                for i in R.dir_exts:
                    allow_dirs.add(os.path.dirname(i))
                logging.debug('allow dirs: %s' % allow_dirs)

                def react(dirpath, dirnames, filenames):
                    _dirnames = []
                    for i in dirnames:
                        i_rel_path = _rel_path(dirpath, i)
                        for j in allow_dirs:
                            if is_dir_family(j, i_rel_path):
                                _dirnames.append(i)
                                break
                    dirnames[:] = _dirnames

                    # filenames[:] = [i for i in filenames
                    #                 if check_file(_rel_path(dirpath, i))]
                    filenames, filepaths = check_files(filenames, dirpath)
                    #print 'filenames', filenames
                    return dirpath, dirnames, filenames, filepaths
        elif self.ignores:
            logging.debug('Detected Ignore Mode, constructing walk function')

            R.exts.update(_ext_ignores)
            R.files.update(_ext_ignores)

            def react(dirpath, dirnames, filenames):
                dirnames[:] = [i for i in dirnames
                               if (not i in _dir_ignores
                                   and not _rel_path(dirpath, i) in R.dirs)]

                # filenames[:] = [i for i in filenames
                #                 if check_file(_rel_path(dirpath, i))]
                filenames, filepaths = check_files(filenames, dirpath)
                return dirpath, dirnames, filenames, filepaths
        else:
            # actually the ignore mode with only _dir_ignores and _ext_ignores
            R.exts.update(_ext_ignores)
            R.files.update(_ext_ignores)

            def react(dirpath, dirnames, filenames):
                dirnames[:] = [i for i in dirnames
                               if not i in _dir_ignores]

                # filenames[:] = [i for i in filenames
                #                 if check_file(_rel_path(dirpath, i))]
                filenames, filepaths = check_files(filenames, dirpath)
                return dirpath, dirnames, filenames, filepaths

        def _walk():
            t0 = time.time()

            # manually produce dragline package files for the first loop
            yield _dragline_dirpath, [], _dragline_filenames, _dragline_filepaths

            # `dirpath` is absolute path iff dragline package files in the first loop
            # other times it is relative path without './' at the beginning
            for dirpath, dirnames, filenames in os.walk(self.root):
                yield react(dirpath, dirnames, filenames)

                if not self.recursive:
                    break
            t1 = time.time()
            self.walk_time_cost = t1 - t0  # unit: second
            print 'walk time cost: %s' % self.walk_time_cost

        self.walk = _walk


def is_dir_family(p1, p2):
    if in_dir(p1, p2) or in_dir(p2, p1):
        return True


def in_dir(pth, dir):
    """
    ('dir0/dir1', 'dir0') True
    ('dir0', 'dir0') True
    ('file.py', '') True
    ('', '') True
    """
    if not dir:
        return True
    if pth == dir:
        return True
    if not pth.startswith(dir):
        return False
    if os.path.dirname(pth[len(dir):]).startswith('/'):
        return True
    else:
        return False


def parse_path(root, path):
    """
    `root`:
        '.'
        'dir0'
        '/tmp/dir1'
    `path`:
        'a.py'
        'dir2/a.py'

    o.path:   parameter `path`
     .abspath
     .rel..
     .filename
     .ext
     .dirpath
    """
    pass


def main():
    try:
        root = sys.argv[1]
    except IndexError:
        root = '.'

    # try:
    import dragconfig as config
    # except ImportError:
    #     config = type('Config', (), {})()

    kwgs = {
        'ignores': [],
        'watches': [],
        'handlers': [],
        'global_handler': None,
        'interval': 300,
        'recursive': True
    }

    for k in kwgs:
        if hasattr(config, k.upper()):
            logging.debug('%s affects' % k.upper())
            kwgs[k] = getattr(config, k.upper())

    drag = Dragline(root, **kwgs)

    drag.start()


if __name__ == '__main__':
    logging.getLogger().setLevel('DEBUG')
    print __file__
    main()
