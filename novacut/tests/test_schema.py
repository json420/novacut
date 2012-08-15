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

from microfiber import random_id
from filestore import DIGEST_BYTES

from novacut import schema


random = SystemRandom()


class TestFunctions(TestCase):
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

    def test_project_db_name(self):
        self.assertEqual(
            schema.project_db_name('AAAAAAAAAAAAAAAAAAAAAAAA'),
            'novacut-0-aaaaaaaaaaaaaaaaaaaaaaaa',
        )
        _id = random_id()
        self.assertEqual(
            schema.project_db_name(_id),
            'novacut-0-{}'.format(_id.lower())
        )

    def test_create_project(self):
        doc = schema.create_project()
        schema.check_project(doc)
        self.assertEqual(doc['title'], '')

        doc = schema.create_project(title='Hobo Spaceship')
        schema.check_project(doc)
        self.assertEqual(doc['title'], 'Hobo Spaceship')

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
 
    def test_check_slice(self):
        good = {
            '_id': random_id(),
            'time': time.time(),
            'type': 'novacut/node',
            'node': {
                'type': 'slice/video',
                'src': random_id(DIGEST_BYTES),
                'start': 1776,
                'stop': 2013,
            },
        }
        schema.check_slice(good)

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
            "doc['node']['type'] value 'foo/bar' not in ('slice/video', 'slice/audio')"
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
            'node': {
                'type': 'slice/video',
                'src': random_id(DIGEST_BYTES),
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
        bad['node']['type'] = 'slice/audio'
        with self.assertRaises(ValueError) as cm:
            schema.check_video_slice(bad)
        self.assertEqual(
            str(cm.exception),
            "doc['node']['type'] must equal 'slice/video'; got 'slice/audio'"
        )

    def test_create_video_slice(self):
        src_id = random_id(DIGEST_BYTES)
        frames = 24 * 60
        start = random.randrange(0, frames)
        stop = random.randrange(start + 1, frames + 1)
        doc = schema.create_video_slice(src_id, start, stop)
        schema.check_video_slice(doc)
        self.assertEqual(doc['node']['type'], 'slice/video')
        self.assertEqual(doc['node']['src'], src_id)
        self.assertEqual(doc['node']['start'], start)
        self.assertEqual(doc['node']['stop'], stop)

    def test_check_audio_slice(self):
        good = {
            '_id': random_id(),
            'time': time.time(),
            'type': 'novacut/node',
            'node': {
                'type': 'slice/audio',
                'src': random_id(DIGEST_BYTES),
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
        bad['node']['type'] = 'slice/video'
        with self.assertRaises(ValueError) as cm:
            schema.check_audio_slice(bad)
        self.assertEqual(
            str(cm.exception),
            "doc['node']['type'] must equal 'slice/audio'; got 'slice/video'"
        )

    def test_create_audio_slice(self):
        src_id = random_id(DIGEST_BYTES)
        samples = 48000 * 60
        start = random.randrange(0, samples)
        stop = random.randrange(start + 1, samples + 1)
        doc = schema.create_audio_slice(src_id, start, stop)
        schema.check_audio_slice(doc)
        self.assertEqual(doc['node']['type'], 'slice/audio')
        self.assertEqual(doc['node']['src'], src_id)
        self.assertEqual(doc['node']['start'], start)
        self.assertEqual(doc['node']['stop'], stop)

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
