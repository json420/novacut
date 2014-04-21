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

from microfiber import random_id
from filestore import DIGEST_BYTES


def resolve(_id):
    """
    A dummy Dmedia-like resolver.
    
    For example:
    
    >>> resolve('VQIXPULW3G77W4XLGROMEDGFAH2XJBN4SAVFUGOZRFSIVU7N')
    'file:///home/.dmedia/files/VQ/IXPULW3G77W4XLGROMEDGFAH2XJBN4SAVFUGOZRFSIVU7N'

    """
    return 'file://' + path.join('/home', '.dmedia', 'files', _id[:2], _id[2:])


sample1 = 'VQIXPULW3G77W4XLGROMEDGFAH2XJBN4SAVFUGOZRFSIVU7N'
sample2 = 'W62OZLFQUSKE4K6SLJWJ4EHFDUTRLD7JKQXUQMDJSSUG6TAQ'



def random_file_id():
    return random_id(DIGEST_BYTES)



class TempDir(object):
    def __init__(self, prefix='unit-tests.'):
        self.dir = tempfile.mkdtemp(prefix=prefix)
        
    def __del__(self):
        self.rmtree()
        
    def rmtree(self):
        if self.dir is not None:
            shutil.rmtree(self.dir)
            self.dir = None

    def join(self, *parts):
        return path.join(self.dir, *parts)

    def makedirs(self, *parts):
        d = self.join(*parts)
        if not path.exists(d):
            os.makedirs(d)
        return d

    def touch(self, *parts):
        self.makedirs(*parts[:-1])
        f = self.join(*parts)
        assert not path.exists(f)
        open(f, 'wb').close()
        assert path.isfile(f) and not path.islink(f)
        return f

    def write(self, content, *parts):
        self.makedirs(*parts[:-1])
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


class TempHome(TempDir):
    def __init__(self):
        super().__init__()
        self.orig = os.environ['HOME']
        os.environ['HOME'] = self.dir

    def __del__(self):
        os.environ['HOME'] = self.orig
        super().__del__()
