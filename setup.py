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
from distutils.core import setup
from distutils.cmd import Command

import novacut
from novacut.tests.run import run_tests


tree = path.dirname(path.abspath(__file__))
packagedir = path.join(tree, 'novacut')
ui = path.join(tree, 'ui')


class Test(Command):
    description = 'run unit tests and doc tests'

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        if not run_tests():
            sys.exit(2)


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

