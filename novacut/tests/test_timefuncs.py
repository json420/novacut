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

from novacut import timefuncs


class TestFunctions(TestCase):
    def test_get_fraction(self):
        self.assertEqual(
            timefuncs.get_fraction({'num': 24, 'denom': 1}),
            (24, 1)
        )
        self.assertEqual(
            timefuncs.get_fraction((30000, 1001)),
            (30000, 1001)
        )
        self.assertEqual(
            timefuncs.get_fraction((30000, 1001, True)),
            (30000, 1001)
        )
        with self.assertRaises(TypeError) as cm:
            timefuncs.get_fraction([24, 1])
        self.assertEqual(
            str(cm.exception),
            'value must be a dict or tuple; got [24, 1]'
        )   

    def test_frame_to_nanosecond(self):
        self.assertEqual(
            timefuncs.frame_to_nanosecond(0, {'num': 24, 'denom': 1}),
            0
        )
        self.assertEqual(
            timefuncs.frame_to_nanosecond(0, {'num': 30000, 'denom': 1001}),
            0
        )
        self.assertEqual(
            timefuncs.frame_to_nanosecond(1, {'num': 24, 'denom': 1}),
            41666666
        )
        self.assertEqual(
            timefuncs.frame_to_nanosecond(1, {'num': 30000, 'denom': 1001}),
            33366666
        )
        self.assertEqual(
            timefuncs.frame_to_nanosecond(24, {'num': 24, 'denom': 1}),
            1000000000
        )
        self.assertEqual(
            timefuncs.frame_to_nanosecond(30, {'num': 30000, 'denom': 1001}),
            1001000000
        )

    def test_nanosecond_to_frame(self):
        # nanosecond_to_frame() rounds to the nearest int, so we should be able
        # to round-trip the values
        framerates = [
            {'num': 30000, 'denom': 1001},
            {'num': 24, 'denom': 1},
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
        framerate = {'num': 30000, 'denom': 1001}
        self.assertEqual(timefuncs.frame_to_sample(0, framerate, 48000), 0)
        self.assertEqual(timefuncs.frame_to_sample(0, framerate, 44100), 0)
        self.assertEqual(timefuncs.frame_to_sample(1, framerate, 48000), 1601)
        self.assertEqual(timefuncs.frame_to_sample(1, framerate, 44100), 1471)
        framerate = {'num': 24, 'denom': 1}
        self.assertEqual(timefuncs.frame_to_sample(0, framerate, 48000), 0)
        self.assertEqual(timefuncs.frame_to_sample(0, framerate, 44100), 0)
        self.assertEqual(timefuncs.frame_to_sample(1, framerate, 48000), 2000)
        self.assertEqual(timefuncs.frame_to_sample(1, framerate, 44100), 1837)

    def test_sample_to_frame(self):
        framerate = {'num': 30000, 'denom': 1001}
        self.assertEqual(timefuncs.sample_to_frame(0, 48000, framerate), 0)
        self.assertEqual(timefuncs.sample_to_frame(0, 44100, framerate), 0)
        self.assertEqual(timefuncs.sample_to_frame(1601, 48000, framerate), 0)
        self.assertEqual(timefuncs.sample_to_frame(1471, 44100, framerate), 0)
        self.assertEqual(timefuncs.sample_to_frame(1602, 48000, framerate), 1)
        self.assertEqual(timefuncs.sample_to_frame(1472, 44100, framerate), 1)
        framerate = {'num': 24, 'denom': 1}
        self.assertEqual(timefuncs.sample_to_frame(0, 48000, framerate), 0)
        self.assertEqual(timefuncs.sample_to_frame(0, 44100, framerate), 0)
        self.assertEqual(timefuncs.sample_to_frame(1999, 48000, framerate), 0)
        self.assertEqual(timefuncs.sample_to_frame(1837, 44100, framerate), 0)
        self.assertEqual(timefuncs.sample_to_frame(2000, 48000, framerate), 1)
        self.assertEqual(timefuncs.sample_to_frame(1838, 44100, framerate), 1)

