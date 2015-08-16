# novacut: the collaborative video editor
# Copyright (C) 2015 Novacut Inc
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
from usercouch.misc import CouchTestCase
from microfiber import Database, NotFound

from .. import misc
from .. import renderer2 as renderer


TYPE_ERROR = '{}: need a {!r}; got a {!r}: {!r}'
from collections import namedtuple


random = SystemRandom()


class TestFunctions(TestCase):
    def test_get(self):
        _get = renderer._get
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
        _int = renderer._int
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

    def test_get_framerate_from_struct(self):
        class MockStructure:
            def __init__(self, ret):
                self._ret = ret

            def get_fraction(self, key):
                assert not hasattr(self, '_key')
                self._key = key
                return self._ret

        s = MockStructure((True, 24000, 1001))
        f = renderer.get_framerate_from_struct(s)
        self.assertIsInstance(f, Fraction)
        self.assertEqual(f, Fraction(24000, 1001))
        self.assertEqual(s._key, 'framerate')

        s = MockStructure((False, 24000, 1001))
        with self.assertRaises(Exception) as cm:
            renderer.get_framerate_from_struct(s)
        self.assertEqual(str(cm.exception),
            "could not get 'framerate' from video caps structure"
        )
        self.assertEqual(s._key, 'framerate')


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
    (num, denom, framerate) = random_framerate()
    s = renderer.Slice(
        random_id(),
        file_id,
        start,
        stop,
        Dmedia._path(file_id),
        framerate,
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
    fdoc = {
        '_id': file_id,
        'framerate': {
            'num': num,
            'denom': denom,
        }
    }
    return (s, doc, fdoc)


def random_sequence():
    s = renderer.Sequence(random_id(),
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


class TestSliceIter(CouchTestCase):
    def get_db(self, create=False):
        db = Database('foo-{}-1'.format(random_id().lower()), self.env)
        if create is True:
            self.assertEqual(db.ensure(), True)
        return db

    def test_init(self):
        Dmedia = MockDmedia()
        db = self.get_db()
        root_id = random_id()
        inst = renderer.SliceIter(Dmedia, db, root_id)
        self.assertIs(inst.Dmedia, Dmedia)
        self.assertIs(inst.db, db)
        self.assertIs(inst.root_id, root_id)

        # SliceIter.__init__() shouldn't try to create the database, etc:
        self.assertIs(db.ensure(), True)

    def test_get(self):
        Dmedia = MockDmedia()
        db = self.get_db(create=True)
        inst = renderer.SliceIter(Dmedia, db, random_id())

        # video/sequence with empty src:
        _id = random_id()
        with self.assertRaises(NotFound):
            inst.get(_id)
        doc = {
            '_id': _id,
            'node': {
                'type': 'video/sequence',
                'src': [],
            }
        }
        db.save(doc)
        s = inst.get(_id)
        self.assertIsInstance(s, renderer.Sequence)
        self.assertEqual(s.id, _id)
        self.assertIsInstance(s.src, tuple)
        self.assertEqual(s.src, tuple())

        # video/sequence with populated src:
        src = tuple(random_id() for i in range(29))
        doc['node']['src'] = list(src)
        db.save(doc)
        s = inst.get(_id)
        self.assertIsInstance(s, renderer.Sequence)
        self.assertEqual(s.id, _id)
        self.assertIsInstance(s.src, tuple)
        self.assertEqual(s.src, src)

        # video/slice when dmedia/file doc is missing:
        _id = random_id()
        with self.assertRaises(NotFound):
            inst.get(_id)
        file_id = random_id(30)
        (start, stop) = misc.random_slice(5000)
        doc = {
            '_id': _id,
            'node': {
                'type': 'video/slice',
                'src': file_id,
                'start': start,
                'stop': stop,
            }
        }
        db.save(doc)
        with self.assertRaises(NotFound):  # dmedia/file doc is still misssing
            inst.get(_id)
        num = random.randrange(1, 9000)
        denom = random.randrange(1, 9000)

        # video/slice when dmedia/file doc is missing:
        fdoc = {
            '_id': file_id,
            'framerate': {
                'num': num,
                'denom': denom,
            }
        }
        db.save(fdoc)
        s = inst.get(_id)
        self.assertIsInstance(s, renderer.Slice)
        self.assertEqual(s.id, _id)
        self.assertEqual(s.src, file_id)
        self.assertEqual(s.start, start)
        self.assertEqual(s.stop, stop)
        self.assertEqual(s.filename, Dmedia._path(file_id))
        self.assertIsInstance(s.framerate, Fraction)
        self.assertEqual(s.framerate, Fraction(num, denom))

    def test_get_many(self):
        Dmedia = MockDmedia()
        db = self.get_db(create=True)
        inst = renderer.SliceIter(Dmedia, db, random_id())

        (s1, doc1, fdoc1) = random_slice(Dmedia)
        (s2, doc2, fdoc2) = random_slice(Dmedia)
        (s3, doc3) = random_sequence()
        (s4, doc4) = random_sequence()

        tups = [s1, s2, s3, s4]
        random.shuffle(tups)
        tups = tuple(tups)
        ids = tuple(s.id for s in tups)

        # No docs saved:
        with self.assertRaises(ValueError) as cm:
            inst.get_many(ids)
        self.assertEqual(str(cm.exception), 'Not Found: {!r}'.format(ids[0]))

        # All docs saved:
        db.save_many([doc1, fdoc1, doc2, fdoc2, doc3, doc4])
        self.assertEqual(inst.get_many(ids), tups)

    def test_framerate(self):
        Dmedia = MockDmedia()
        db = self.get_db(create=True)
        inst = renderer.SliceIter(Dmedia, db, random_id())

        # dmedia/file doc is missing:
        _id = random_id(30)
        with self.assertRaises(NotFound):
            inst.get_framerate(_id)

        # doc['framerate'] is missing:
        doc = {'_id': _id}
        db.save(doc)
        with self.assertRaises(TypeError) as cm:
            inst.get_framerate(_id)
        self.assertEqual(str(cm.exception),
            TYPE_ERROR.format('framerate', dict, type(None), None)
        )

        # doc['framerate'] isn't a dict:
        marker = random_id()
        doc['framerate'] = marker
        db.save(doc)
        with self.assertRaises(TypeError) as cm:
            inst.get_framerate(_id)
        self.assertEqual(str(cm.exception),
            TYPE_ERROR.format('framerate', dict, str, marker)
        )

        # doc['framerate']['num'] and doc['framerate']['denom'] are missing:
        doc['framerate'] = {}
        db.save(doc)
        with self.assertRaises(TypeError) as cm:
            inst.get_framerate(_id)
        self.assertEqual(str(cm.exception),
            TYPE_ERROR.format('num', int, type(None), None)
        )

        # doc['framerate']['denom'] is missing:
        doc['framerate']['num'] = 1
        db.save(doc)
        with self.assertRaises(TypeError) as cm:
            inst.get_framerate(_id)
        self.assertEqual(str(cm.exception),
            TYPE_ERROR.format('denom', int, type(None), None)
        )

        # doc['framerate']['denom'] is < 1:
        doc['framerate']['denom'] = 0
        db.save(doc)
        with self.assertRaises(ValueError) as cm:
            inst.get_framerate(_id)
        self.assertEqual(str(cm.exception), "need 'denom' >= 1; got 0")

        # doc['framerate']['num'] is < 1:
        doc['framerate']['denom'] = 34
        doc['framerate']['num'] = 0
        db.save(doc)
        with self.assertRaises(ValueError) as cm:
            inst.get_framerate(_id)
        self.assertEqual(str(cm.exception), "need 'num' >= 1; got 0")

        # All good:
        doc['framerate']['num'] = 32
        db.save(doc)
        f = inst.get_framerate(_id)
        self.assertIsInstance(f, Fraction)
        self.assertEqual(f, Fraction(16, 17))

        # Also all good:
        doc['framerate']['num'] = 1
        doc['framerate']['denom'] = 1
        db.save(doc)
        f = inst.get_framerate(_id)
        self.assertIsInstance(f, Fraction)
        self.assertEqual(f, Fraction(1, 1))



