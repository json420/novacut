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
from novacut.timefuncs import video_pts_and_duration, audio_pts_and_duration
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

