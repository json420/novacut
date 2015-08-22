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

from gi.repository import Gst

from .. import validate


class TestValidator(TestCase):
    def test_init(self):
        def callback(inst, success):
            pass

        inst = validate.Validator(callback, '/tmp/whatever.mov')
        self.assertEqual(inst.frame, 0)
        self.assertIsNone(inst.framerate)
        self.assertEqual(inst.info, {'valid': True})
        self.assertIs(inst.full_check, False)

        # Make sure gsthelpers.Pipeline.__init__() was called:
        self.assertIs(inst.callback, callback)
        self.assertIsInstance(inst.pipeline, Gst.Pipeline)
        self.assertIsInstance(inst.bus, Gst.Bus)
        self.assertIsNone(inst.destroy())
        self.assertFalse(hasattr(inst, 'pipeline'))
        self.assertFalse(hasattr(inst, 'bus'))

        inst = validate.Validator(callback, '/tmp/whatever.mov', full_check=True)
        self.assertEqual(inst.frame, 0)
        self.assertIsNone(inst.framerate)
        self.assertEqual(inst.info, {'valid': True})
        self.assertIs(inst.full_check, True)

        # Make sure gsthelpers.Pipeline.__init__() was called:
        self.assertIs(inst.callback, callback)
        self.assertIsInstance(inst.pipeline, Gst.Pipeline)
        self.assertIsInstance(inst.bus, Gst.Bus)
        self.assertIsNone(inst.destroy())
        self.assertFalse(hasattr(inst, 'pipeline'))
        self.assertFalse(hasattr(inst, 'bus'))

