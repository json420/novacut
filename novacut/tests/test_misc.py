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
Unit tests for the `novacut.misc` module.
"""

from unittest import TestCase

from .. import misc


class TestFunctions(TestCase):
    def test_random_slice(self):
        for i in range(100):
            s = misc.random_slice(1)
            self.assertEqual(s, (0, 1))
            self.assertIsInstance(s, misc.Slice)
            self.assertEqual(s.start, 0)
            self.assertEqual(s.stop, 1)
        for count in range(1, 10000):
            s = misc.random_slice(count)
            self.assertIsInstance(s, misc.Slice)
            self.assertEqual(s, (s.start, s.stop))
            self.assertLessEqual(0, s.start)
            self.assertLess(s.start, s.stop)
            self.assertLessEqual(s.stop, count)
            # Just so the above is clearer:
            assert 0 <= s.start < s.stop <= count

    def test_random_start_stop(self):
        for i in range(100):
            (start, stop) = misc.random_start_stop(1)
            self.assertEqual(start, 0)
            self.assertEqual(stop, 1)
        for count in range(1, 1000):
            (start, stop) = misc.random_start_stop(count)
            self.assertGreaterEqual(start, 0)
            self.assertLess(start, stop)
            self.assertLessEqual(stop, count)
            # Just so the above is clearer:
            self.assertTrue(0 <= start < stop <= count)
        for i in range(1000):
            (start, stop) = misc.random_start_stop()
            self.assertGreaterEqual(start, 0)
            self.assertLess(start, stop)
            self.assertLessEqual(stop, 123456)
            # Just so the above is clearer:
            self.assertTrue(0 <= start < stop <= 123456)

