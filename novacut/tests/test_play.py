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
import queue

from dbase32 import random_id

from .. import play


class TestVideoSink(TestCase):
    def test_init(self):
        def callback(obj, success):
            pass
        buffer_queue = queue.Queue(16)
        xid = random_id()

        inst = play.VideoSink(callback, buffer_queue, xid)
        self.assertIs(inst.buffer_queue, buffer_queue)
        self.assertIs(inst.xid, xid)
        
