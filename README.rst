
Dragline: File system automation guard
======================================


Usage:

1. Install dragline::

    python setup install

   or just try without touching your dist-packages::

    python setup develop

2. Write a ``dragconfig.py`` file in the director you want to watch::


    #!/usr/bin/env python
    # -*- coding: utf-8 -*-

    from dragline.handlers import CommandHandler, StylusHandler, JadeHandler


    class MyStylusHandler(StylusHandler):
        paths = ['stylus']
        plugins = ['nib']

        def added(self):
            self.make()

        def modified(self):
            self.make()

        def make(self):
            output = self.rreplace(self.lreplace(self.filepath, 'stylus', 'public/stylesheets'),
                                   '.styl', '.css')
            self.stylus(self.filepath, output)


    class MyJadeHandler(JadeHandler):
        template = 'tornado'

        def added(self):
            self.make()

        def modified(self):
            self.make()

        def make(self):
            output = self.rreplace(self.lreplace(self.filepath, 'jade', 'public/html'),
                                   '.jade', '.html')
            self.jade(self.filepath, output)


    class MyJsHandler(CommandHandler):
        def added(self):
            self.make()

        def modified(self):
            self.make()

        def make(self):
            output = self.lreplace(self.filepath, 'javascripts', 'public/javascripts')
            self.mkdir(output)
            self.run_command(['cp', self.filepath, output])


    DEBUG = False

    HANDLERS = [
        ('*.styl', MyStylusHandler),
        ('*.jade', MyJadeHandler),
        ('*.js', MyJsHandler),
    ]


    INTERVAL = 2000

    RECURSIVE = True

3. Run ``dragline``

4. You are done, continue focusing on your work
