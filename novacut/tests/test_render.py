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
        self.assertIs(inst.drained, False)

        # Make sure gsthelpers.Pipeline.__init__() was called:
        self.assertIs(inst.callback, callback)
        self.assertIsInstance(inst.pipeline, Gst.Pipeline)
        self.assertIsInstance(inst.bus, Gst.Bus)
        self.assertIsNone(inst.destroy())
        self.assertFalse(hasattr(inst, 'pipeline'))
        self.assertFalse(hasattr(inst, 'bus'))

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

        # Make sure gsthelpers.Pipeline.__init__() was called:
        self.assertIs(inst.callback, callback)
        self.assertIsInstance(inst.pipeline, Gst.Pipeline)
        self.assertIsInstance(inst.bus, Gst.Bus)
        self.assertIsNone(inst.destroy())
        self.assertFalse(hasattr(inst, 'pipeline'))
        self.assertFalse(hasattr(inst, 'bus'))


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

