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
Some base test classes used by many tests.
"""

import os
from os import path
import shutil
import tempfile
from unittest import TestCase


# FIXME: This will be improved by using dmedia to hold sample videos
home = path.abspath(os.environ['HOME'])
testdir = path.join(home, '.novacut-test-files')
sample_id = 'NPY3IW5SQJUNSP2KV47GVB24G7SWX6XF'
sample_name = sample_id + '.mov'
sample_file = path.join(testdir, sample_name)
sample_url = 'http://uds-o.novacut.com/' + sample_name


class TempDir(object):
    def __init__(self, prefix='unit-tests.'):
        self.dir = tempfile.mkdtemp(prefix=prefix)

    def join(self, *parts):
        return path.join(self.dir, *parts)

    def rmtree(self):
        if self.dir is not None:
            check_call(['/bin/chmod', '-R', '+w', self.dir])
            shutil.rmtree(self.dir)
            self.dir = None

    def makedirs(self, *parts):
        d = self.join(*parts)
        if not path.exists(d):
            os.makedirs(d)
        return d

    def touch(self, *parts):
        d = self.makedirs(*parts[:-1])
        f = self.join(*parts)
        assert not path.exists(f)
        open(f, 'wb').close()
        assert path.isfile(f) and not path.islink(f)
        return f

    def write(self, content, *parts):
        d = self.makedirs(*parts[:-1])
        f = self.join(*parts)
        assert not path.exists(f)
        open(f, 'wb').write(content)
        assert path.isfile(f) and not path.islink(f)
        return f

    def copy(self, src, *parts):
        self.makedirs(*parts[:-1])
        dst = self.join(*parts)
        assert not path.exists(dst)
        shutil.copy2(src, dst)
        assert path.isfile(dst) and not path.islink(dst)
        return dst

    def __del__(self):
        self.rmtree()


class LiveTestCase(TestCase):
    """
    Base class for tests that need the sample video files available locally.

    If the needed files are not available, the tests are skipped.
    """

    sample_file = sample_file

    def setUp(self):
        if not path.isfile(self.sample_file):
            self.skipTest('missing {!r}'.format(self.sample_file))
