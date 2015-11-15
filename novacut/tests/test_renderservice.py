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
Unit tests for the `novacut.renderservice` module.
"""

from unittest import TestCase
from os import path

from dbase32 import random_id
from usercouch.misc import CouchTestCase
from microfiber import Database, NotFound

from ..misc import random_slice as random_start_stop
from ..renderservice import Slice
from .. import renderservice


TYPE_ERROR = '{}: need a {!r}; got a {!r}: {!r}'


class MockDmedia:
    def __init__(self, status=None, parentdir=None):
        self._status = ({} if status is None else status)
        if parentdir is None:
            parentdir = path.join('/', 'media', random_id())
        assert path.abspath(parentdir) == parentdir
        self._filesdir = path.join(parentdir, '.dmedia', 'files')
        self._calls = []

    def _path(self, _id):
        return path.join(self._filesdir, _id[:2], _id[2:])

    def Resolve(self, _id):
        self._calls.append(_id)
        status = self._status.get(_id, 0)
        return (_id, status, self._path(_id))


class TestConstants(TestCase):
    def test_MAX_DEPTH(self):
        self.assertIsInstance(renderservice.MAX_DEPTH, int)
        self.assertEqual(renderservice.MAX_DEPTH, 10)


class TestFunctions(TestCase):
    def test_get(self):
        _get = renderservice._get
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

    def test_get_str(self):
        _get_str = renderservice._get_str

        # Good value:
        key = random_id()
        val = random_id()
        d = {key: val}
        result = _get_str(d, key)
        self.assertIs(result, val)

        # Value is empty str:
        with self.assertRaises(ValueError) as cm:
            _get_str({key: ''}, key)
        self.assertEqual(str(cm.exception), 'str {!r} is empty'.format(key))

        # d[key] isn't a str:
        with self.assertRaises(TypeError) as cm:
            _get_str({key: 17}, key)
        self.assertEqual(str(cm.exception),
            TYPE_ERROR.format(key, str, int, 17)
        )

        # d[key] is missing:
        with self.assertRaises(TypeError) as cm:
            _get_str({random_id(): val}, key)
        self.assertEqual(str(cm.exception),
            TYPE_ERROR.format(key, str, type(None), None)
        )

    def test_get_int(self):
        _get_int = renderservice._get_int
        key = random_id()
        badkey = random_id()
        for val in (-17, -1, 0, 1, 17):
            d = {key: val}
            with self.assertRaises(ValueError) as cm:
                _get_int(d, key, val + 1)
            self.assertEqual(str(cm.exception),
                'need {!r} >= {}; got {}'.format(key, val + 1, val)
            )
            for minval in (val, val - 1):
                with self.assertRaises(TypeError) as cm:
                    _get_int(d, badkey, minval)
                self.assertEqual(str(cm.exception),
                    TYPE_ERROR.format(badkey, int, type(None), None)
                )
                self.assertIs(_get_int(d, key, minval), val)

    def test_get_slice(self):
        _get_slice = renderservice._get_slice

        # All good:
        src = random_id(30)
        (start, stop) = random_start_stop(5000)
        node = {
            'src': src,
            'start': start,
            'stop': stop,
        }
        self.assertEqual(_get_slice(node), (src, start, stop))

        # Missing keys:
        items = tuple(node.items())
        for (key, val) in items:
            badnode = node.copy()
            del badnode[key]
            with self.assertRaises(TypeError) as cm:
                _get_slice(badnode)
            self.assertEqual(str(cm.exception),
                TYPE_ERROR.format(key, type(val), type(None), None)
            )

        # node['src'] is not a str:
        badnode = {
            'src': 17,
            'start': start,
            'stop': stop,
        }
        with self.assertRaises(TypeError) as cm:
            _get_slice(badnode)
        self.assertEqual(str(cm.exception),
            TYPE_ERROR.format('src', str, int, 17)
        )

        # node['src'] is empty:
        badnode = {
            'src': '',
            'start': start,
            'stop': stop,
        }
        with self.assertRaises(ValueError) as cm:
            _get_slice(badnode)
        self.assertEqual(str(cm.exception), "str 'src' is empty")

        # node['start'] is not an int:
        badnode = {
            'src': src,
            'start': float(start),
            'stop': stop,
        }
        with self.assertRaises(TypeError) as cm:
            _get_slice(badnode)
        self.assertEqual(str(cm.exception),
            TYPE_ERROR.format('start', int, float, float(start))
        )

        # node['start'] > node['stop']:
        badnode = {
            'src': src,
            'start': stop + 1,
            'stop': stop,
        }
        with self.assertRaises(ValueError) as cm:
            _get_slice(badnode)
        self.assertEqual(str(cm.exception),
            'need start <= stop; got {} > {}'.format(stop + 1, stop)
        )

    def test_get_sequence(self):
        _get_sequence = renderservice._get_sequence

        # Empty sequence is allowed, although ignored:
        src = []
        node = {'src': src}
        result = _get_sequence(node)
        self.assertIs(result, src)
        self.assertEqual(result, [])

        # Populated sequence:
        ids = tuple(random_id() for i in range(17))
        src = list(ids)
        node = {'src': src}
        result = _get_sequence(node)
        self.assertIs(result, src)
        self.assertEqual(result, list(ids))

        # node['src'] isn't a list:
        badnode = {'src': ids}
        with self.assertRaises(TypeError) as cm:
            _get_sequence(badnode)
        self.assertEqual(str(cm.exception),
            TYPE_ERROR.format('src', list, tuple, ids)
        )

        # node['src'] is missing:
        with self.assertRaises(TypeError) as cm:
            _get_sequence(badnode)
        self.assertEqual(str(cm.exception),
            TYPE_ERROR.format('src', list, tuple, ids)
        )

    def test_iter_raw_slices(self):
        _iter_raw_slices = renderservice._iter_raw_slices
        MAX_DEPTH = renderservice.MAX_DEPTH

        _id = random_id()
        src = random_id(30)
        (start, stop) = random_start_stop(5000)
        doc = {
            'node': {
                'type': 'video/slice',
                'src': src,
                'start': start,
                'stop': stop,
            }
        }
        db = {_id: doc}
        with self.assertRaises(ValueError) as cm:
            list(_iter_raw_slices(db, _id, MAX_DEPTH + 1))
        self.assertEqual(str(cm.exception),
            'MAX_DEPTH exceeded: {} > {}'.format(MAX_DEPTH + 1, MAX_DEPTH)
        )
        for depth in range(MAX_DEPTH + 1):
            self.assertEqual(
                list(_iter_raw_slices(db, _id, depth)),
                [(_id, src, start, stop)]
            )

    def test_resolve_files(self):
        resolve_files = renderservice.resolve_files
        Dmedia = MockDmedia()

        # Empty files list:
        self.assertEqual(resolve_files(Dmedia, []), {})
        self.assertEqual(Dmedia._calls, [])

        # Populated files list:
        files = tuple(random_id(30) for i in range(37))
        self.assertEqual(resolve_files(Dmedia, files),
            dict((_id, Dmedia._path(_id)) for _id in files)
        )
        self.assertEqual(Dmedia._calls, list(files))

        # File not available in local Dmedia FileStore:
        Dmedia = MockDmedia(status={files[17]: 1})
        with self.assertRaises(ValueError) as cm:
            resolve_files(Dmedia, files)
        self.assertEqual(str(cm.exception),
            'File {} not available in local Dmedia stores'.format(files[17])
        )
        self.assertEqual(Dmedia._calls, list(files[0:18]))

        # File not in Dmedia library:
        Dmedia = MockDmedia(status={files[29]: 2})
        with self.assertRaises(ValueError) as cm:
            resolve_files(Dmedia, files)
        self.assertEqual(str(cm.exception),
            'File {} not in Dmedia library'.format(files[29])
        )
        self.assertEqual(Dmedia._calls, list(files[0:30]))       


def random_slice(Dmedia, src):
    (start, stop) = random_start_stop(123456)
    s = Slice(
        random_id(),
        src,
        start,
        stop,
        Dmedia._path(src),
    )
    doc = {
        '_id': s.id,
        'node': {
            'type': 'video/slice',
            'src': src,
            'start': start,
            'stop': stop,
        }
    }
    return (s, doc)


class TestCouchFunctions(CouchTestCase):
    def get_db(self, create=False):
        db = Database('foo-{}-1'.format(random_id().lower()), self.env)
        if create is True:
            self.assertEqual(db.ensure(), True)
        return db

    def test_get_raw_slices(self):
        get_raw_slices = renderservice.get_raw_slices

        raw_slices = []
        for i in range(100):
            (start, stop) = random_start_stop(9123)
            raw_slices.append(
                (random_id(), random_id(30), start, stop)
            )
        raw_slices = tuple(raw_slices)

        docs = []
        for (_id, src, start, stop) in raw_slices:
            docs.append({
                '_id': _id,
                'node': {
                    'type': 'video/slice',
                    'src': src,
                    'start': start,
                    'stop': stop,
                }
            })
        root_id = random_id()
        docs.append({
            '_id': root_id,
            'node': {
                'type': 'video/sequence',
                'src': list(r[0] for r in raw_slices),
            }
        })

        db = self.get_db(create=True)
        with self.assertRaises(NotFound):
            get_raw_slices(db, root_id)
        db.save_many(docs)
        del docs
        self.assertEqual(get_raw_slices(db, root_id), raw_slices)

        # Nested sequences:
        seq1 = {
            '_id': random_id(),
            'node': {
                'type': 'video/sequence',
                'src': list(r[0] for r in raw_slices[0:25]),
            }
        }
        seq2 = {
            '_id': random_id(),
            'node': {
                'type': 'video/sequence',
                'src': list(r[0] for r in raw_slices[50:100]),
            }
        }
        src = [seq1['_id']]
        src.extend(r[0] for r in raw_slices[25:50])
        src.append(seq2['_id'])
        root = {
            '_id': random_id(),
            'node': {
                'type': 'video/sequence',
                'src': src,
            },
        }
        db.save_many([seq1, seq2, root])
        self.assertEqual(get_raw_slices(db, seq1['_id']), raw_slices[0:25])
        self.assertEqual(get_raw_slices(db, seq2['_id']), raw_slices[50:100])
        self.assertEqual(get_raw_slices(db, root['_id']), raw_slices)

    def test_get_slices(self):
        get_slices = renderservice.get_slices
        Dmedia = MockDmedia()
        db = self.get_db(create=True)

        # Build random edit graph:
        files = tuple(random_id(30) for i in range(42))
        nested = tuple(random_id() for i in range(3))
        slices = []
        docs = []
        for seq_id in nested:
            seq_src = []
            for file_id in files:
                (s, d) = random_slice(Dmedia, file_id)
                slices.append(s)
                docs.append(d)
                seq_src.append(s.id)
            docs.append({
                '_id': seq_id,
                'node': {
                    'type': 'video/sequence',
                    'src': seq_src,
                }
            })
        root_id = random_id()
        docs.append({
            '_id': root_id,
            'node': {
                'type': 'video/sequence',
                'src': list(nested),
            }
        })
        slices = tuple(slices)
        self.assertEqual(len(slices), 126)  # 42 * 3
        self.assertEqual(len(docs), 130)  # (42 * 3) + 4

        # Save graph to CouchDB, test get_slices():
        db.save_many(docs)
        result = get_slices(Dmedia, db, root_id)
        self.assertEqual(result, slices)
        for item in result:
            self.assertIsInstance(item, Slice)
        self.assertEqual(Dmedia._calls, sorted(files))

