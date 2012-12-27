#!/usr/bin/env python
# -*- coding: utf-8 -*-

import termcolor
import subprocess as sp
import shlex
import os
import re


def run_command_str(cmd_str, *args, **kwargs):
    cmd = shlex.split(cmd_str)

    p = sp.Popen(cmd, *args, **kwargs)

    return p


_print_tab = '      '


def add_tab(s):
    s = _print_tab + s
    return s.replace('\n', '\n' + _print_tab)


class ActionHandler(object):
    def __init__(self, dragline, dirpath, filename, filepath):
        self.dragline = dragline
        self.dirpath = dirpath
        self.filename = filename
        self.filepath = filepath

    def added(self):
        raise NotImplementedError('no added method defined')

    def modified(self):
        raise NotImplementedError('no modified method defined')

    def removed(self):
        raise NotImplementedError('no removed method defined')

    def mkdir(self, anypath):
        if not anypath:
            return
        if os.path.isdir(anypath):
            dirpath = anypath
        else:
            dirpath = os.path.dirname(anypath)
        if dirpath and not os.path.exists(dirpath):
            os.makedirs(dirpath)

    def lreplace(self, s, ori, sub):
        return re.sub('^%s' % ori, sub, s)

    def rreplace(self, s, ori, sub):
        return re.sub('%s$' % ori, sub, s)


class CommandHandler(ActionHandler):
    show_stdout = False

    show_stderr = False

    def run_command(self, cmd, *args, **kwargs):
        """
        use subprocess.Popen to run command, but not asynchronous because it will wait for result
        """
        self.cmd = cmd
        if self.dragline.debug:
            print 'Command:', self.cmd
            return

        if not 'stdout' in kwargs:
            kwargs['stdout'] = sp.PIPE
        if not 'stderr' in kwargs:
            kwargs['stderr'] = sp.PIPE
        self.p = sp.Popen(cmd, *args, **kwargs)

        self.stdoutdata, self.stderrdata = self.p.communicate()

        self._log_command()

    def _log_command(self):
        if not hasattr(self, 'stdoutdata') or not hasattr(self, 'stderrdata'):
            raise Exception('No attributes stdoutdata or stderrdata, check whether you have assigned them')

        if self.p.returncode == 0:
            prefix = termcolor.colored('[%s] ' % 'OK ', 'green')
        else:
            prefix = termcolor.colored('[%s] ' % 'Err', 'red')
        if isinstance(self.cmd, list):
            cmd_str = ' '.join(self.cmd)
        else:
            cmd_str = self.cmd
        log = prefix + cmd_str
        print log

        if self.show_stdout and self.stdoutdata:
            print termcolor.colored(add_tab('Stdout:'), 'green', attrs=['bold'])
            print add_tab(self.stdoutdata)
        if self.show_stderr and self.stderrdata:
            print termcolor.colored(add_tab('Stderr:'), 'red', attrs=['bold'])
            print add_tab(self.stderrdata)


class JadeHandler(CommandHandler):
    def jade(self, source, output):
        self.mkdir(output)

        cmd = 'jade < %s > %s' % (source, output)
        self.run_command(cmd, shell=True)


class StylusHandler(CommandHandler):
    def jade(self, source, output):
        self.mkdir(output)

        cmd = 'stylus < %s > %s' % (source, output)
        self.run_command(cmd, shell=True)
