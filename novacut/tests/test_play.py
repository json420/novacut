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
Unit tests for the `novacut.play` module.
"""

from unittest import TestCase
import queue
import sys

from dbase32 import random_id

from .helpers import random_slice
from .. import play


class TestSliceDecoder(TestCase):
    def test_init(self):
        def callback(obj, success):
            pass
        sample_queue = queue.Queue(16)
        s = random_slice()

        inst = play.SliceDecoder(callback, sample_queue, s)
        self.assertIs(inst.sample_queue, sample_queue)
        self.assertIs(inst.s, s)
        self.assertIs(inst.frame, s.start)
        self.assertIs(inst.isprerolled, False)

        self.assertIsNone(inst.destroy())
        self.assertEqual(inst.handlers, [])
        self.assertEqual(sys.getrefcount(inst), 2)


class TestVideoSink(TestCase):
    def test_init(self):
        def callback(obj, success):
            pass
        sample_queue = queue.Queue(16)
        xid = random_id()

        inst = play.VideoSink(callback, sample_queue, xid)
        self.assertIs(inst.sample_queue, sample_queue)
        self.assertIs(inst.xid, xid)

        self.assertIsNone(inst.destroy())
        self.assertEqual(inst.handlers, [])
        self.assertEqual(sys.getrefcount(inst), 2)

