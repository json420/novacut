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
Unit tests for the `novacut.settings` module.
"""

from unittest import TestCase

from .. import settings


class TestFunctions(TestCase):
    def get_default_settings(self):
        s = settings.get_default_settings()
        self.assertIsInstance(s, dict)
        self.assertIsInstance(s.get('muxer'), (str, dict))
        self.assertIsInstance(s.get('ext'), str)
        self.assertIsInstance(s.get('video'), dict)
        video = s['video']
        self.assertIsInstance(video.get('encoder'), (str, dict))
        self.assertIsInstance(video.get('caps'), dict)
        vcaps = video['caps']
        self.assertEqual(vcaps.get('width'), 1920)
        self.assertEqual(vcaps.get('width'), 1080)
        self.assertIsInstance(s.get('audio'), dict)

        for (w, h) in [(1280, 720), (960, 540), (640, 480)]:
            s = settings.get_default_settings(width=w, height=h)
            self.assertIsInstance(s, dict)
            self.assertIsInstance(s.get('muxer'), (str, dict))
            self.assertIsInstance(s.get('ext'), str)
            self.assertIsInstance(s.get('video'), dict)
            video = s['video']
            self.assertIsInstance(video.get('encoder'), (str, dict))
            self.assertIsInstance(video.get('caps'), dict)
            vcaps = video['caps']
            self.assertEqual(vcaps.get('width'), w)
            self.assertEqual(vcaps.get('width'), h)
            self.assertIsInstance(s.get('audio'), dict) 

