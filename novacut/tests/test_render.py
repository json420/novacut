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
from queue import Queue
import sys

from dbase32 import random_id
from gi.repository import Gst

from .. import timefuncs
from ..settings import get_default_settings
from ..misc import random_start_stop
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


def random_framerate():
    num = random.randrange(1, 54321)
    denom = random.randrange(1, 54321)
    return (num, denom, Fraction(num, denom))


def random_filename():
    return '/tmp/' + random_id() + '.mov'


def random_slice():
    (start, stop) = random_start_stop()
    filename = random_filename()
    return render.Slice(random_id(), random_id(30), start, stop, filename)


class TestInput(TestCase):
    def test_init(self):
        def callback(inst, success):
            pass
        buffer_queue = Queue()
        s = random_slice()
        input_caps = Gst.caps_from_string('video/x-raw')

        inst = render.Input(callback, buffer_queue, s, input_caps)
        self.assertIs(inst.buffer_queue, buffer_queue)
        self.assertIs(inst.s, s)
        self.assertIs(inst.frame, s.start)
        self.assertIsNone(inst.framerate)

        # filesrc:
        self.assertIsInstance(inst.src, Gst.Element)
        self.assertEqual(inst.src.get_factory().get_name(), 'filesrc')
        self.assertEqual(inst.src.get_property('location'), s.filename)

        # decodebin:
        self.assertIsInstance(inst.dec, Gst.Element)
        self.assertEqual(inst.dec.get_factory().get_name(), 'decodebin')

        # videoconvert:
        self.assertIsInstance(inst.convert, Gst.Element)
        self.assertEqual(inst.convert.get_factory().get_name(), 'videoconvert')

        # videoscale:
        self.assertIsInstance(inst.scale, Gst.Element)
        self.assertEqual(inst.scale.get_factory().get_name(), 'videoscale')
        self.assertEqual(inst.scale.get_property('method'), 3)

        # appsink:
        self.assertIsInstance(inst.sink, Gst.Element)
        self.assertEqual(inst.sink.get_factory().get_name(), 'appsink')
        self.assertEqual(inst.sink.get_property('caps').to_string(),
            'video/x-raw'
        )
        self.assertIs(inst.sink.get_property('emit-signals'), True)
        self.assertEqual(inst.sink.get_property('max-buffers'), 1)

        # Make sure all elements have been added to Pipeline:
        for child in [inst.src, inst.dec, inst.convert, inst.scale, inst.sink]:
            self.assertIs(child.get_parent(), inst.pipeline)

        # Make sure gsthelpers.Pipeline.__init__() was called:
        self.assertIs(inst.callback, callback)
        self.assertIsInstance(inst.pipeline, Gst.Pipeline)
        self.assertIsInstance(inst.bus, Gst.Bus)
        self.assertEqual(sys.getrefcount(inst), 6)
        self.assertIsNone(inst.destroy())
        self.assertFalse(hasattr(inst, 'pipeline'))
        self.assertFalse(hasattr(inst, 'bus'))
        self.assertEqual(sys.getrefcount(inst), 2)

    def test_check_frame(self):
        class Subclass(render.Input):
            def __init__(self, s, frame, framerate):
                self.s = s
                self.frame = frame
                self.framerate = framerate

        s = random_slice()
        framerate = Fraction(30000, 1001)
        inst = Subclass(s, s.start, framerate)
        buf = timefuncs.video_pts_and_duration(s.start, s.start + 1, framerate)
        self.assertIs(inst.check_frame(buf), True)
        self.assertEqual(inst.frame, s.start)
        inst.frame += 1
        self.assertIs(inst.check_frame(buf), False)
        self.assertEqual(inst.frame, s.start + 1)

    def test_on_eos(self):
        class Subclass(render.Input):
            def __init__(self, s, frame):
                self.s = s
                self.frame = frame
                self._complete_calls = []

            def complete(self, success):
                self._complete_calls.append(success)

        s = random_slice()
        for frame in (s.stop, s.stop + 1, s.stop + 2):
            inst = Subclass(s, frame)
            self.assertIsNone(inst.on_eos('bus', 'msg'))
            self.assertEqual(inst._complete_calls, [])
        for frame in (s.stop - 1, s.stop - 2, s.stop - 3):
            inst = Subclass(s, frame)
            self.assertIsNone(inst.on_eos('bus', 'msg'))
            self.assertEqual(inst._complete_calls, [False])


