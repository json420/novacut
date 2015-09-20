# novacut: the collaborative video editor
# Copyright (C) 2011-2015 Novacut Inc
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
Run the `novacut` unit tests.
"""

import sys
import os
from os import path
import stat
from unittest import TestLoader, TextTestRunner
from doctest import DocTestSuite


packagedir = path.dirname(path.dirname(path.abspath(__file__)))


def pynames_iter(pkdir=packagedir, pkname=None):
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
        if name in ('__init__.py', '__pycache__'):
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
        subpkg = '.'.join([pkname, name])
        yield from pynames_iter(fullname, subpkg)


def run_tests(skip_gtk=False):
    pynames = list(pynames_iter())
    if skip_gtk:
        pynames.remove('novacut.play')
        pynames.remove('novacut.tests.test_play')
    pynames = tuple(pynames)
    for name in pynames:
        print(name)
    return True

    # Add unit-tests:
    loader = TestLoader()
    suite = loader.loadTestsFromNames(pynames)

    # Add doc-tests:
    for name in pynames:
        suite.addTest(DocTestSuite(name))

    # Run the tests:
    runner = TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print(
        'Ran `novacut` tests from package at {!r}'.format(packagedir),
        file=sys.stderr
    )
    print('-' * 70, file=sys.stderr)
    return result.wasSuccessful()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--skip-gtk', action='store_true', default=False,
        help='Skip GTK related tests',
    )
    args = parser.parse_args()
    if not run_tests(args.skip_gtk):
        raise SystemExit(2)

