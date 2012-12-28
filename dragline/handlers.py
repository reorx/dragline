#!/usr/bin/env python
# -*- coding: utf-8 -*-

import termcolor
import subprocess as sp
import shlex
import os
import re
import codecs


def run_command_str(cmd_str, *args, **kwargs):
    cmd = shlex.split(cmd_str)

    p = sp.Popen(cmd, *args, **kwargs)

    return p


_print_tab = '      '


def add_tab(s):
    s = _print_tab + s
    return s.replace('\n', '\n' + _print_tab)


class DependenceUnexist(Exception):
    pass


def check_python_dep(dep, clsname):
    try:
        __import__(dep)
    except ImportError:
        raise DependenceUnexist(
            'Python module %s dependence is not satisfied on class %s' % (dep, clsname))


def check_node_dep(dep, clsname):
    jscode = 'require("%s")' % dep
    rv = sp.call(['node', '-e', jscode], stdout=sp.PIPE, stderr=sp.PIPE)
    if rv != 0:
        raise DependenceUnexist(
            'NodeJS module %s dependence is not satisfied on class %s' % (dep, clsname))


class _DependentMeta(type):
    def __new__(cls, name, bases, attrs):
        """
        Check dependences, currently support python and node(nodejs)
        """
        if 'DEPENDENCES' in attrs:
            for env, packages in attrs['DEPENDENCES'].iteritems():
                if 'python' == env:
                    check = check_python_dep
                elif 'node' == env:
                    check = check_node_dep
                for i in packages:
                    check(i, name)
        return type.__new__(cls, name, bases, attrs)


class DependentClass(object):
    __metaclass__ = _DependentMeta


class ActionHandler(DependentClass):
    def __init__(self, dragline, dirpath, filename, filepath):
        self.dragline = dragline
        self.dirpath = dirpath
        self.filename = filename
        self.filepath = filepath

        self.initialize()

    def initialize(self):
        pass

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

    def log(self, status, message, exc_info=None):
        if status:
            prefix = termcolor.colored('[%s] ' % 'OK ', 'green')
        else:
            prefix = termcolor.colored('[%s] ' % 'Err', 'red')
        print prefix + message


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
        print prefix + cmd_str

        if self.show_stdout and self.stdoutdata:
            print termcolor.colored(add_tab('Stdout:'), 'green', attrs=['bold'])
            print add_tab(self.stdoutdata)
        if self.show_stderr and self.stderrdata:
            print termcolor.colored(add_tab('Stderr:'), 'red', attrs=['bold'])
            print add_tab(self.stderrdata)


class CompileHandler(ActionHandler):
    _compiler = None

    def initialize(self):
        cls = self.__class__
        cls._compiler = {
            'compiler': cls.get_compiler()
        }

    def read_file(self, path):
        f = codecs.open(path, 'r', 'utf8')
        content = f.read()
        f.close()
        return content

    def write_file(self, path, content):
        #print repr(content)
        f = codecs.open(path, 'w', 'utf8')
        f.write(content)
        f.close()

    def get_compiler(self):
        raise NotImplementedError

    @property
    def compiler(self):
        return self.__class__._compiler['compiler']


class StylusHandler(CompileHandler):
    DEPENDENCES = {
        'python': ['stylus'],
        'node': ['nib', 'canvas', 'stylus']
    }

    plugins = []
    compress = True
    paths = []

    @classmethod
    def get_compiler(cls):
        from stylus import Stylus
        compiler = Stylus(compress=cls.compress,
                          paths=cls.paths)
        for i in cls.plugins:
            compiler.use(i)
        return compiler

    def stylus(self, source, output):
        self.mkdir(output)

        self.write_file(output,
                        self.compiler.compile(self.read_file(source)))
        self.log(True, 'Stylus compiled: %s -> %s' % (source, output))


class JadeHandler(CompileHandler):
    DEPENDENCES = {
        'python': ['pyjade'],
        'node': ['jade']
    }

    template = 'django'

    _support_templates = ['django', 'jinja', 'mako', 'tornado']

    @classmethod
    def get_compiler(cls):
        from pyjade.utils import process
        if not cls.template in cls._support_templates:
            raise Exception('Template should be one of %s' % cls._support_templates)
        try:
            template_compiler = __import__('pyjade.ext.' + cls.template).Compiler
        except Exception, e:
            raise Exception('Import template compiler failed: %s' % e)

        def _compiler(s):
            return process(s, compiler=template_compiler)
        return _compiler

    def jade(self, source, output):
        self.mkdir(output)

        self.write_file(output,
                        self.compiler(self.read_file(source)))
        self.log(True, 'Jade compiled: %s -> %s' % (source, output))
