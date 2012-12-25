#!/usr/bin/env python
# -*- coding: utf-8 -*-

import termcolor
import subprocess as sp
import shlex
import os
import re


def run_command(cmd, *args, **kwargs):
    #cmd_list = shlex.split(cmd_str)

    p = sp.Popen(cmd, *args, **kwargs)

    return p


_print_tab = '      '


def add_tab(s):
    s = _print_tab + s
    return s.replace('\n', '\n' + _print_tab)


class Handler(object):
    show_stdout = False

    show_stderr = False

    def run_command(self, cmd, *args, **kwargs):
        self.cmd = cmd
        if not 'stdout' in kwargs:
            kwargs['stdout'] = sp.PIPE
        if not 'stderr' in kwargs:
            kwargs['stderr'] = sp.PIPE
        self.p = sp.Popen(cmd, *args, **kwargs)

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

    def log_command(self):
        stdoutdata, stderrdata = self.p.communicate()

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

        if self.show_stdout and stdoutdata:
            print termcolor.colored(add_tab('Stdout:'), 'green', attrs=['bold'])
            print add_tab(stdoutdata)
        if self.show_stderr and stderrdata:
            print termcolor.colored(add_tab('Stderr:'), 'red', attrs=['bold'])
            print add_tab(stderrdata)


class JadeHandler(Handler):
    def jade(self, source, output):
        self.mkdir(output)

        cmd = 'jade < %s > %s' % (source, output)
        #self.p = sp.Popen(self.cmd, shell=True)
        self.run_command(cmd, shell=True)

        self.log_command()


class StylusHandler(Handler):
    show_stdout = False

    show_stderr = False

    def jade(self, source, output):
        self.mkdir(output)

        cmd = 'stylus < %s > %s' % (source, output)
        #self.p = sp.Popen(self.cmd, shell=True)
        self.run_command(cmd, shell=True)

        self.log_command()
