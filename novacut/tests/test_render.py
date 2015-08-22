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
Unit tests for the `novacut.renderer` module.
"""

from unittest import TestCase
from os import path
from fractions import Fraction
from random import SystemRandom

from dbase32 import random_id

from .. import misc
from .. import render


TYPE_ERROR = '{}: need a {!r}; got a {!r}: {!r}'


random = SystemRandom()


class TestFunctions(TestCase):
    def test_get(self):
        _get = render._get
        values = (
            random_id(),
            17,
            16.9,
            {'hello': 'world'},
            ['hello', 'world'],
        )
        for val in values:
            key = random_id()
            d = {key: val}
            badkey = random_id()
            with self.assertRaises(TypeError) as cm:
                _get(d, badkey, type(val))
            self.assertEqual(str(cm.exception),
                TYPE_ERROR.format(badkey, type(val), type(None), None)
            )
            self.assertIs(_get(d, key, type(val)), val)

    def test_int(self):
        _int = render._int
        key = random_id()
        badkey = random_id()
        for val in (-17, -1, 0, 1, 17):
            d = {key: val}
            with self.assertRaises(TypeError) as cm:
                _int(d, badkey)
            self.assertEqual(str(cm.exception),
                TYPE_ERROR.format(badkey, int, type(None), None)
            )
            with self.assertRaises(ValueError) as cm:
                _int(d, key, val + 1)
            self.assertEqual(str(cm.exception),
                'need {!r} >= {}; got {}'.format(key, val + 1, val)
            )
            for minval in (None, val, val - 1):
                self.assertIs(_int(d, key, minval), val)


class MockDmedia:
    def __init__(self, parentdir=None):
        if parentdir is None:
            parentdir = path.join('/', 'media', random_id())
        assert path.abspath(parentdir) == parentdir
        self.filesdir = path.join(parentdir, '.dmedia', 'files')

    def _path(self, _id):
        return path.join(self.filesdir, _id[:2], _id[2:])

    def Resolve(self, _id):
        return (_id, 0, self._path(_id))


def random_framerate():
    num = random.randrange(1, 54321)
    denom = random.randrange(1, 54321)
    return (num, denom, Fraction(num, denom))


def random_slice(Dmedia):
    (start, stop) = misc.random_slice(123456)
    file_id = random_id(30)
    s = render.Slice(
        random_id(),
        file_id,
        start,
        stop,
        Dmedia._path(file_id),
    )
    doc = {
        '_id': s.id,
        'node': {
            'type': 'video/slice',
            'src': file_id,
            'start': start,
            'stop': stop,
        }
    }
    return (s, doc)


def random_sequence():
    s = render.Sequence(random_id(),
        tuple(random_id() for i in range(random.randrange(20)))
    )
    doc = {
        '_id': s.id,
        'node': {
            'type': 'video/sequence',
            'src': list(s.src),
        }
    }
    return (s, doc)

