#!/usr/bin/env python3

# novacut: the collaborative video editor
# Copyright (C) 2011 Novacut Inc
#
# This file is part of `novacut`.
#
# `novacut` is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# `novacut` is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for
# more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with `novacut`.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#   Jason Gerard DeRose <jderose@novacut.com>

"""
Install `novacut`.
"""

import sys
if sys.version_info < (3, 4):
    sys.exit('Novacut requires Python 3.4 or newer')

import os
from os import path
import subprocess
from distutils.core import setup
from distutils.cmd import Command

import novacut
from novacut.tests.run import run_tests


TREE = path.dirname(path.abspath(__file__))


def run_under_same_interpreter(opname, script, args):
    print('\n** running: {}...'.format(script), file=sys.stderr)
    if not os.access(script, os.R_OK | os.X_OK):
        print('ERROR: cannot read and execute: {!r}'.format(script),
            file=sys.stderr
        )
        print('Consider running `setup.py test --skip-{}`'.format(opname),
            file=sys.stderr
        )
        sys.exit(3)
    cmd = [sys.executable, script] + args
    print('check_call:', cmd, file=sys.stderr)
    subprocess.check_call(cmd)
    print('** PASSED: {}\n'.format(script), file=sys.stderr)


def run_pyflakes3():
    script = '/usr/bin/pyflakes3'
    names = [
        'novacut',
        'setup.py',
        'novacut-gtk',
        'novacut-cli',
        'novacut-v0-v1-upgrade',
        'novacut-reset',
        'novacut-video-checker',
        'novacut-service',
        'novacut-thumbnailer',
        'novacut-renderer',
    ]
    args = [path.join(TREE, name) for name in names]
    run_under_same_interpreter('flakes', script, args)


class Test(Command):
    description = 'run unit tests and doc tests'

    user_options = [
        ('skip-flakes', None, 'do not run pyflakes static checks'),
        ('skip-gtk', None, 'Skip GTK related tests'),
    ]

    def initialize_options(self):
        self.skip_flakes = 0
        self.skip_gtk = 0

    def finalize_options(self):
        pass

    def run(self):
        if not run_tests(self.skip_gtk):
            sys.exit(2)
        if not self.skip_flakes:
            run_pyflakes3()


setup(
    name='novacut',
    description='the collaborative video editor',
    url='https://launchpad.net/novacut',
    version=novacut.__version__,
    author='Jason Gerard DeRose',
    author_email='jderose@novacut.com',
    license='AGPLv3+',
    packages=[
        'novacut',
        'novacut.tests',
    ],
    scripts=[
        'novacut-gtk',
        'novacut-cli',
        'novacut-v0-v1-upgrade',
        'novacut-reset',
        'novacut-video-checker',
    ],
    data_files=[
        ('share/couchdb/apps/novacut',
            [path.join('ui', name) for name in os.listdir('ui')]
        ),
        ('share/applications',
            ['data/novacut.desktop']
        ),
        ('share/icons/hicolor/48x48/apps',
            ['data/novacut.svg']
        ),
        ('lib/novacut',
            ['novacut-service', 'novacut-thumbnailer', 'novacut-renderer'],
        ),
        ('share/dbus-1/services/',
            ['data/com.novacut.Renderer.service']
        ),
        ('share/novacut',
            ['blender-vse-import.py'],
        ),
    ],
    cmdclass={'test': Test},
)

