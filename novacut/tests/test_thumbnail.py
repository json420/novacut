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
Unit tests for the `novacut.validate` module.
"""

from unittest import TestCase
import sys
from random import SystemRandom
from fractions import Fraction

from gi.repository import Gst
from dbase32 import random_id

from ..timefuncs import frame_to_nanosecond
from .. import thumbnail


random = SystemRandom()


class TestThumbnailer(TestCase):
    def test_init(self):
        def callback(inst, success):
            pass

        filename = '/tmp/' + random_id() + '.mov'
        indexes = [random.randrange(0, 5000) for i in range(15)]
        attachments = {}
        inst = thumbnail.Thumbnailer(callback, filename, indexes, attachments)
        self.assertIs(inst.attachments, attachments)
        self.assertEqual(inst.indexes, sorted(set(indexes)))
        self.assertIsNone(inst.framerate)
        self.assertIs(inst.changed, False)

        # filesrc:
        self.assertIsInstance(inst.src, Gst.Element)
        self.assertEqual(inst.src.get_factory().get_name(), 'filesrc')
        self.assertEqual(inst.src.get_property('location'), filename)

        # decodebin:
        self.assertIsInstance(inst.dec, Gst.Element)
        self.assertEqual(inst.dec.get_factory().get_name(), 'decodebin')

        # video and audio queues:
        self.assertIsInstance(inst.video_q, Gst.Element)
        self.assertEqual(inst.video_q.get_factory().get_name(), 'queue')
        self.assertIsNone(inst.audio_q)

        # videoconvert:
        self.assertIsInstance(inst.convert, Gst.Element)
        self.assertEqual(inst.convert.get_factory().get_name(), 'videoconvert')

        # videoscale:
        self.assertIsInstance(inst.scale, Gst.Element)
        self.assertEqual(inst.scale.get_factory().get_name(), 'videoscale')
        self.assertEqual(inst.scale.get_property('method'), 2)

        # jpegenc:
        self.assertIsInstance(inst.enc, Gst.Element)
        self.assertEqual(inst.enc.get_factory().get_name(), 'jpegenc')
        self.assertEqual(inst.enc.get_property('idct-method'), 2)

        # fakesink:
        self.assertIsInstance(inst.sink, Gst.Element)
        self.assertEqual(inst.sink.get_factory().get_name(), 'fakesink')
        self.assertEqual(inst.sink.get_property('signal-handoffs'), True)

        # Make sure all elements have been added to pipeline:
        children = (
            inst.src,
            inst.dec,
            inst.video_q,
            inst.convert,
            inst.scale,
            inst.enc,
            inst.sink,
        )
        for child in children:
            self.assertIs(child.get_parent(), inst.pipeline)

        # Check that Pipeline.connect() was used:
        self.assertEqual(len(inst.handlers), 4)
        self.assertIs(inst.handlers[0][0], inst.bus)
        self.assertIs(inst.handlers[1][0], inst.bus)
        self.assertIs(inst.handlers[2][0], inst.dec)
        self.assertIs(inst.handlers[3][0], inst.sink)

        # Make sure gsthelpers.Pipeline.__init__() was called:
        self.assertIs(inst.callback, callback)
        self.assertIsInstance(inst.pipeline, Gst.Pipeline)
        self.assertIsInstance(inst.bus, Gst.Bus)
        self.assertEqual(sys.getrefcount(inst), 6)
        self.assertIsNone(inst.destroy())
        self.assertFalse(hasattr(inst, 'pipeline'))
        self.assertFalse(hasattr(inst, 'bus'))
        self.assertEqual(inst.handlers, [])
        self.assertEqual(sys.getrefcount(inst), 2)

    def test_seek_to_frame(self):
        class DummyPipeline:
            def __init__(self):
                self._calls = []

            def seek_simple(self, frmt, flags, ns):
                self._calls.append((frmt, flags, ns))

        class Subclass(thumbnail.Thumbnailer):
            def __init__(self, pipeline, framerate):
                self.pipeline = pipeline
                self.framerate = framerate

        pipeline = DummyPipeline()
        framerate = Fraction(30000, 1001)
        inst = Subclass(pipeline, framerate)
        frmt = Gst.Format.TIME
        flags = Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT
        self.assertIsNone(inst.seek_to_frame(0))
        self.assertEqual(inst.target, 0)
        self.assertEqual(pipeline._calls, [
            (frmt, flags, 0),
        ])
        self.assertIsNone(inst.seek_to_frame(1))
        self.assertEqual(inst.target, 1)
        self.assertEqual(pipeline._calls, [
            (frmt, flags, 0),
            (frmt, flags, 33366666),
        ])
        self.assertIsNone(inst.seek_to_frame(2))
        self.assertEqual(inst.target, 2)
        self.assertEqual(pipeline._calls, [
            (frmt, flags, 0),
            (frmt, flags, 33366666),
            (frmt, flags, 66733333),
        ])

        for i in range(500):
            pipeline = DummyPipeline()
            inst = Subclass(pipeline, framerate)
            frame = random.randrange(1234567)
            self.assertIsNone(inst.seek_to_frame(frame))
            self.assertIs(inst.target, frame)
            self.assertEqual(pipeline._calls,
                [(frmt, flags, frame_to_nanosecond(frame, framerate))]
            )

    def test_next(self):
        class Subclass(thumbnail.Thumbnailer):
            def __init__(self, indexes, attachments):
                self.indexes = indexes
                self.attachments = attachments
                self._calls = []

            def seek_to_frame(self, frame):
                self._calls.append(('seek_to_frame', frame))

            def complete(self, success):
                self._calls.append(('complete', success))


        indexes = [17, 18, 19]
        attachments = {'18': 'foobar'}
        inst = Subclass(indexes, attachments)

        # Frame 17:
        self.assertIsNone(inst.next())
        self.assertEqual(inst.indexes, [18, 19])
        self.assertEqual(inst.attachments, {'18': 'foobar'})
        self.assertEqual(inst._calls, [
            ('seek_to_frame', 17),
        ])

        # Frame 18 should be skipped as it's already in attachments:
        self.assertIsNone(inst.next())
        self.assertEqual(inst.indexes, [])
        self.assertEqual(inst.attachments, {'18': 'foobar'})
        self.assertEqual(inst._calls, [
            ('seek_to_frame', 17),
            ('seek_to_frame', 19),
        ])

        # Pipeline.complete() should be called once indexes is empty:
        self.assertIsNone(inst.next())
        self.assertEqual(inst.indexes, [])
        self.assertEqual(inst.attachments, {'18': 'foobar'})
        self.assertEqual(inst._calls, [
            ('seek_to_frame', 17),
            ('seek_to_frame', 19),
            ('complete', True),
        ])


