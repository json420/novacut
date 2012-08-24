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
Unit tests for the `novacut.mapper` module.
"""

from unittest import TestCase
from fractions import Fraction

from novacut.misc import random_slice
from novacut.timefuncs import video_pts_and_duration
from novacut import mapper


class TestFunctions(TestCase):
    def test_get_fraction(self):
        self.assertEqual(
            mapper.get_fraction({'num': 30000, 'denom': 1001}),
            Fraction(30000, 1001)
        )
        self.assertEqual(
            mapper.get_fraction([30000, 1001]),
            Fraction(30000, 1001)
        )
        self.assertEqual(
            mapper.get_fraction((30000, 1001)),
            Fraction(30000, 1001)
        )
        self.assertEqual(
            mapper.get_fraction((30000, 1001, True)),
            Fraction(30000, 1001)
        )
        frac = Fraction(24, 1)
        self.assertIs(mapper.get_fraction(frac), frac)
        with self.assertRaises(TypeError) as cm:
            mapper.get_fraction('24/1')
        self.assertEqual(
            str(cm.exception),
            "invalid fraction type <class 'str'>: '24/1'"
        )

    def test_video_slice_to_gnl(self):
        framerate = Fraction(30000, 1001)
        self.assertEqual(
            mapper.video_slice_to_gnl(0, 0, 1, framerate),
            {
                'media-start': 0,
                'media-duration': 33366666,
                'start': 0,
                'duration': 33366666,   
            }
        )
        self.assertEqual(
            mapper.video_slice_to_gnl(0, 1, 2, framerate),
            {
                'media-start': 33366666,
                'media-duration': 33366667,
                'start': 0,
                'duration': 33366666,   
            }
        )
        self.assertEqual(
            mapper.video_slice_to_gnl(1, 0, 1, framerate),
            {
                'media-start': 0,
                'media-duration': 33366666,
                'start': 33366666,
                'duration': 33366667,   
            }
        )

        # Test random slices at different offsets:
        for i in range(10):
            (start, stop) = random_slice(30 * 120)
            frames = stop - start
            self.assertGreaterEqual(frames, 1)
            for offset in range(1000):
                (pts1, dur1) = video_pts_and_duration(
                    start, stop, framerate
                )
                (pts2, dur2) = video_pts_and_duration(
                    offset, offset + frames, framerate
                )
                self.assertEqual(
                    mapper.video_slice_to_gnl(offset, start, stop, framerate),
                    {
                        'media-start': pts1,
                        'media-duration': dur1,
                        'start': pts2,
                        'duration': dur2,   
                    }
                )
                self.assertLessEqual(abs(dur1 - dur2), 1)

        # Test accumulating random slices (as if in a sequence):
        offset = 0
        accum = 0
        for i in range(1000):
            (start, stop) = random_slice(30 * 120)
            frames = stop - start
            self.assertGreaterEqual(frames, 1)
            (pts1, dur1) = video_pts_and_duration(
                start, stop, framerate
            )
            (pts2, dur2) = video_pts_and_duration(
                offset, offset + frames, framerate
            )
            self.assertEqual(
                mapper.video_slice_to_gnl(offset, start, stop, framerate),
                {
                    'media-start': pts1,
                    'media-duration': dur1,
                    'start': pts2,
                    'duration': dur2,   
                }
            )
            self.assertLessEqual(abs(dur1 - dur2), 1)
            self.assertEqual(pts2, accum)
            offset += frames
            accum += dur2
