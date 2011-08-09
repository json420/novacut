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
Unit tests for the `novacut.renderer` module.
"""

from unittest import TestCase

import gst

from novacut.schema import random_id
from novacut import renderer

from .base import LiveTestCase, TempDir



clip1 = random_id()
clip2 = random_id()
slice1 = random_id()
slice2 = random_id()
slice3 = random_id()
sequence1 = random_id()
sequence2 = random_id()
docs = [
    {
        '_id': clip1,
        'type': 'dmedia/file',
        'framerate': {'num': 24, 'denom': 1},
        'samplerate': 48000,
    },

    {
        '_id': clip2,
        'type': 'dmedia/file',
        'framerate': {'num': 24, 'denom': 1},
        'samplerate': 48000,
    },

    {
        '_id': slice1,
        'type': 'novacut/node',
        'node': {
            'src': clip1,
            'type': 'slice',
            'stream': 'video',
            'start': {'frame': 8 * 24},
            'stop': {'frame': 12 * 24},
        },
    },

    {
        '_id': slice2,
        'type': 'novacut/node',
        'node': {
            'src': clip2,
            'type': 'slice',
            'stream': 'video',
            'start': {'frame': 32 * 24},
            'stop': {'frame': 35 * 24},
        },
    },

    {
        '_id': slice3,
        'type': 'novacut/node',
        'node': {
            'src': clip1,
            'type': 'slice',
            'stream': 'video',
            'start': {'frame': 40},
            'stop': {'frame': 88},
        },
    },

    {
        '_id': sequence1,
        'type': 'novacut/node',
        'node': {
            'type': 'sequence',
            'src': [
                slice1,
                slice2,
            ],
        },
    },

    {
        '_id': sequence1,
        'type': 'novacut/node',
        'node': {
            'type': 'sequence',
            'src': [
                slice1,
                slice2,
            ],
        },
    },

    {
        '_id': sequence2,
        'type': 'novacut/node',
        'node': {
            'type': 'sequence',
            'src': [
                slice3,
                sequence1,
            ],
        },
    },
]


class DummyBuilder(renderer.Builder):
    def __init__(self, docs):
        self._docmap = dict(
            (doc['_id'], doc) for doc in docs
        )

    def get_doc(self, _id):
        return self._docmap[_id]

    def resolve_file(self, _id):
        return '/path/to/' + _id


class TestFunctions(TestCase):
    def test_caps_string(self):
        f = renderer.caps_string
        self.assertEqual(
            f('audio/x-raw-float', {}),
            'audio/x-raw-float'
        )
        self.assertEqual(
            f('audio/x-raw-float', {'rate': 44100}),
            'audio/x-raw-float, rate=44100'
        )
        self.assertEqual(
            f('audio/x-raw-float', {'rate': 44100, 'channels': 1}),
            'audio/x-raw-float, channels=1, rate=44100'
        )

    def test_build_slice(self):
        b = DummyBuilder(docs)

        doc = {
            'node': {
                'src': clip1,
                'type': 'slice',
                'stream': 'video',
                'start': {'frame': 8 * 24},
                'stop': {'frame': 12 * 24},
            },
        }
        el = renderer.build_slice(doc, b)
        self.assertIsInstance(el, gst.Element)
        self.assertEqual(el.get_factory().get_name(), 'gnlfilesource')
        self.assertEqual(el.get_property('media-start'), 8 * gst.SECOND)
        self.assertEqual(el.get_property('media-duration'), 4 * gst.SECOND)
        self.assertEqual(el.get_property('duration'), 4 * gst.SECOND)
        self.assertEqual(el.get_property('caps').to_string(), 'video/x-raw-rgb')
        self.assertEqual(el.get_property('location'), '/path/to/' + clip1)

        # Now with audio stream:
        doc['node']['stream'] = 'audio'
        el = renderer.build_slice(doc, b)
        self.assertIsInstance(el, gst.Element)
        self.assertEqual(el.get_factory().get_name(), 'gnlfilesource')
        self.assertEqual(el.get_property('media-start'), 8 * gst.SECOND)
        self.assertEqual(el.get_property('media-duration'), 4 * gst.SECOND)
        self.assertEqual(el.get_property('duration'), 4 * gst.SECOND)
        self.assertEqual(
            el.get_property('caps').to_string(),
            'audio/x-raw-int; audio/x-raw-float'
        )
        self.assertEqual(el.get_property('location'), '/path/to/' + clip1)

        # When specified by sample instead:
        doc = {
            'node': {
                'src': clip1,
                'type': 'slice',
                'stream': 'video',
                'start': {'sample': 8 * 48000},
                'stop': {'sample': 12 * 48000},
            },
        }
        el = renderer.build_slice(doc, b)
        self.assertIsInstance(el, gst.Element)
        self.assertEqual(el.get_factory().get_name(), 'gnlfilesource')
        self.assertEqual(el.get_property('media-start'), 8 * gst.SECOND)
        self.assertEqual(el.get_property('media-duration'), 4 * gst.SECOND)
        self.assertEqual(el.get_property('duration'), 4 * gst.SECOND)
        self.assertEqual(
            el.get_property('caps').to_string(),
            'video/x-raw-rgb'
        )
        self.assertEqual(el.get_property('location'), '/path/to/' + clip1)

    def test_build_sequence(self):
        b = DummyBuilder(docs)

        el = renderer.build_sequence(b.get_doc(sequence1), b)
        self.assertIsInstance(el, gst.Element)
        self.assertEqual(el.get_factory().get_name(), 'gnlcomposition')
        self.assertEqual(el.get_property('duration'), 7 * gst.SECOND)

        el = b.build(sequence1)
        self.assertIsInstance(el, gst.Element)
        self.assertEqual(el.get_factory().get_name(), 'gnlcomposition')
        self.assertEqual(el.get_property('duration'), 7 * gst.SECOND)

        el = b.build(sequence2)
        self.assertIsInstance(el, gst.Element)
        self.assertEqual(el.get_factory().get_name(), 'gnlcomposition')
        self.assertEqual(el.get_property('duration'), 9 * gst.SECOND)


class TestEncodeBin(TestCase):
    klass = renderer.EncoderBin

    def test_init(self):
        # with props
        d = {
            'enc': 'vorbisenc',
            'props': {
                'quality': 0.5,
            },
        }
        inst = self.klass(d)
        self.assertTrue(inst._d is d)

        self.assertTrue(inst._q1.get_parent() is inst)
        self.assertTrue(isinstance(inst._q1, gst.Element))
        self.assertEqual(inst._q1.get_factory().get_name(), 'queue')

        self.assertTrue(inst._enc.get_parent() is inst)
        self.assertTrue(isinstance(inst._enc, gst.Element))
        self.assertEqual(inst._enc.get_factory().get_name(), 'vorbisenc')
        self.assertEqual(inst._enc.get_property('quality'), 0.5)

        self.assertTrue(inst._q2.get_parent() is inst)
        self.assertTrue(isinstance(inst._q2, gst.Element))
        self.assertEqual(inst._q2.get_factory().get_name(), 'queue')

        self.assertIsNone(inst._caps)

        # default properties
        d = {'enc': 'vorbisenc'}
        inst = self.klass(d)
        self.assertTrue(inst._d is d)

        self.assertTrue(inst._q1.get_parent() is inst)
        self.assertTrue(isinstance(inst._q1, gst.Element))
        self.assertEqual(inst._q1.get_factory().get_name(), 'queue')

        self.assertTrue(inst._enc.get_parent() is inst)
        self.assertTrue(isinstance(inst._enc, gst.Element))
        self.assertEqual(inst._enc.get_factory().get_name(), 'vorbisenc')
        self.assertNotEqual(inst._enc.get_property('quality'), 0.5)

        self.assertTrue(inst._q2.get_parent() is inst)
        self.assertTrue(isinstance(inst._q2, gst.Element))
        self.assertEqual(inst._q2.get_factory().get_name(), 'queue')

        self.assertIsNone(inst._caps)

        # with mime and caps
        d = {
            'enc': 'vorbisenc',
            'mime': 'audio/x-raw-float',
            'caps': {'rate': 44100, 'channels': 1},
        }
        inst = self.klass(d)
        self.assertTrue(inst._d is d)
        self.assertIsInstance(inst._caps, gst.Caps)
        self.assertEqual(
            inst._caps.to_string(),
            'audio/x-raw-float, channels=(int)1, rate=(int)44100'
        )

        # Test with caps but no mime:
        d = {
            'enc': 'vorbisenc',
            'caps': {'rate': 44100, 'channels': 1},
        }
        inst = self.klass(d)
        self.assertIsNone(inst._caps)

        # Test with mime but no caps:
        d = {
            'enc': 'vorbisenc',
            'mime': 'audio/x-raw-float',
        }
        inst = self.klass(d)
        self.assertIsNone(inst._caps)

    def test_repr(self):
        d = {
            'enc': 'vorbisenc',
            'props': {
                'quality': 0.5,
            },
        }

        inst = self.klass(d)
        self.assertEqual(
            repr(inst),
            'EncoderBin(%r)' % (d,)
        )

        class FooBar(self.klass):
            pass
        inst = FooBar(d)
        self.assertEqual(
            repr(inst),
            'FooBar(%r)' % (d,)
        )

    def test_make(self):
        d = {'enc': 'vorbisenc'}
        inst = self.klass(d)

        enc = inst._make('theoraenc')
        self.assertTrue(enc.get_parent() is inst)
        self.assertTrue(isinstance(enc, gst.Element))
        self.assertEqual(enc.get_factory().get_name(), 'theoraenc')
        self.assertEqual(enc.get_property('quality'), 48)
        self.assertEqual(enc.get_property('keyframe-force'), 64)

        enc = inst._make('theoraenc', {'quality': 50, 'keyframe-force': 32})
        self.assertTrue(enc.get_parent() is inst)
        self.assertTrue(isinstance(enc, gst.Element))
        self.assertEqual(enc.get_factory().get_name(), 'theoraenc')
        self.assertEqual(enc.get_property('quality'), 50)
        self.assertEqual(enc.get_property('keyframe-force'), 32)


class TestAudioEncoder(TestCase):
    klass = renderer.AudioEncoder

    def test_init(self):
        d = {
            'enc': 'vorbisenc',
            'props': {
                'quality': 0.5,
            },
        }
        inst = self.klass(d)
        self.assertTrue(isinstance(inst._enc, gst.Element))
        self.assertEqual(inst._enc.get_factory().get_name(), 'vorbisenc')
        self.assertEqual(inst._enc.get_property('quality'), 0.5)

        d = {
            'enc': 'vorbisenc',
            'caps': {'rate': 44100},
            'props': {'quality': 0.25},
        }
        inst = self.klass(d)
        self.assertTrue(isinstance(inst._enc, gst.Element))
        self.assertEqual(inst._enc.get_factory().get_name(), 'vorbisenc')
        self.assertEqual(inst._enc.get_property('quality'), 0.25)


class TestAbusively(LiveTestCase):
    def test_canned(self):
        pass
