#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import fnmatch
import logging
import itertools
import inspect

from .handlers import run_command


logging.basicConfig(format='- %(message)s', level=logging.INFO)
#logging.getLogger().setLevel('DEBUG')


_dragline_dirpath = os.path.abspath(os.path.dirname(__file__))
_dragline_filenames = filter(
    lambda x: fnmatch.fnmatch(x, '*.py'),
    os.listdir(_dragline_dirpath))
_dragline_filepaths = [os.path.join(_dragline_dirpath, i) for i in _dragline_filenames]

logging.debug('dragline dirpath: %s' % _dragline_dirpath)
logging.debug('dragline filenames: %s' % _dragline_filenames)
logging.debug('dragline filepaths: %s' % _dragline_filepaths)


# `_dir_ignores` overlooks relative path
# and only matches the name of directory
# so .git/ ignore any directory named '.git',
# if you want's to only ignore some/where/.git/,
# remove '.git/' in `_dir_ignores`
# and add 'some/where/.git/' in dragconfig.IGNORES
_dir_ignores = set(['.git', '.hg', '.svn'])

_ext_ignores = set(['*.pyc', '.pyo', '.swp', '.swo', '.o'])


class EmptyClass(object):
    pass


class PathObject(object):
    def __init__(self, filepath):
        self.dirname, self.filename = os.path.split(filepath)
        self.filepath = filepath

    def __str__(self):
        return '<PathObject dirname=%s, filename=%s, filepath=%s>' % (self.dirname, self.filename, self.filepath)

    def __repr__(self):
        return self.__str__()


class ActionHandler(object):
    def added(self):
        raise NotImplementedError('no added method defined')

    def modified(self):
        raise NotImplementedError('no modified method defined')

    def removed(self):
        raise NotImplementedError('no removed method defined')


class Dragline(object):

    def __init__(self, ignores=[], watches=[], handlers=[], global_handler=None,
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
        # NOTE is it nessessary to check whether path is legal or not ?
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

    def get_record(self):
        record = {}
        for dirpath, dirnames, filenames, filepaths in self.walk():
            logging.debug('self.walk: %s, %s, %s, %s' % (dirpath, dirnames, filenames, filepaths))
            for i in filepaths:
                record[i] = os.stat(i).st_mtime
        return record

    def get_changes(self, record):
        changes = {
            'added': [],
            'modified': [],
            'removed': []
        }
        for filepath, mtime in record.iteritems():
            if filepath in self.last_record:
                if mtime != self.last_record[filepath]:
                    changes['modified'].append(filepath)
            else:
                changes['added'].append(filepath)
        changes['removed'] = [i for i in self.last_record if not i in record]

        return changes, list(itertools.chain(*changes.itervalues()))

    def start(self):
        """
        Start monitoring
        """
        self.last_record = self.get_record()

        while True:
            record = self.get_record()

            changes, changes_list = self.get_changes(record)
            logging.debug('changes: %s; changes_list: %s' % (changes, changes_list))

            if changes_list:
                self.log_info(changes)

                # reload if dragline package changed
                for i in changes_list:
                    if i in _dragline_filepaths:
                        print 'dragline package files changed, reload the process..\n'
                        os.execv(sys.executable, [sys.executable] + sys.argv)
                        sys.exit(0)

                if not self.act is None:
                    logging.debug('Act on changes')
                    self.act(changes)
            else:
                logging.debug('no changes')

            self.last_record = record

            time.sleep(float(self.interval) / 1000)

    def trigger_all(self):
        self.act({'added': self.get_record()})

    def act(self, changes):

        if self.handlers:
            for status, filepaths in changes.iteritems():
                for filepath in filepaths:
                    hdr = self.get_handler(filepath)
                    path = PathObject(filepath)
                    if not hdr:
                        continue
                    if inspect.isclass(hdr):
                        hdr_instance = hdr()
                        getattr(hdr_instance, status)(path)
                    elif inspect.isfunction(hdr):
                        hdr(path)
                    elif isinstance(hdr, (str, unicode)):
                        run_command(hdr)
                    else:
                        raise Exception('Handler type error, %s' % type(hdr))

        if self.global_handler:
            hdr = self.global_handler
            if inspect.isfunction(hdr):
                hdr()
            elif isinstance(hdr, (str, unicode)):
                run_command(hdr)
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

        R = EmptyClass()
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

        def check_file(filepath):
            if not os.path.isfile(filepath):
                # this will ignore symbolic link file
                return False

            for i in R.files:
                if fnmatch.fnmatch(filepath, i):
                    return False

            return True

        def check_files(dirpath, filenames):
            _filenames = []
            _filepaths = []
            for i in filenames:
                filepath = get_relpath(dirpath, i)
                if check_file(filepath):
                    _filenames.append(i)
                    _filepaths.append(filepath)
            return _filenames, _filepaths

        if self.watches:
            raise NotImplementedError('watch mode not implemented')
        else:
            logging.debug('Detected Ignore Mode, constructing walk function')

            analyse(self.ignores)
            R.exts.update(_ext_ignores)
            R.files.update(_ext_ignores)

            def react(dirpath, dirnames, filenames):
                if R.dirs:
                    dirnames[:] = [i for i in dirnames
                                   if (not i in _dir_ignores
                                       and not get_relpath(dirpath, i) in R.dirs)]
                else:
                    dirnames[:] = [i for i in dirnames
                                   if not i in _dir_ignores]

                filenames[:], filepaths = check_files(dirpath, filenames)
                return dirpath, dirnames, filenames, filepaths

        def _walk():
            t0 = time.time()

            # manually produce dragline package files for the first loop
            yield _dragline_dirpath, [], _dragline_filenames, _dragline_filepaths

            # `dirpath` is absolute path iff dragline package files in the first loop
            # other times it is relative path without './' at the beginning
            for dirpath, dirnames, filenames in os.walk('.'):
                logging.debug('os.walk  : %s, %s, %s' % (dirpath, dirnames, filenames))
                yield react(dirpath, dirnames, filenames)

                if not self.recursive:
                    break
            t1 = time.time()
            self.walk_time_cost = t1 - t0  # unit: second
            logging.debug('walk time cost: %s' % self.walk_time_cost)

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


def get_relpath(dirpath, name):
    return os.path.relpath(os.path.join(dirpath, name), '.')


def main():
    try:
        arg1 = sys.argv[1]
    except IndexError:
        arg1 = None

    sys.path.insert(0, os.getcwd())
    import dragconfig as config

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

    drag = Dragline(**kwgs)

    if arg1 == 'trigger_all':
        drag.trigger_all()
    else:
        drag.start()


if __name__ == '__main__':
    print __file__
    main()
