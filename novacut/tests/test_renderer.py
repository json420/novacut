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

from microfiber import random_id
from novacut import renderer
from gi.repository import Gst

from .base import TempDir, resolve, random_file_id, sample1, sample2


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
        super(DummyBuilder, self).__init__()
        self._docmap = dict(
            (doc['_id'], doc) for doc in docs
        )

    def get_doc(self, _id):
        return self._docmap[_id]

    def resolve_file(self, _id):
        return resolve(_id)


class TestNoSuchElement(TestCase):
    def test_init(self):
        inst = renderer.NoSuchElement('foobar')
        self.assertIsInstance(inst, Exception)
        self.assertEqual(inst.name, 'foobar')
        self.assertEqual(str(inst), "GStreamer element 'foobar' not available")


class TestFunctions(TestCase):
    def test_make_element(self):
        # Test with bad 'name' type:
        with self.assertRaises(TypeError) as cm:
            renderer.make_element(b'theoraenc')
        self.assertEqual(
            str(cm.exception),
            "name: need a <class 'str'>; got a <class 'bytes'>: b'theoraenc'"
        )

        # Test with bad 'props' type:
        with self.assertRaises(TypeError) as cm:
            renderer.make_element('video/x-raw', 'width=800')
        self.assertEqual(
            str(cm.exception),
            "props: need a <class 'dict'>; got a <class 'str'>: 'width=800'"
        )

        # Test our assumptions about Gst.ElementFactory.make():
        self.assertIsNone(Gst.ElementFactory.make('foobar', None))

        # Test that NoSuchElement is raised
        with self.assertRaises(renderer.NoSuchElement) as cm:
            renderer.make_element('foobar')
        self.assertEqual(
            str(cm.exception),
            "GStreamer element 'foobar' not available"
        )

        # Test with a good element
        element = renderer.make_element('theoraenc')
        self.assertIsInstance(element, Gst.Element)
        self.assertEqual(element.get_factory().get_name(), 'theoraenc')
        self.assertEqual(element.get_property('quality'), 48)
        self.assertEqual(element.get_property('speed-level'), 1)

        # Test with props also
        element = renderer.make_element('theoraenc',
            {'quality': 40, 'speed-level': 2}
        )
        self.assertIsInstance(element, Gst.Element)
        self.assertEqual(element.get_factory().get_name(), 'theoraenc')
        self.assertEqual(element.get_property('quality'), 40)
        self.assertEqual(element.get_property('speed-level'), 2)

    def test_element_from_desc(self):
        el = renderer.element_from_desc('theoraenc')
        self.assertIsInstance(el, Gst.Element)
        self.assertEqual(el.get_factory().get_name(), 'theoraenc')
        self.assertEqual(el.get_property('keyframe-force'), 64)
        self.assertEqual(el.get_property('quality'), 48)

        d = {'name': 'theoraenc'}
        el = renderer.element_from_desc(d)
        self.assertIsInstance(el, Gst.Element)
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
        el = renderer.element_from_desc(d)
        self.assertIsInstance(el, Gst.Element)
        self.assertEqual(el.get_factory().get_name(), 'theoraenc')
        self.assertEqual(el.get_property('keyframe-force'), 16)
        self.assertEqual(el.get_property('quality'), 40)

    def test_caps_string(self):
        self.assertEqual(
            renderer.caps_string('audio/x-raw'),
            'audio/x-raw'
        )

        self.assertEqual(
            renderer.caps_string('audio/x-raw', {'rate': 44100}), 
            'audio/x-raw, rate=44100'
        )

        self.assertEqual(
            renderer.caps_string('audio/x-raw', {'rate': 44100, 'channels': 1}),
            'audio/x-raw, channels=1, rate=44100'
        )

    def test_make_caps(self):
        self.assertIsNone(renderer.make_caps('audio/x-raw', None))

        c = renderer.make_caps('audio/x-raw', {'rate': 44100})
        self.assertIsInstance(c, Gst.Caps)
        self.assertEqual(
            c.to_string(),
            'audio/x-raw, rate=(int)44100'
        )

        c = renderer.make_caps('audio/x-raw', {'rate': 44100, 'channels': 1})
        self.assertIsInstance(c, Gst.Caps)
        self.assertEqual(
            c.to_string(),
            'audio/x-raw, channels=(int)1, rate=(int)44100'
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

        # Video stream, offset=0
        self.assertEqual(renderer.build_slice(b, doc, 0), 4 * Gst.SECOND)
        el = b.last
        self.assertIsInstance(el, Gst.Element)
        self.assertEqual(el.get_factory().get_name(), 'gnlurisource')
        self.assertEqual(el.get_property('media-start'), 8 * Gst.SECOND)
        self.assertEqual(el.get_property('media-duration'), 4 * Gst.SECOND)
        self.assertEqual(el.get_property('start'), 0)
        self.assertEqual(el.get_property('duration'), 4 * Gst.SECOND)
        self.assertEqual(el.get_property('caps').to_string(), 'video/x-raw')
        self.assertEqual(el.get_property('uri'), 'file://' + resolve(clip1))

        # Video stream, offset=3s
        self.assertEqual(
            renderer.build_slice(b, doc, 3 * Gst.SECOND),
            4 * Gst.SECOND
        )
        el = b.last
        self.assertIsInstance(el, Gst.Element)
        self.assertEqual(el.get_factory().get_name(), 'gnlurisource')
        self.assertEqual(el.get_property('media-start'), 8 * Gst.SECOND)
        self.assertEqual(el.get_property('media-duration'), 4 * Gst.SECOND)
        self.assertEqual(el.get_property('start'), 3 * Gst.SECOND)
        self.assertEqual(el.get_property('duration'), 4 * Gst.SECOND)
        self.assertEqual(el.get_property('caps').to_string(), 'video/x-raw')
        self.assertEqual(el.get_property('uri'), 'file://' + resolve(clip1))

        # Audio stream, offset=0
        doc['node']['stream'] = 'audio'
        self.assertEqual(renderer.build_slice(b, doc, 0), 4 * Gst.SECOND)
        el = b.last
        self.assertIsInstance(el, Gst.Element)
        self.assertEqual(el.get_factory().get_name(), 'gnlurisource')
        self.assertEqual(el.get_property('media-start'), 8 * Gst.SECOND)
        self.assertEqual(el.get_property('media-duration'), 4 * Gst.SECOND)
        self.assertEqual(el.get_property('start'), 0)
        self.assertEqual(el.get_property('duration'), 4 * Gst.SECOND)
        self.assertEqual(
            el.get_property('caps').to_string(),
            'audio/x-raw'
        )
        self.assertEqual(el.get_property('uri'), 'file://' + resolve(clip1))

        # Audio stream, offset=3s
        self.assertEqual(
            renderer.build_slice(b, doc, 3 * Gst.SECOND),
            4 * Gst.SECOND
        )
        el = b.last
        self.assertIsInstance(el, Gst.Element)
        self.assertEqual(el.get_factory().get_name(), 'gnlurisource')
        self.assertEqual(el.get_property('media-start'), 8 * Gst.SECOND)
        self.assertEqual(el.get_property('media-duration'), 4 * Gst.SECOND)
        self.assertEqual(el.get_property('start'), 3 * Gst.SECOND)
        self.assertEqual(el.get_property('duration'), 4 * Gst.SECOND)
        self.assertEqual(
            el.get_property('caps').to_string(),
            'audio/x-raw'
        )
        self.assertEqual(el.get_property('uri'), 'file://' + resolve(clip1))

        # Audio stream specified in samples, offset=0
        doc = {
            'node': {
                'src': clip1,
                'type': 'slice',
                'stream': 'audio',
                'start': {'sample': 8 * 48000},
                'stop': {'sample': 12 * 48000},
            },
        }
        self.assertEqual(renderer.build_slice(b, doc, 0), 4 * Gst.SECOND)
        el = b.last
        self.assertIsInstance(el, Gst.Element)
        self.assertEqual(el.get_factory().get_name(), 'gnlurisource')
        self.assertEqual(el.get_property('media-start'), 8 * Gst.SECOND)
        self.assertEqual(el.get_property('media-duration'), 4 * Gst.SECOND)
        self.assertEqual(el.get_property('start'), 0)
        self.assertEqual(el.get_property('duration'), 4 * Gst.SECOND)
        self.assertEqual(
            el.get_property('caps').to_string(),
            'audio/x-raw'
        )
        self.assertEqual(el.get_property('uri'), 'file://' + resolve(clip1))

        # Audio stream specified in samples, offset=3s
        self.assertEqual(
            renderer.build_slice(b, doc, 3 * Gst.SECOND),
            4 * Gst.SECOND
        )
        el = b.last
        self.assertIsInstance(el, Gst.Element)
        self.assertEqual(el.get_factory().get_name(), 'gnlurisource')
        self.assertEqual(el.get_property('media-start'), 8 * Gst.SECOND)
        self.assertEqual(el.get_property('media-duration'), 4 * Gst.SECOND)
        self.assertEqual(el.get_property('start'), 3 * Gst.SECOND)
        self.assertEqual(el.get_property('duration'), 4 * Gst.SECOND)
        self.assertEqual(
            el.get_property('caps').to_string(),
            'audio/x-raw'
        )
        self.assertEqual(el.get_property('uri'), 'file://' + resolve(clip1))

    def test_build_sequence(self):
        b = DummyBuilder(docs)
        self.assertEqual(
            renderer.build_sequence(b, b.get_doc(sequence1), 0),
            7 * Gst.SECOND
        )

        b = DummyBuilder(docs)
        self.assertEqual(
            renderer.build_sequence(b, b.get_doc(sequence2), 0),
            9 * Gst.SECOND
        )

    def test_build_audio_slice(self):
        file_id = random_file_id()
        file = {
            '_id': file_id,
            'samplerate': 48000,
        }
        b = DummyBuilder([file])

        doc = {
            'node': {
                'src': file_id,
                'start': 48038,
                'stop': 79453,
            },
        }
        (samples, element) = renderer.build_audio_slice(b, doc, 0)
        self.assertEqual(samples, 31415)
        self.assertIsInstance(element, Gst.Element)
        self.assertEqual(element.get_factory().get_name(), 'gnlurisource')
        self.assertEqual(
            element.get_property('caps').to_string(),
            'audio/x-raw'
        )
        self.assertEqual(
            element.get_property('uri'),
            'file://' + resolve(file_id)
        )
        self.assertEqual(element.get_property('media-start'), 1000791666)
        self.assertEqual(element.get_property('media-duration'), 654479167)
        self.assertEqual(element.get_property('start'), 0)
        self.assertEqual(element.get_property('duration'), 654479166)

        (samples, element) = renderer.build_audio_slice(b, doc, 48038)
        self.assertEqual(samples, 31415)
        self.assertIsInstance(element, Gst.Element)
        self.assertEqual(element.get_factory().get_name(), 'gnlurisource')
        self.assertEqual(
            element.get_property('caps').to_string(),
            'audio/x-raw'
        )
        self.assertEqual(
            element.get_property('uri'),
            'file://' + resolve(file_id)
        )
        self.assertEqual(element.get_property('media-start'), 1000791666)
        self.assertEqual(element.get_property('media-duration'), 654479167)
        self.assertEqual(element.get_property('start'), 1000791666)
        self.assertEqual(element.get_property('duration'), 654479167)


class TestBuilder(TestCase):

    def test_init(self):
        builder = renderer.Builder()
        self.assertIsNone(builder.video)
        self.assertIsNone(builder.audio)
        self.assertIsNone(builder.last)

    def test_add(self):
        builder = renderer.Builder()
        self.assertIsNone(builder.video)
        self.assertIsNone(builder.audio)

        child1 = Gst.ElementFactory.make('gnlurisource', None)
        self.assertIsNone(builder.add(child1, 'video'))
        self.assertIs(child1.get_parent(), builder.video)
        self.assertIs(builder.last, child1)
        self.assertIsInstance(builder.video, Gst.Element)
        self.assertEqual(
            builder.video.get_factory().get_name(), 'gnlcomposition'
        )
        self.assertIsNone(builder.audio)

        child2 = Gst.ElementFactory.make('gnlurisource', None)
        self.assertIsNone(builder.add(child2, 'audio'))
        self.assertIs(child2.get_parent(), builder.audio)
        self.assertIs(builder.last, child2)
        self.assertIsInstance(builder.audio, Gst.Element)
        self.assertEqual(
            builder.audio.get_factory().get_name(), 'gnlcomposition'
        )

        self.assertIs(child1.get_parent(), builder.video)
        self.assertEqual(
            builder.video.get_factory().get_name(), 'gnlcomposition'
        )


class TestEncodeBin(TestCase):

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
        inst = renderer.EncoderBin(d, 'audio/x-raw')
        self.assertTrue(inst._d is d)
        return

        for el in (inst._q1, inst._q2, inst._q3):
            self.assertIsInstance(el, Gst.Element)
            self.assertTrue(el.get_parent() is inst)
            self.assertEqual(el.get_factory().get_name(), 'queue')

        self.assertIsInstance(inst._enc, Gst.Element)
        self.assertTrue(inst._enc.get_parent() is inst)
        self.assertEqual(inst._enc.get_factory().get_name(), 'vorbisenc')
        self.assertEqual(inst._enc.get_property('quality'), 0.5)

        self.assertIsNone(inst._caps)

        # default properties
        d = {'encoder': {'name': 'vorbisenc'}}
        inst = renderer.EncoderBin(d, 'audio/x-raw')
        self.assertTrue(inst._d is d)

        self.assertTrue(inst._q1.get_parent() is inst)
        self.assertTrue(isinstance(inst._q1, Gst.Element))
        self.assertEqual(inst._q1.get_factory().get_name(), 'queue')

        self.assertTrue(inst._enc.get_parent() is inst)
        self.assertTrue(isinstance(inst._enc, Gst.Element))
        self.assertEqual(inst._enc.get_factory().get_name(), 'vorbisenc')
        self.assertNotEqual(inst._enc.get_property('quality'), 0.5)

        self.assertTrue(inst._q2.get_parent() is inst)
        self.assertTrue(isinstance(inst._q2, Gst.Element))
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
                'mime': 'audio/x-raw',
                'caps': {'rate': 44100, 'channels': 1},
            },
        }
        inst = renderer.EncoderBin(d, 'audio/x-raw')
        self.assertTrue(inst._d is d)
        self.assertIsInstance(inst._caps, Gst.Caps)
        self.assertEqual(
            inst._caps.to_string(),
            'audio/x-raw, channels=(int)1, rate=(int)44100'
        )

    def test_repr(self):
        d = {
            'encoder': 'vorbisenc',
            'props': {
                'quality': 0.5,
            },
        }

        inst = renderer.EncoderBin(d, 'audio/x-raw')
        self.assertEqual(
            repr(inst),
            'EncoderBin({!r})'.format(d)
        )

        class FooBar(renderer.EncoderBin):
            pass
        inst = FooBar(d, 'audio/x-raw')
        self.assertEqual(
            repr(inst),
            'FooBar({!r})'.format(d)
        )

    def test_make(self):
        d = {'encoder': 'vorbisenc'}
        inst = renderer.EncoderBin(d, 'audio/x-raw')

        enc = inst._make('theoraenc')
        self.assertTrue(enc.get_parent() is inst)
        self.assertTrue(isinstance(enc, Gst.Element))
        self.assertEqual(enc.get_factory().get_name(), 'theoraenc')
        self.assertEqual(enc.get_property('quality'), 48)
        self.assertEqual(enc.get_property('keyframe-force'), 64)

        enc = inst._make('theoraenc', {'quality': 50, 'keyframe-force': 32})
        self.assertTrue(enc.get_parent() is inst)
        self.assertTrue(isinstance(enc, Gst.Element))
        self.assertEqual(enc.get_factory().get_name(), 'theoraenc')
        self.assertEqual(enc.get_property('quality'), 50)
        self.assertEqual(enc.get_property('keyframe-force'), 32)


