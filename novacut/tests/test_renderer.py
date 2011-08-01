# novacut: the collaborative video editor
# Copyright (C) 2011 Novacut Inc
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

from novacut import renderer

import gst


class TestFunctions(TestCase):
    def test_build_slice(self):
        doc = {
            'framerate': {'numerator': 25, 'denominator': 1},
            'node': {
                'start': {'frame': 200},
                'stop': {'frame': 300},
            },
        }
        element = renderer.build_slice(doc)
        self.assertIsInstance(element, gst.Element)
        self.assertEqual(element.get_factory().get_name(), 'gnlfilesource')
        self.assertEqual(element.get_property('media-start'), 8 * gst.SECOND)
        self.assertEqual(element.get_property('media-duration'), 4 * gst.SECOND)
        self.assertEqual(element.get_property('duration'), 4 * gst.SECOND)
