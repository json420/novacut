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

from gi.repository import Gst
from dbase32 import random_id

from .. import validate


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
                self.assertIsInstance(inst.q, Gst.Element)
                self.assertEqual(inst.q.get_factory().get_name(), 'queue')
                self.assertIsInstance(inst.sink, Gst.Element)
                self.assertEqual(inst.sink.get_factory().get_name(), 'fakesink')
                self.assertIs(inst.sink.get_property('signal-handoffs'), True)
                for child in [inst.src, inst.dec, inst.q, inst.sink]:
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


