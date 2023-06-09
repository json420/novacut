# novacut: the collaborative video editor
# Copyright (C) 2012 Novacut Inc
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
Unit tests for the `novacut.timefuncs` module.
"""

from unittest import TestCase
from fractions import Fraction

from novacut.misc import random_start_stop
from novacut import timefuncs


class TestFunctions(TestCase):   
    def test_frame_to_nanosecond(self):
        self.assertEqual(
            timefuncs.frame_to_nanosecond(0, Fraction(24, 1)),
            0
        )
        self.assertEqual(
            timefuncs.frame_to_nanosecond(0, Fraction(30000, 1001)),
            0
        )
        self.assertEqual(
            timefuncs.frame_to_nanosecond(1, Fraction(24, 1)),
            41666666
        )
        self.assertEqual(
            timefuncs.frame_to_nanosecond(1, Fraction(30000, 1001)),
            33366666
        )
        self.assertEqual(
            timefuncs.frame_to_nanosecond(24, Fraction(24, 1)),
            1000000000
        )
        self.assertEqual(
            timefuncs.frame_to_nanosecond(30, Fraction(30000, 1001)),
            1001000000
        )

    def test_nanosecond_to_frame(self):
        # nanosecond_to_frame() rounds to the nearest int, so we should be able
        # to round-trip the values
        framerates = [
            Fraction(30000, 1001),
            Fraction(25, 1),
            Fraction(24, 1),
        ]
        for framerate in framerates:
            for i in range(100000):
                ns = timefuncs.frame_to_nanosecond(i, framerate)
                self.assertEqual(
                    timefuncs.nanosecond_to_frame(ns, framerate),
                    i
                )

    def test_sample_to_nanosecond(self):
        self.assertEqual(timefuncs.sample_to_nanosecond(0, 48000), 0)
        self.assertEqual(timefuncs.sample_to_nanosecond(0, 44100), 0)
        self.assertEqual(timefuncs.sample_to_nanosecond(1, 48000), 20833)
        self.assertEqual(timefuncs.sample_to_nanosecond(1, 44100), 22675)
        self.assertEqual(timefuncs.sample_to_nanosecond(480, 48000), 10000000)
        self.assertEqual(timefuncs.sample_to_nanosecond(441, 44100), 10000000)

    def test_nanosecond_to_sample(self):
        # nanosecond_to_sample() rounds to the nearest int, so we should be able
        # to round-trip the values
        for samplerate in (96000, 48000, 44100):
            for i in range(100000):
                ns = timefuncs.sample_to_nanosecond(i, samplerate)
                self.assertEqual(
                    timefuncs.nanosecond_to_sample(ns, samplerate),
                    i
                )

    def test_frame_to_sample(self):
        framerate = Fraction(30000, 1001)
        self.assertEqual(timefuncs.frame_to_sample(0, framerate, 48000), 0)
        self.assertEqual(timefuncs.frame_to_sample(0, framerate, 44100), 0)
        self.assertEqual(timefuncs.frame_to_sample(1, framerate, 48000), 1601)
        self.assertEqual(timefuncs.frame_to_sample(1, framerate, 44100), 1471)
        framerate = Fraction(24, 1)
        self.assertEqual(timefuncs.frame_to_sample(0, framerate, 48000), 0)
        self.assertEqual(timefuncs.frame_to_sample(0, framerate, 44100), 0)
        self.assertEqual(timefuncs.frame_to_sample(1, framerate, 48000), 2000)
        self.assertEqual(timefuncs.frame_to_sample(1, framerate, 44100), 1837)

    def test_sample_to_frame(self):
        framerate = Fraction(30000, 1001)
        self.assertEqual(timefuncs.sample_to_frame(0, 48000, framerate), 0)
        self.assertEqual(timefuncs.sample_to_frame(0, 44100, framerate), 0)
        self.assertEqual(timefuncs.sample_to_frame(1601, 48000, framerate), 0)
        self.assertEqual(timefuncs.sample_to_frame(1471, 44100, framerate), 0)
        self.assertEqual(timefuncs.sample_to_frame(1602, 48000, framerate), 1)
        self.assertEqual(timefuncs.sample_to_frame(1472, 44100, framerate), 1)
        framerate = Fraction(24, 1)
        self.assertEqual(timefuncs.sample_to_frame(0, 48000, framerate), 0)
        self.assertEqual(timefuncs.sample_to_frame(0, 44100, framerate), 0)
        self.assertEqual(timefuncs.sample_to_frame(1999, 48000, framerate), 0)
        self.assertEqual(timefuncs.sample_to_frame(1837, 44100, framerate), 0)
        self.assertEqual(timefuncs.sample_to_frame(2000, 48000, framerate), 1)
        self.assertEqual(timefuncs.sample_to_frame(1838, 44100, framerate), 1)

    def test_video_pts_and_duration(self):
        framerate = Fraction(30000, 1001)

        ts = timefuncs.video_pts_and_duration(0, framerate)
        self.assertIsInstance(ts, timefuncs.Timestamp)
        self.assertEqual(ts.pts, 0)
        self.assertEqual(ts.duration, 33366666)
        self.assertEqual(ts, timefuncs.Timestamp(0, 33366666))

        ts = timefuncs.video_pts_and_duration(1, framerate)
        self.assertIsInstance(ts, timefuncs.Timestamp)
        self.assertEqual(ts.pts, 33366666)
        self.assertEqual(ts.duration, 33366667)
        self.assertEqual(ts, timefuncs.Timestamp(33366666, 33366667))

        accum = 0
        for frame in range(10000):
            (pts, dur) = timefuncs.video_pts_and_duration(frame, framerate)
            self.assertEqual(pts, accum)
            self.assertEqual(pts,
                timefuncs.frame_to_nanosecond(frame, framerate)
            )
            self.assertIn(dur, (33366666, 33366667))
            accum += dur
            self.assertEqual(accum,
                timefuncs.frame_to_nanosecond(frame + 1, framerate)
            )

        framerate = Fraction(24, 1)
        self.assertEqual(
            timefuncs.video_pts_and_duration(0, framerate),
            (0, 41666666),
        )
        self.assertEqual(
            timefuncs.video_pts_and_duration(1, framerate),
            (41666666, 41666667),
        )
        accum = 0
        for frame in range(10000):
            (pts, dur) = timefuncs.video_pts_and_duration(frame, framerate)
            self.assertEqual(pts, accum)
            self.assertEqual(pts,
                timefuncs.frame_to_nanosecond(frame, framerate)
            )
            self.assertIn(dur, (41666666, 41666667))
            accum += dur
            self.assertEqual(accum,
                timefuncs.frame_to_nanosecond(frame + 1, framerate)
            )

    def test_audio_pts_and_duration(self):
        samplerate = 48000

        ts = timefuncs.audio_pts_and_duration(0, 1, samplerate)
        self.assertIsInstance(ts, timefuncs.Timestamp)
        self.assertEqual(ts.pts, 0)
        self.assertEqual(ts.duration, 20833)
        self.assertEqual(ts, timefuncs.Timestamp(0, 20833))

        self.assertEqual(
            timefuncs.audio_pts_and_duration(0, 1, samplerate),
            (0, 20833),
        )
        self.assertEqual(
            timefuncs.audio_pts_and_duration(1, 2, samplerate),
            (20833, 20833),
        )
        accum = 0
        for i in range(100000):
            (pts, dur) = timefuncs.audio_pts_and_duration(i, i+1, samplerate)
            self.assertEqual(pts, accum)
            self.assertEqual(pts, timefuncs.sample_to_nanosecond(i, samplerate))
            self.assertIn(dur, (20833, 20834))
            accum += dur

        samplerate = 44100
        self.assertEqual(
            timefuncs.audio_pts_and_duration(0, 1, samplerate),
            (0, 22675),
        )
        self.assertEqual(
            timefuncs.audio_pts_and_duration(1, 2, samplerate),
            (22675, 22676),
        )
        accum = 0
        for i in range(100000):
            (pts, dur) = timefuncs.audio_pts_and_duration(i, i+1, samplerate)
            self.assertEqual(pts, accum)
            self.assertEqual(pts, timefuncs.sample_to_nanosecond(i, samplerate))
            self.assertIn(dur, (22675, 22676))
            accum += dur

    def test_audio_pts_and_duration2(self):
        rate = 48000
        count = rate * 10
        accum = 0
        offset = 0
        for i in range(2000):
            s = random_start_stop(count)
            samples = s.stop - s.start

            # The slice
            (pts, dur) = timefuncs.audio_pts_and_duration(
                    s.start, s.stop, rate)

            # Global position and duration in the edit
            (g_pts, g_dur) = timefuncs.audio_pts_and_duration(
                    offset, offset + samples, rate)

            self.assertEqual(g_pts, accum)
            self.assertLessEqual(abs(g_dur - dur), 1)
            accum += g_dur
            offset += samples

