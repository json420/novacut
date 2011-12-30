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
Unit tests for the `novacut.schema` module.
"""

from unittest import TestCase

from microfiber import random_id

from novacut import schema


class TestFunctions(TestCase):
    def test_project_db_name(self):
        self.assertEqual(
            schema.project_db_name('AAAAAAAAAAAAAAAAAAAAAAAA'),
            'novacut-aaaaaaaaaaaaaaaaaaaaaaaa',
        )
        _id = random_id()
        self.assertEqual(
            schema.project_db_name(_id),
            'novacut-{}'.format(_id.lower())
        )
