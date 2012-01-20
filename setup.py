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

import os
from os import path
import stat
from distutils.core import setup
from distutils.cmd import Command
from unittest import TestLoader, TextTestRunner
from doctest import DocTestSuite
import sys

if sys.version_info.major != 3:
    print(sys.argv)
    sys.exit(1)

import novacut


tree = path.dirname(path.abspath(__file__))
packagedir = path.join(tree, 'novacut')
ui = path.join(tree, 'ui')


def pynames_iter(pkdir, pkname=None):
    """
    Recursively yield dotted names for *.py files in directory *pydir*.
    """
    if not path.isfile(path.join(pkdir, '__init__.py')):
        return
    if pkname is None:
        pkname = path.basename(pkdir)
    yield pkname
    dirs = []
    for name in sorted(os.listdir(pkdir)):
        if name == '__init__.py':
            continue
        if name.startswith('.') or name.endswith('~'):
            continue
        fullname = path.join(pkdir, name)
        st = os.lstat(fullname)
        if stat.S_ISREG(st.st_mode) and name.endswith('.py'):
            parts = name.split('.')
            if len(parts) == 2:
                yield '.'.join([pkname, parts[0]])
        elif stat.S_ISDIR(st.st_mode):
            dirs.append((fullname, name))
    for (fullname, name) in dirs:
        for n in pynames_iter(fullname, '.'.join([pkname, name])):
            yield n


class Test(Command):
    description = 'run unit tests and doc tests'

    user_options = [
        ('no-doctest', None, 'do not run doc-tests'),
        ('no-unittest', None, 'do not run unit-tests'),
        ('names=', None, 'comma-sperated list of modules to test'),
    ]

    def _pynames_iter(self):
        for pyname in pynames_iter(packagedir):
            if not self.names:
                yield pyname
            else:
                for name in self.names:
                    if name in pyname:
                        yield pyname
                        break

    def run(self):
        pynames = list(self._pynames_iter())
        pynames.remove('novacut.dbus')
        for name in pynames:
            print(name)
        #raise SystemExit()

        # Add unit-tests:
        if self.no_unittest:
            suite = TestSuite()
        else:
            loader = TestLoader()
            suite = loader.loadTestsFromNames(pynames)

        # Add doc-tests:
        if not self.no_doctest:
            for mod in pynames:
                suite.addTest(DocTestSuite(mod))

        # Run the tests:
        runner = TextTestRunner(verbosity=2)
        result = runner.run(suite)
        if not result.wasSuccessful():
            raise SystemExit(1)

    def initialize_options(self):
        self.no_doctest = 0
        self.no_unittest = 0
        self.names = ''

    def finalize_options(self):
        self.names = self.names.split(',')


setup(
    name='novacut',
    description='the collaborative video editor',
    url='https://launchpad.net/novacut',
    version=novacut.__version__,
    author='Jason Gerard DeRose',
    author_email='jderose@novacut.com',
    license='AGPLv3+',
    packages=['novacut'],
    scripts=['novacut-gtk', 'novacut-cli'],
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
            ['novacut-service'],
        ),
        ('share/dbus-1/services/',
            ['data/com.novacut.Renderer.service']
        ),
    ],
    cmdclass={'test': Test},
)