class TestAudioEncoder(TestCase):
    def test_init(self):
        d = {
            'encoder': {
                'name': 'vorbisenc',
                'props': {
                    'quality': 0.5,
                },
            },
        }
        inst = renderer.AudioEncoder(d)
        self.assertTrue(isinstance(inst._enc, Gst.Element))
        self.assertEqual(inst._enc.get_factory().get_name(), 'vorbisenc')
        self.assertEqual(inst._enc.get_property('quality'), 0.5)
        self.assertIsNone(inst._caps)

        d = {
            'encoder': {
                'name': 'vorbisenc',
                'props': {'quality': 0.25},
            },
            'caps': {'rate': 44100},
        }
        inst = renderer.AudioEncoder(d)
        self.assertTrue(isinstance(inst._enc, Gst.Element))
        self.assertEqual(inst._enc.get_factory().get_name(), 'vorbisenc')
        self.assertEqual(inst._enc.get_property('quality'), 0.25)
        self.assertIsInstance(inst._caps, Gst.Caps)
        self.assertEqual(
            inst._caps.to_string(),
            'audio/x-raw, rate=(int)44100'
        )


class TestVideoEncoder(TestCase):
    def test_init(self):
        d = {
            'encoder': {
                'name': 'theoraenc',
                'props': {'quality': 40},
            },
        }
        inst = renderer.VideoEncoder(d)
        self.assertIsInstance(inst._enc, Gst.Element)
        self.assertTrue(inst._enc.get_parent() is inst)
        self.assertEqual(inst._enc.get_factory().get_name(), 'theoraenc')
        self.assertEqual(inst._enc.get_property('quality'), 40)
        self.assertIsNone(inst._caps)

        d = {
            'encoder': {
                'name': 'theoraenc',
                'props': {'quality': 40},
            },
            'caps': {
                'format': 'Y42B',
                'width': 960,
                'height': 540,
            },
        }
        inst = renderer.VideoEncoder(d)
        self.assertIsInstance(inst._enc, Gst.Element)
        self.assertTrue(inst._enc.get_parent() is inst)
        self.assertEqual(inst._enc.get_factory().get_name(), 'theoraenc')
        self.assertEqual(inst._enc.get_property('quality'), 40)
        self.assertIsInstance(inst._caps, Gst.Caps)
        self.assertEqual(
            inst._caps.to_string(),
            'video/x-raw, format=(string)Y42B, height=(int)540, width=(int)960'
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

        self.assertIsInstance(inst.sources, tuple)
        self.assertEqual(len(inst.sources), 1)
        src = inst.sources[0]
        self.assertIs(src.get_parent(), inst.pipeline)
        self.assertEqual(src.get_factory().get_name(), 'gnlcomposition')

        self.assertIsInstance(inst.mux, Gst.Element)
        self.assertIs(inst.mux.get_parent(), inst.pipeline)
        self.assertEqual(inst.mux.get_factory().get_name(), 'oggmux')

        self.assertIsInstance(inst.sink, Gst.Element)
        self.assertIs(inst.sink.get_parent(), inst.pipeline)
        self.assertEqual(inst.sink.get_factory().get_name(), 'filesink')
        self.assertEqual(inst.sink.get_property('location'), dst)

