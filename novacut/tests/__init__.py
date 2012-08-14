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
Unit tests for the `novacut` package.
"""

from unittest import TestCase
import os
from os import path
import logging

from .base import TempHome

import novacut


class TestFunctions(TestCase):
    def test_configure_logging(self):
        tmp = TempHome()
        cache = tmp.join('.cache', 'novacut')
        self.assertFalse(path.isdir(cache))
        log = novacut.configure_logging()
        self.assertIsInstance(log, logging.RootLogger)
        self.assertTrue(path.isdir(cache))
        self.assertEqual(os.listdir(cache), ['setup.py.log'])
        self.assertTrue(path.isfile(path.join(cache, 'setup.py.log')))
