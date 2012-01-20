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

from dc3lib.microfiber import random_id
from novacut2 import renderer

from .base import LiveTestCase, TempDir, resolve, sample1, sample2


clip1 = random_id()
clip2 = random_id()
slice1 = random_id()
slice2 = random_id()
slice3 = random_id()
slice4 = random_id()
slice5 = random_id()
sequence1 = random_id()
sequence2 = random_id()
sequence3 = random_id()

docs = [
    {
        '_id': sample1,
        'type': 'dmedia/file',
        'framerate': {'num': 25, 'denom': 1},
        'samplerate': 48000,
    },

    {
        '_id': sample2,
        'type': 'dmedia/file',
        'framerate': {'num': 25, 'denom': 1},
        'samplerate': 48000,
    },

    {
        '_id': slice4,
        'type': 'novacut/node',
        'node': {
            'src': sample2,
            'type': 'slice',
            'stream': 'video',
            'start': {'frame': 3 * 25},
            'stop': {'frame': 5 * 25},
        },
    },

    {
        '_id': slice5,
        'type': 'novacut/node',
        'node': {
            'src': sample1,
            'type': 'slice',
            'stream': 'video',
            'start': {'frame': 18 * 25},
            'stop': {'frame': 21 * 25},
        },
    },

    {
        '_id': sequence3,
        'type': 'novacut/node',
        'node': {
            'type': 'sequence',
            'src': [
                slice4,
                slice5,
                slice4,
            ],
        },
    },

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
        return resolve(_id)


class TestFunctions(TestCase):
    def test_make_element(self):
        d = {'name': 'theoraenc'}
        el = renderer.make_element(d)
        self.assertIsInstance(el, gst.Element)
        self.assertEqual(el.get_factory().get_name(), 'theoraenc')
        self.assertEqual(el.get_property('keyframe-force'), 64)
        self.assertEqual(el.get_property('quality'), 48)

        d = {
            'name': 'theoraenc',
            'props': {
                'quality': 40,
                'keyframe-force': 16,
            },
        }
        el = renderer.make_element(d)
        self.assertIsInstance(el, gst.Element)
        self.assertEqual(el.get_factory().get_name(), 'theoraenc')
        self.assertEqual(el.get_property('keyframe-force'), 16)
        self.assertEqual(el.get_property('quality'), 40)

    def test_caps_string(self):
        f = renderer.caps_string

        d = {'mime': 'audio/x-raw-float'}
        self.assertEqual(
            f(d),
            'audio/x-raw-float'
        )

        d = {
            'mime': 'audio/x-raw-float',
            'caps': {'rate': 44100},
        }
        self.assertEqual(
            f(d),
            'audio/x-raw-float, rate=44100'
        )

        d = {
            'mime': 'audio/x-raw-float',
            'caps': {'rate': 44100, 'channels': 1},
        }
        self.assertEqual(
            f(d),
            'audio/x-raw-float, channels=1, rate=44100'
        )

    def test_make_caps(self):
        f = renderer.make_caps

        self.assertIsNone(f({}))
        self.assertIsNone(f(None))

        d = {'mime': 'audio/x-raw-float'}
        c = f(d)
        self.assertIsInstance(c, gst.Caps)
        self.assertEqual(
            c.to_string(),
            'audio/x-raw-float'
        )

        d = {
            'mime': 'audio/x-raw-float',
            'caps': {'rate': 44100},
        }
        c = f(d)
        self.assertIsInstance(c, gst.Caps)
        self.assertEqual(
            c.to_string(),
            'audio/x-raw-float, rate=(int)44100'
        )

        d = {
            'mime': 'audio/x-raw-float',
            'caps': {'rate': 44100, 'channels': 1},
        }
        c = f(d)
        self.assertIsInstance(c, gst.Caps)
        self.assertEqual(
            c.to_string(),
            'audio/x-raw-float, channels=(int)1, rate=(int)44100'
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
        self.assertEqual(el.get_property('location'), resolve(clip1))

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
        self.assertEqual(el.get_property('location'), resolve(clip1))

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
        self.assertEqual(el.get_property('location'), resolve(clip1))

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
            'encoder': {
                'name': 'vorbisenc',
                'props': {
                    'quality': 0.5,
                },
            },
        }
        inst = self.klass(d)
        self.assertTrue(inst._d is d)

        for el in (inst._q1, inst._q2, inst._q3):
            self.assertIsInstance(el, gst.Element)
            self.assertTrue(el.get_parent() is inst)
            self.assertEqual(el.get_factory().get_name(), 'queue')

        self.assertIsInstance(inst._enc, gst.Element)
        self.assertTrue(inst._enc.get_parent() is inst)
        self.assertEqual(inst._enc.get_factory().get_name(), 'vorbisenc')
        self.assertEqual(inst._enc.get_property('quality'), 0.5)

        self.assertIsNone(inst._caps)

        # default properties
        d = {'encoder': {'name': 'vorbisenc'}}
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
            'encoder': {
                'name': 'vorbisenc',
                'props': {
                    'quality': 0.5,
                },
            },
            'filter': {
                'mime': 'audio/x-raw-float',
                'caps': {'rate': 44100, 'channels': 1},
            },
        }
        inst = self.klass(d)
        self.assertTrue(inst._d is d)
        self.assertIsInstance(inst._caps, gst.Caps)
        self.assertEqual(
            inst._caps.to_string(),
            'audio/x-raw-float, channels=(int)1, rate=(int)44100'
        )

    def test_repr(self):
        d = {
            'encoder': 'vorbisenc',
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
        d = {'encoder': 'vorbisenc'}
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
            'encoder': {
                'name': 'vorbisenc',
                'props': {
                    'quality': 0.5,
                },
            },
        }
        inst = self.klass(d)
        self.assertTrue(isinstance(inst._enc, gst.Element))
        self.assertEqual(inst._enc.get_factory().get_name(), 'vorbisenc')
        self.assertEqual(inst._enc.get_property('quality'), 0.5)

        d = {
            'encoder': {
                'name': 'vorbisenc',
                'props': {'quality': 0.25},
            },
            'filter': {
                'mime': 'audio/x-raw-float',
                'caps': {'rate': 44100},
            },
        }
        inst = self.klass(d)
        self.assertTrue(isinstance(inst._enc, gst.Element))
        self.assertEqual(inst._enc.get_factory().get_name(), 'vorbisenc')
        self.assertEqual(inst._enc.get_property('quality'), 0.25)


