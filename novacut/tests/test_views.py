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
Unit tests for the `novacut.views` module.
"""

from unittest import TestCase

from usercouch.misc import CouchTestCase
from microfiber import Database, random_id
from dmedia import util

from novacut import views


class TestDesignValues(TestCase):
    """
    Do a Python value sanity check on all design docs.

    This is a fast test to make sure all the design docs are well-formed from
    the Python perspective.  But it can't tell you if you have JavaScript syntax
    errors.  For that, there is `TestDesignsLive`.
    """

    def check_design(self, doc):
        self.assertIsInstance(doc, dict)
        self.assertTrue(set(doc).issuperset(['_id', 'views']))
        self.assertTrue(set(doc).issubset(['_id', 'views', 'filters']))

        _id = doc['_id']
        self.assertIsInstance(_id, str)
        self.assertTrue(_id.startswith('_design/'))

        views = doc['views']
        self.assertIsInstance(views, dict)
        self.assertGreater(len(views), 0)
        for (key, value) in views.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(value, dict)
            self.assertTrue(set(value).issuperset(['map']))
            self.assertTrue(set(value).issubset(['map', 'reduce']))
            self.assertIsInstance(value['map'], str)
            if 'reduce' in value:
                self.assertIsInstance(value['reduce'], str)
                self.assertIn(value['reduce'], ['_count', '_sum'])

        if 'filters' not in doc:
            return

        filters = doc['filters']
        self.assertIsInstance(filters, dict)
        self.assertGreater(len(filters), 0)
        for (key, value) in filters.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(value, str)

    def test_novacut_main(self):
        for doc in views.novacut_main:
            self.check_design(doc)

    def test_novacut_projects(self):
        for doc in views.novacut_projects:
            self.check_design(doc)


class TestDesignsLive(CouchTestCase):
    """
    Do a sanity check on all design docs using a live CouchDB.

    This is mostly a check for JavaScript syntax errors, or other things that
    would make a design or view fail immediately.
    """

    def check_views(self, db, doc):
        design = doc['_id'].split('/')[1]
        for view in doc['views']:
            db.view(design, view)
            if 'reduce' in doc['views'][view]:
                db.view(design, view, reduce=True)

    def check_designs(self, designs):
        db = Database('foo', self.env)
        db.put(None)
        ids = [doc['_id'] for doc in designs]
        self.assertEqual(
            util.init_views(db, designs),
            [('new', _id) for _id in ids],
        )

        # Test all designs when database is empty
        for doc in designs:
            self.check_views(db, doc)

        # Add 100 random docs and test all designs again
        for i in range(100):
            db.post({'_id': random_id()})
        for doc in designs:
            self.check_views(db, doc)

    def test_novacut_main(self):
        self.check_designs(views.novacut_main)

    def test_novacut_projects(self):
        self.check_designs(views.novacut_projects)
