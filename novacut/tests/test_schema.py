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
Unit tests for the `novacut.schema` module.
"""

from unittest import TestCase
import time
from copy import deepcopy
from random import SystemRandom

from dbase32 import random_id

from novacut.misc import random_slice
from novacut import schema
from .base import random_file_id


class TestFunctions(TestCase):
    def test_normalized_dumps(self):
        self.skipTest('FIXME')

    def test_hash_node(self):
        self.skipTest('FIXME')

    def test_check_novacut(self):
        good = {
            '_id': random_id(),
            'type': 'novacut/whatever',
            'time': time.time(),
        }
        schema.check_novacut(good)
        also_good = deepcopy(good)
        also_good['_id'] = random_file_id()

        # Test with missing keys
        keys = sorted(good)
        for key in keys:
            bad = deepcopy(good)
            del bad[key]
            with self.assertRaises(ValueError) as cm:
                schema.check_novacut(bad)
            self.assertEqual(
                str(cm.exception),
                'doc[{!r}] does not exist'.format(key)
            )

        # Test with bad _id value
        bad = deepcopy(good)
        bad['_id'] = 'foobar'
        with self.assertRaises(ValueError) as cm:
            schema.check_novacut(bad)
        self.assertEqual(
            str(cm.exception),
            "doc['_id']: length of ID (6) not multiple of 8: 'foobar'"
        )

        # Test with bad time value
        bad = deepcopy(good)
        bad['time'] = -1
        with self.assertRaises(ValueError) as cm:
            schema.check_novacut(bad)
        self.assertEqual(
            str(cm.exception),
            "doc['time'] must be >= 0; got -1"
        )

        # Test with bad type value
        bad = deepcopy(good)
        bad['type'] = 'dmedia/file'
        with self.assertRaises(ValueError) as cm:
            schema.check_novacut(bad)
        self.assertEqual(
            str(cm.exception),
            "doc['type']: 'dmedia/file' does not match 'novacut/[a-z]+$'"
        )

    def test_check_node(self):
        good = {
            '_id': random_id(),
            'time': time.time(),
            'type': 'novacut/node',
            'node': {
                'type': 'shaker',
                'src': random_id(),
            },
        }
        schema.check_node(good)

        # Test with missing keys
        keys = sorted(good)
        for key in keys:
            bad = deepcopy(good)
            del bad[key]
            with self.assertRaises(ValueError) as cm:
                schema.check_node(bad)
            self.assertEqual(
                str(cm.exception),
                'doc[{!r}] does not exist'.format(key)
            )

        # Test with missing keys in doc['node']
        keys = sorted(good['node'])
        for key in keys:
            bad = deepcopy(good)
            del bad['node'][key]
            with self.assertRaises(ValueError) as cm:
                schema.check_node(bad)
            self.assertEqual(
                str(cm.exception),
                "doc['node'][{!r}] does not exist".format(key)
            )

    def test_create_node(self):
        marker = random_id()
        node = {'type': 'foo', 'src': marker}
        doc = schema.create_node(node)
        schema.check_novacut(doc)
        schema.check_node(doc)
        self.assertEqual(doc['type'], 'novacut/node')
        self.assertEqual(doc['node'],
            {'type': 'foo', 'src': marker}
        )
 
    def test_check_relative_audio(self):
        id1 = random_id()
        id2 = random_id()
        good = {
            'audio': [
                {'id': id1, 'offset': 17},
                {'id': id2, 'offset': -300},
            ],
        }
        schema.check_relative_audio(good)
        schema.check_relative_audio({'audio': []})

        # Test when audio is missing
        with self.assertRaises(ValueError) as cm:
            schema.check_relative_audio({})
        self.assertEqual(str(cm.exception), "doc['audio'] does not exist")

        # Test with bad audio type
        with self.assertRaises(TypeError) as cm:
            schema.check_relative_audio({'audio': tuple()})
        self.assertEqual(
            str(cm.exception),
            "doc['audio']: need a <class 'list'>; got a <class 'tuple'>: ()"
        )

        bad = deepcopy(good)
        bad['audio'][1] = 17
        with self.assertRaises(TypeError) as cm:
            schema.check_relative_audio(bad)
        self.assertEqual(
            str(cm.exception),
            "doc['audio'][1]: need a <class 'dict'>; got a <class 'int'>: 17"
        )

        bad = deepcopy(good)
        bad_id = random_id(5)
        bad['audio'][0]['id'] = bad_id
        with self.assertRaises(ValueError) as cm:
            schema.check_relative_audio(bad)
        self.assertEqual(
            str(cm.exception),
            "doc['audio'][0]['id']: random ID must be 24 characters, got 8: {!r}".format(bad_id)
        )

        bad = deepcopy(good)
        bad['audio'][1]['offset'] = 18.0
        with self.assertRaises(TypeError) as cm:
            schema.check_relative_audio(bad)
        self.assertEqual(
            str(cm.exception),
            "doc['audio'][1]['offset']: need a <class 'int'>; got a <class 'float'>: 18.0"
        )

        bad = deepcopy(good)
        del bad['audio'][1]['id']
        with self.assertRaises(ValueError) as cm:
            schema.check_relative_audio(bad)
        self.assertEqual(
            str(cm.exception),
            "doc['audio'][1]['id'] does not exist"
        )

        bad = deepcopy(good)
        del bad['audio'][0]['offset']
        with self.assertRaises(ValueError) as cm:
            schema.check_relative_audio(bad)
        self.assertEqual(
            str(cm.exception),
            "doc['audio'][0]['offset'] does not exist"
        )

    def test_check_video_sequence(self):
        good = {
            '_id': random_id(),
            'time': time.time(),
            'type': 'novacut/node',
            'audio': [],
            'node': {
                'type': 'video/sequence',
                'src': [
                    random_id(),
                    random_id(),
                    random_id(),
                ],
            },
        }
        schema.check_video_sequence(good)

        # Test with missing keys
        keys = sorted(good)
        for key in keys:
            bad = deepcopy(good)
            del bad[key]
            with self.assertRaises(ValueError) as cm:
                schema.check_video_sequence(bad)
            self.assertEqual(
                str(cm.exception),
                'doc[{!r}] does not exist'.format(key)
            )

        # Test with missing keys in doc['node']
        keys = sorted(good['node'])
        for key in keys:
            bad = deepcopy(good)
            del bad['node'][key]
            with self.assertRaises(ValueError) as cm:
                schema.check_video_sequence(bad)
            self.assertEqual(
                str(cm.exception),
                "doc['node'][{!r}] does not exist".format(key)
            )

        # Test with bad doc['node']['type'] value:
        bad = deepcopy(good)
        bad['node']['type'] = 'video/foo'
        with self.assertRaises(ValueError) as cm:
            schema.check_video_sequence(bad)
        self.assertEqual(
            str(cm.exception),
            "doc['node']['type'] must equal 'video/sequence'; got 'video/foo'"
        )

        # Test with bad doc['node']['src'] type:
        bad = deepcopy(good)
        bad_id = random_id()
        bad['node']['src'] = bad_id
        with self.assertRaises(TypeError) as cm:
            schema.check_video_sequence(bad)
        self.assertEqual(
            str(cm.exception),
            "doc['node']['src']: need a {!r}; got a {!r}: {!r}".format(
                list, str, bad_id
            )
        )

        # Test with bad doc['node']['src'] value:
        bad = deepcopy(good)
        bad_id = random_id(5)
        bad['node']['src'][1] = bad_id
        with self.assertRaises(ValueError) as cm:
            schema.check_video_sequence(bad)
        self.assertEqual(
            str(cm.exception),
            "doc['node']['src'][1]: random ID must be 24 characters, got 8: {!r}".format(
                bad_id
            )
        )

    def test_create_video_sequence(self):
        id1 = random_id()
        id2 = random_id()
        doc = schema.create_video_sequence([id1, id2])
        schema.check_novacut(doc)
        schema.check_node(doc)
        schema.check_video_sequence(doc)
        self.assertEqual(doc['node']['type'], 'video/sequence')
        self.assertEqual(doc['node']['src'], [id1, id2])

    def test_check_slice(self):
        good = {
            '_id': random_id(),
            'time': time.time(),
            'type': 'novacut/node',
            'node': {
                'type': 'video/slice',
                'src': random_file_id(),
                'start': 1776,
                'stop': 2013,
            },
        }
        schema.check_slice(good)
        also_good = deepcopy(good)
        also_good['node']['type'] = 'audio/slice'
        schema.check_slice(also_good)

        # Test with missing keys
        keys = sorted(good)
        for key in keys:
            bad = deepcopy(good)
            del bad[key]
            with self.assertRaises(ValueError) as cm:
                schema.check_slice(bad)
            self.assertEqual(
                str(cm.exception),
                'doc[{!r}] does not exist'.format(key)
            )

        # Test with missing keys in doc['node']
        keys = sorted(good['node'])
        for key in keys:
            bad = deepcopy(good)
            del bad['node'][key]
            with self.assertRaises(ValueError) as cm:
                schema.check_slice(bad)
            self.assertEqual(
                str(cm.exception),
                "doc['node'][{!r}] does not exist".format(key)
            )

        # Test with bad doc['node']['type'] value:
        bad = deepcopy(good)
        bad['node']['type'] = 'foo/bar'
        with self.assertRaises(ValueError) as cm:
            schema.check_slice(bad)
        self.assertEqual(
            str(cm.exception),
            "doc['node']['type'] value 'foo/bar' not in ('video/slice', 'audio/slice')"
        )

        # Test with bad start type
        bad = deepcopy(good)
        bad['node']['start'] = 1776.0
        with self.assertRaises(TypeError) as cm:
            schema.check_slice(bad)
        self.assertEqual(
            str(cm.exception),
            "doc['node']['start']: need a <class 'int'>; got a <class 'float'>: 1776.0"
        )

        # Test with bad stop type
        bad = deepcopy(good)
        bad['node']['stop'] = 2013.0
        with self.assertRaises(TypeError) as cm:
            schema.check_slice(bad)
        self.assertEqual(
            str(cm.exception),
            "doc['node']['stop']: need a <class 'int'>; got a <class 'float'>: 2013.0"
        )

        # Test with bad start value
        bad = deepcopy(good)
        bad['node']['start'] = -1
        with self.assertRaises(ValueError) as cm:
            schema.check_slice(bad)
        self.assertEqual(
            str(cm.exception),
            "doc['node']['start'] must be >= 0; got -1"
        )

        # Test with bad stop value
        bad = deepcopy(good)
        bad['node']['stop'] = 0
        with self.assertRaises(ValueError) as cm:
            schema.check_slice(bad)
        self.assertEqual(
            str(cm.exception),
            "doc['node']['stop'] must be >= 1; got 0"
        )

        # Test with a zero-length slice
        bad = deepcopy(good)
        bad['node']['stop'] = 1776
        with self.assertRaises(ValueError) as cm:
            schema.check_slice(bad)
        self.assertEqual(
            str(cm.exception),
            "doc['node']['stop'] must be >= 1777; got 1776"
        )

    def test_check_video_slice(self):
        good = {
            '_id': random_id(),
            'time': time.time(),
            'type': 'novacut/node',
            'audio': [],
            'node': {
                'type': 'video/slice',
                'src': random_file_id(),
                'start': 1776,
                'stop': 2013,
            },
        }
        schema.check_video_slice(good)

        # Test with missing keys
        keys = sorted(good)
        for key in keys:
            bad = deepcopy(good)
            del bad[key]
            with self.assertRaises(ValueError) as cm:
                schema.check_video_slice(bad)
            self.assertEqual(
                str(cm.exception),
                'doc[{!r}] does not exist'.format(key)
            )

        # Test with missing keys in doc['node']
        keys = sorted(good['node'])
        for key in keys:
            bad = deepcopy(good)
            del bad['node'][key]
            with self.assertRaises(ValueError) as cm:
                schema.check_video_slice(bad)
            self.assertEqual(
                str(cm.exception),
                "doc['node'][{!r}] does not exist".format(key)
            )

        # Test with bad doc['node']['type'] value:
        bad = deepcopy(good)
        bad['node']['type'] = 'audio/slice'
        with self.assertRaises(ValueError) as cm:
            schema.check_video_slice(bad)
        self.assertEqual(
            str(cm.exception),
            "doc['node']['type'] must equal 'video/slice'; got 'audio/slice'"
        )

    def test_create_video_slice(self):
        src_id = random_file_id()
        frames = 24 * 60
        (start, stop) = random_slice(frames)
        doc = schema.create_video_slice(src_id, start, stop)
        schema.check_video_slice(doc)
        self.assertEqual(doc['node']['type'], 'video/slice')
        self.assertEqual(doc['node']['src'], src_id)
        self.assertEqual(doc['node']['start'], start)
        self.assertEqual(doc['node']['stop'], stop)

    def test_check_audio_slice(self):
        good = {
            '_id': random_id(),
            'time': time.time(),
            'type': 'novacut/node',
            'node': {
                'type': 'audio/slice',
                'src': random_file_id(),
                'start': 1776,
                'stop': 2013,
            },
        }
        schema.check_audio_slice(good)

        # Test with missing keys
        keys = sorted(good)
        for key in keys:
            bad = deepcopy(good)
            del bad[key]
            with self.assertRaises(ValueError) as cm:
                schema.check_audio_slice(bad)
            self.assertEqual(
                str(cm.exception),
                'doc[{!r}] does not exist'.format(key)
            )

        # Test with missing keys in doc['node']
        keys = sorted(good['node'])
        for key in keys:
            bad = deepcopy(good)
            del bad['node'][key]
            with self.assertRaises(ValueError) as cm:
                schema.check_audio_slice(bad)
            self.assertEqual(
                str(cm.exception),
                "doc['node'][{!r}] does not exist".format(key)
            )

        # Test with bad doc['node']['type'] value:
        bad = deepcopy(good)
        bad['node']['type'] = 'video/slice'
        with self.assertRaises(ValueError) as cm:
            schema.check_audio_slice(bad)
        self.assertEqual(
            str(cm.exception),
            "doc['node']['type'] must equal 'audio/slice'; got 'video/slice'"
        )

    def test_create_audio_slice(self):
        src_id = random_file_id()
        samples = 48000 * 60
        (start, stop) = random_slice(samples)
        doc = schema.create_audio_slice(src_id, start, stop)
        schema.check_audio_slice(doc)
        self.assertEqual(doc['node']['type'], 'audio/slice')
        self.assertEqual(doc['node']['src'], src_id)
        self.assertEqual(doc['node']['start'], start)
        self.assertEqual(doc['node']['stop'], stop)

    def test_project_db_name(self):
        self.assertEqual(
            schema.project_db_name('AAAAAAAAAAAAAAAAAAAAAAAA'),
            'novacut-1-aaaaaaaaaaaaaaaaaaaaaaaa',
        )
        _id = random_id()
        self.assertEqual(
            schema.project_db_name(_id),
            'novacut-1-{}'.format(_id.lower())
        )

    def test_get_project_id(self):
        self.assertEqual(
            schema.get_project_id('novacut-1-aaaaaaaaaaaaaaaaaaaaaaaa'),
            'AAAAAAAAAAAAAAAAAAAAAAAA'
        )
        self.assertIsNone(schema.get_project_id('novacut-1'))
        self.assertIsNone(schema.get_project_id('dmedia-1'))
        self.assertIsNone(
            schema.get_project_id('dmedia-1-aaaaaaaaaaaaaaaaaaaaaaaa')
        )
        # Make sure we can round-trip with project_db_name():
        for i in range(1000):
            _id = random_id()
            db_name = schema.project_db_name(_id)
            self.assertEqual(schema.get_project_id(db_name), _id)

    def test_check_project(self):
        self.skipTest('FIXME')

    def test_create_project(self):
        doc = schema.create_project()
        schema.check_project(doc)
        self.assertEqual(doc['title'], '')

        doc = schema.create_project(title='Hobo Spaceship')
        schema.check_project(doc)
        self.assertEqual(doc['title'], 'Hobo Spaceship')

    def test_create_slice(self):
        src = random_id()
        doc = schema.create_slice(src, {'frame': 17}, {'frame': 1869})
        schema.check_node(doc)
        self.assertEqual(doc['node'],
            {
                'type': 'slice',
                'src': src,
                'start': {'frame': 17},
                'stop': {'frame': 1869},
                'stream': 'video',
            }
        )

        src = random_id() 
        doc = schema.create_slice(src, {'sample': 48000}, {'sample': 96000},
            'audio'
        )
        schema.check_node(doc)
        self.assertEqual(doc['node'],
            {
                'type': 'slice',
                'src': src,
                'start': {'sample': 48000},
                'stop': {'sample': 96000},
                'stream': 'audio',
            }
        )

    def test_create_sequence(self):
        one = random_id()
        two = random_id()
        doc = schema.create_sequence([one, two])
        schema.check_node(doc)
        self.assertEqual(doc['node'],
            {
                'type': 'sequence',
                'src': [one, two],
            }
        )

    def test_intrinsic_node(self):
        node = {
            'src': 'VQIXPULW3G77W4XLGROMEDGFAH2XJBN4SAVFUGOZRFSIVU7N',
            'type': 'slice',
            'stream': 'video',
            'start': {
                'frame': 200,
            },
            'stop': {
                'frame': 245,
            },
        }
        data = schema.normalized_dumps(node)
        t = schema.intrinsic_node(node)
        self.assertIsInstance(t, schema.Intrinsic)
        self.assertEqual(t.id, schema.hash_node(data))
        self.assertEqual(t.data, data)
        self.assertIs(t.node, node)
        self.assertEqual(schema.normalized_dumps(t.node), data)

    def test_intrinsic_src(self):
        return  # FIXME: need to change this a bit to make it easier to test
        _id = random_id(30)
        self.assertEqual(
            schema.intrinsic_src(_id, None, None),
            _id
        )

        _id = random_id(30)
        src = {'id': _id, 'foo': 'bar'}
        self.assertEqual(
            schema.intrinsic_src(src, None, None),
            {'id': _id, 'foo': 'bar'}
        )

    def test_iter_src(self):
        src = random_id()
        self.assertEqual(
            list(schema.iter_src(src)),
            [src]
        )

        src = [random_id() for i in range(10)]
        self.assertEqual(
            list(schema.iter_src(src)),
            src
        )

        ids = [random_id() for i in range(10)]
        src = [{'id': _id} for _id in ids]
        self.assertEqual(
            list(schema.iter_src(src)),
            ids
        )


        src = {
            'foo': random_id(),
            'bar': random_id(),
            'baz': random_id(),
        }
        self.assertEqual(
            set(schema.iter_src(src)),
            set(v for v in src.values())
        )
        
        ids = [random_id() for i in range(3)]
        src = {
            'foo': {'id': ids[0]},
            'bar': {'id': ids[1]},
            'baz': {'id': ids[2]},
        }
        self.assertEqual(
            set(schema.iter_src(src)),
            set(ids)
        )