class TestVideoEncoder(TestCase):
    def test_init(self):
        d = {
            'encoder': {
                'name': 'theoraenc',
                'props': {'quality': 40},
            },
        }
        inst = renderer.VideoEncoder(d)
        self.assertIsInstance(inst._enc, gst.Element)
        self.assertTrue(inst._enc.get_parent() is inst)
        self.assertEqual(inst._enc.get_factory().get_name(), 'theoraenc')
        self.assertEqual(inst._enc.get_property('quality'), 40)
        self.assertIsNone(inst._caps)

        d = {
            'encoder': {
                'name': 'theoraenc',
                'props': {'quality': 40},
            },
            'filter': {
                'mime': 'video/x-raw-yuv',
                'caps': {
                    #'format': 'Y42B',  # FIXME: Hmm, why does this break it?
                    'width': 960,
                    'height': 540,
                },
            },
        }
        inst = renderer.VideoEncoder(d)
        self.assertIsInstance(inst._enc, gst.Element)
        self.assertTrue(inst._enc.get_parent() is inst)
        self.assertEqual(inst._enc.get_factory().get_name(), 'theoraenc')
        self.assertEqual(inst._enc.get_property('quality'), 40)
        self.assertIsInstance(inst._caps, gst.Caps)
        self.assertEqual(
            inst._caps.to_string(),
            'video/x-raw-yuv, height=(int)540, width=(int)960'
        )


class TestRenderer(TestCase):
    def test_init(self):
        tmp = TempDir()
        builder = DummyBuilder(docs)

        root = sequence1
        settings = {
            'muxer': {'name': 'oggmux'},
        }
        dst = tmp.join('out1.ogv')
        inst = renderer.Renderer(root, settings, builder, dst)

        self.assertIs(inst.root, root)
        self.assertIs(inst.settings, settings)
        self.assertIs(inst.builder, builder)

        self.assertIsInstance(inst.src, gst.Element)
        self.assertIs(inst.src.get_parent(), inst.pipeline)
        self.assertEqual(inst.src.get_factory().get_name(), 'gnlcomposition')

        self.assertIsInstance(inst.mux, gst.Element)
        self.assertIs(inst.mux.get_parent(), inst.pipeline)
        self.assertEqual(inst.mux.get_factory().get_name(), 'oggmux')

        self.assertIsInstance(inst.sink, gst.Element)
        self.assertIs(inst.sink.get_parent(), inst.pipeline)
        self.assertEqual(inst.sink.get_factory().get_name(), 'filesink')
        self.assertEqual(inst.sink.get_property('location'), dst)


class TestAbusively(LiveTestCase):
    def test_canned(self):
        tmp = TempDir()
        builder = DummyBuilder(docs)

        job = {
            'src': sequence3,
            'muxer': {'name': 'oggmux'},
            'video': {
                'encoder': {'name': 'theoraenc'},
                'filter': {
                    'mime': 'video/x-raw-yuv',
                    'caps': {
                        'width': '640',
                        'height': '360',
                    },
                },
            },
        }
        dst = tmp.join('out1.ogv')
        inst = renderer.Renderer(job, builder, dst)
        inst.run()
