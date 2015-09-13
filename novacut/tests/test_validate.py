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

from ..timefuncs import Timestamp, frame_to_nanosecond, video_pts_and_duration
from .. import validate


random = SystemRandom()


class TestValidator(TestCase):
    def test_init(self):
        def callback(inst, success):
            pass

        for full in (True, False):
            for strict in (True, False):
                filename = '/tmp/' + random_id() + '.mov'
                inst = validate.Validator(callback, filename, full, strict)
                self.assertIs(inst.full, full)
                self.assertIs(inst.strict, strict)
                self.assertEqual(inst.frame, 0)
                self.assertIsNone(inst.framerate)
                self.assertEqual(inst.info, {'valid': True})

                # Check Gst.Element:
                self.assertIsInstance(inst.src, Gst.Element)
                self.assertEqual(inst.src.get_factory().get_name(), 'filesrc')
                self.assertEqual(inst.src.get_property('location'), filename)
                self.assertIsInstance(inst.dec, Gst.Element)
                self.assertEqual(inst.dec.get_factory().get_name(), 'decodebin')
                self.assertIsInstance(inst.video_q, Gst.Element)
                self.assertEqual(inst.video_q.get_factory().get_name(), 'queue')
                self.assertIsNone(inst.audio_q)
                self.assertIsInstance(inst.sink, Gst.Element)
                self.assertEqual(inst.sink.get_factory().get_name(), 'fakesink')
                self.assertIs(inst.sink.get_property('signal-handoffs'), True)
                for child in [inst.src, inst.dec, inst.video_q, inst.sink]:
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
                self.assertEqual(sys.getrefcount(inst), 2)

    def test_mark_invalid(self):
        class Subclass(validate.Validator):
            def __init__(self, full):
                assert isinstance(full, bool)
                self.full = full
                self.info = {'valid': True}
                self._complete_calls = []

            def complete(self, success):
                self._complete_calls.append(success)

        # Test when full=False:
        inst = Subclass(False)
        self.assertIsNone(inst.mark_invalid())
        self.assertEqual(inst.info, {'valid': False})
        self.assertEqual(inst._complete_calls, [False])

        # Repeat, should only call Pipeline.complete() once:
        self.assertIsNone(inst.mark_invalid())
        self.assertEqual(inst.info, {'valid': False})
        self.assertEqual(inst._complete_calls, [False])

        # Test when full=True:
        inst = Subclass(True)
        self.assertIsNone(inst.mark_invalid())
        self.assertEqual(inst.info, {'valid': False})
        self.assertEqual(inst._complete_calls, [])

        # Repeat, should still not call Pipeline.complete():
        self.assertIsNone(inst.mark_invalid())
        self.assertEqual(inst.info, {'valid': False})
        self.assertEqual(inst._complete_calls, [])

    def test_check_frame(self):
        class Subclass(validate.Validator):
            def __init__(self, frame, framerate, strict):
                assert isinstance(frame, int) and frame >= 0
                assert isinstance(framerate, Fraction)
                assert isinstance(strict, bool)
                self.frame = frame
                self.framerate = framerate
                self.strict = strict
                self._mark_invalid_calls = 0

            def mark_invalid(self):
                self._mark_invalid_calls += 1

        frame = random.randrange(123456)
        framerate = Fraction(24000, 1001)

        # Exactly matching ts.pts, ts.buf:
        ts = video_pts_and_duration(frame, framerate)
        for strict in (True, False):
            inst = Subclass(frame, framerate, strict)
            self.assertIsNone(inst.check_frame(ts))
            self.assertEqual(inst._mark_invalid_calls, 0)

        # pts or duration is off by one nanosecond, strict=False:
        bad = (
            Timestamp(ts.pts - 1, ts.duration),
            Timestamp(ts.pts + 1, ts.duration),
            Timestamp(ts.pts, ts.duration - 1),
            Timestamp(ts.pts, ts.duration + 1),
        )
        for bad_ts in bad:
            inst = Subclass(frame, framerate, False)
            self.assertIsNone(inst.check_frame(bad_ts))
            self.assertEqual(inst._mark_invalid_calls, 0)

        # pts or duration is off by one nanosecond, strict=True:
        for badts in bad:
            inst = Subclass(frame, framerate, True)
            self.assertIsNone(inst.check_frame(bad_ts))
            self.assertEqual(inst._mark_invalid_calls, 1)

        # pts doesn't round to nearest frame, strict=False:
        error = int(ts.duration * 0.51)
        bad = (
            Timestamp(ts.pts + error, ts.duration),
            Timestamp(ts.pts - error, ts.duration),
        )
        for bad_ts in bad:
            inst = Subclass(frame, framerate, False)
            self.assertIsNone(inst.check_frame(bad_ts))
            self.assertEqual(inst._mark_invalid_calls, 1)

        # pts doesn't round to nearest frame, strict=True:
        error = int(ts.duration * 0.51)
        bad = (
            Timestamp(ts.pts + error, ts.duration),
            Timestamp(ts.pts - error, ts.duration),
        )
        for bad_ts in bad:
            inst = Subclass(frame, framerate, True)
            self.assertIsNone(inst.check_frame(bad_ts))
            self.assertEqual(inst._mark_invalid_calls, 2)

    def test_check_duration(self):
        class Subclass(validate.Validator):
            def __init__(self, framerate, frames, duration, strict):
                assert isinstance(framerate, Fraction)
                assert isinstance(frames, int) and frames >= 0
                assert isinstance(duration, int)
                assert isinstance(strict, bool)
                self.framerate = framerate
                self.info = {'frames': frames, 'duration': duration}
                self.strict = strict
 
        framerate = Fraction(24000, 1001)
        frames = random.randrange(123456)

        # Exactly matching duration:
        duration = frame_to_nanosecond(frames, framerate)
        for strict in (True, False):
            inst = Subclass(framerate, frames, duration, strict)
            self.assertIsNone(inst.check_duration())
            self.assertEqual(inst.info,
                {'frames': frames, 'duration': duration}
            )
 
        # Duration is off by one nanosecond, strict=False:
        bad = (duration - 1, duration + 1)
        for bad_dur in bad:
            inst = Subclass(framerate, frames, bad_dur, False)
            self.assertIsNone(inst.check_duration())
            self.assertEqual(inst.info,
                {'frames': frames, 'duration': bad_dur}
            )

        # Duration is off by one nanosecond, strict=True:
        for bad_dur in bad:
            inst = Subclass(framerate, frames, bad_dur, True)
            self.assertIsNone(inst.check_duration())
            self.assertEqual(inst.info,
                {'frames': frames, 'duration': bad_dur, 'valid': False}
            )

        # Duration doesn't round to frames:
        error = int(duration * 0.51)
        for bad_dur in (duration - error, duration + error):
            for strict in (True, False):
                inst = Subclass(framerate, frames, bad_dur, strict)
                self.assertIsNone(inst.check_duration())
                self.assertEqual(inst.info,
                    {'frames': frames, 'duration': bad_dur, 'valid': False}
                )