class TestOutput(TestCase):
    def test_init(self):
        def callback(inst, success):
            pass
        buffer_queue = Queue()
        settings = get_default_settings()
        filename = random_filename()

        inst = render.Output(callback, buffer_queue, settings, filename)
        self.assertIs(inst.buffer_queue, buffer_queue)
        self.assertEqual(inst.frame, 0)
        self.assertIs(inst.sent_eos, False)
        self.assertEqual(inst.framerate, Fraction(30000, 1001))
        self.assertIsInstance(inst.input_caps, Gst.Caps)
        self.assertEqual(inst.input_caps.to_string(),
            'video/x-raw, chroma-site=(string)mpeg2, colorimetry=(string)bt709, format=(string)I420, height=(int)1080, interlace-mode=(string)progressive, pixel-aspect-ratio=(fraction)1/1, width=(int)1920'
        )

        # appsrc:
        self.assertIsInstance(inst.src, Gst.Element)
        self.assertEqual(inst.src.get_factory().get_name(), 'appsrc')
        self.assertEqual(inst.src.get_property('caps').to_string(),
            'video/x-raw, chroma-site=(string)mpeg2, colorimetry=(string)bt709, format=(string)I420, framerate=(fraction)30000/1001, height=(int)1080, interlace-mode=(string)progressive, pixel-aspect-ratio=(fraction)1/1, width=(int)1920'
        )
        self.assertEqual(inst.src.get_property('format'), 3)

        # x264enc:
        self.assertIsInstance(inst.enc, Gst.Element)
        self.assertEqual(inst.enc.get_factory().get_name(), 'x264enc')
        self.assertEqual(inst.enc.get_property('bitrate'), 8192)
        self.assertEqual(inst.enc.get_property('psy-tune'), 5)

        # matroskamux:
        self.assertIsInstance(inst.mux, Gst.Element)
        self.assertEqual(inst.mux.get_factory().get_name(), 'matroskamux')

        # filesink:
        self.assertIsInstance(inst.sink, Gst.Element)
        self.assertEqual(inst.sink.get_factory().get_name(), 'filesink')
        self.assertEqual(inst.sink.get_property('location'), filename)
        self.assertEqual(inst.sink.get_property('buffer-mode'), 2)

        # Make sure all elements have been added to Pipeline:
        for child in [inst.src, inst.enc, inst.mux, inst.sink]:
            self.assertIs(child.get_parent(), inst.pipeline)

        # Make sure gsthelpers.Pipeline.__init__() was called:
        self.assertIs(inst.callback, callback)
        self.assertIsInstance(inst.pipeline, Gst.Pipeline)
        self.assertIsInstance(inst.bus, Gst.Bus)
        self.assertEqual(sys.getrefcount(inst), 5)
        self.assertIsNone(inst.destroy())
        self.assertFalse(hasattr(inst, 'pipeline'))
        self.assertFalse(hasattr(inst, 'bus'))
        self.assertEqual(sys.getrefcount(inst), 2)


class TestRenderer(TestCase):
    def test_init(self):
        def callback(inst, success):
            pass
        slices = tuple(random_slice() for i in range(69))
        settings = get_default_settings()
        filename = random_filename()

        inst = render.Renderer(callback, slices, settings, filename)
        self.assertIs(inst.callback, callback)
        self.assertIs(inst.slices, slices)
        self.assertIsNone(inst.success)
        self.assertEqual(inst.total_frames,
            sum(s.stop - s.start for s in slices)
        )
        self.assertIsInstance(inst.buffer_queue, Queue)
        self.assertIsNone(inst.input)
        self.assertIsInstance(inst.output, render.Output)
        self.assertIs(inst.input_caps, inst.output.input_caps)
        self.assertIsInstance(inst.input_caps, Gst.Caps)
        self.assertEqual(inst.input_caps.to_string(),
            'video/x-raw, chroma-site=(string)mpeg2, colorimetry=(string)bt709, format=(string)I420, height=(int)1080, interlace-mode=(string)progressive, pixel-aspect-ratio=(fraction)1/1, width=(int)1920'
        )

    def test_on_output_complete(self):
        class DummyOutput:
            def __init__(self, frame):
                self.frame = frame

        class Subclass(render.Renderer):
            def __init__(self, total_frames, output):
                self.total_frames = total_frames
                self.output = output
                self._complete_calls = []

            def complete(self, success):
                self._complete_calls.append(success)

        # success is True, correct total frames:
        output = DummyOutput(17)
        inst = Subclass(17, output)
        self.assertIsNone(inst.on_output_complete(output, True))
        self.assertEqual(inst._complete_calls, [True])

        # success is False, correct total frames:
        inst = Subclass(17, output)
        self.assertIsNone(inst.on_output_complete(output, False))
        self.assertEqual(inst._complete_calls, [False])

        # success is True, incorrect total frames:
        for total in (16, 18):
            inst = Subclass(total, output)
            self.assertIsNone(inst.on_output_complete(output, True))
            self.assertEqual(inst._complete_calls, [False])

