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

from novacut.schema import random_id
from novacut import renderer

import gst


slice1 = random_id()
slice2 = random_id()
slice3 = random_id()
sequence1 = random_id()
sequence2 = random_id()
docs = [
    {
        '_id': slice1,
        'type': 'novacut/node',
        'framerate': {'num': 25, 'denom': 1},
        'node': {
            'type': 'slice',
            'stream': 'video',
            'start': {'frame': 200},
            'stop': {'frame': 300},
        },
    },

    {
        '_id': slice2,
        'type': 'novacut/node',
        'framerate': {'num': 25, 'denom': 1},
        'node': {
            'type': 'slice',
            'stream': 'video',
            'start': {'frame': 800},
            'stop': {'frame': 875},
        },
    },

    {
        '_id': slice3,
        'type': 'novacut/node',
        'framerate': {'num': 25, 'denom': 1},
        'node': {
            'type': 'slice',
            'stream': 'video',
            'start': {'frame': 40},
            'stop': {'frame': 90},
        },
    },

    {
        '_id': sequence1,
        'type': 'novacut/node',
        'node': {
            'type': 'sequence',
            'src': [
                slice1,
                slice2,
            ],
        },
    },

    {
        '_id': sequence1,
        'type': 'novacut/node',
        'node': {
            'type': 'sequence',
            'src': [
                slice1,
                slice2,
            ],
        },
    },

    {
        '_id': sequence2,
        'type': 'novacut/node',
        'node': {
            'type': 'sequence',
            'src': [
                slice3,
                sequence1,
            ],
        },
    },
]


class DummyBuilder(renderer.Builder):
    def __init__(self, docs):
        self._docmap = dict(
            (doc['_id'], doc) for doc in docs
        )

    def get_doc(self, _id):
        return self._docmap[_id]


class TestFunctions(TestCase):
    def test_build_slice(self):
        doc = {
            'framerate': {'num': 25, 'denom': 1},
            'node': {
                'type': 'slice',
                'stream': 'video',
                'start': {'frame': 200},
                'stop': {'frame': 300},
            },
        }
        element = renderer.build_slice(doc, None)
        self.assertIsInstance(element, gst.Element)
        self.assertEqual(element.get_factory().get_name(), 'gnlfilesource')
        self.assertEqual(element.get_property('media-start'), 8 * gst.SECOND)
        self.assertEqual(element.get_property('media-duration'), 4 * gst.SECOND)
        self.assertEqual(element.get_property('duration'), 4 * gst.SECOND)
        self.assertEqual(
            element.get_property('caps').to_string(),
            'video/x-raw-rgb'
        )

        # Now with audio stream:
        doc['node']['stream'] = 'audio'
        element = renderer.build_slice(doc, None)
        self.assertIsInstance(element, gst.Element)
        self.assertEqual(element.get_factory().get_name(), 'gnlfilesource')
        self.assertEqual(element.get_property('media-start'), 8 * gst.SECOND)
        self.assertEqual(element.get_property('media-duration'), 4 * gst.SECOND)
        self.assertEqual(element.get_property('duration'), 4 * gst.SECOND)
        self.assertEqual(
            element.get_property('caps').to_string(),
            'audio/x-raw-int; audio/x-raw-float'
        )

        # When specified by sample instead:
        doc = {
            'samplerate': 48000,
            'node': {
                'type': 'slice',
                'stream': 'video',
                'start': {'sample': 8 * 48000},
                'stop': {'sample': 12 * 48000},
            },
        }
        element = renderer.build_slice(doc, None)
        self.assertIsInstance(element, gst.Element)
        self.assertEqual(element.get_factory().get_name(), 'gnlfilesource')
        self.assertEqual(element.get_property('media-start'), 8 * gst.SECOND)
        self.assertEqual(element.get_property('media-duration'), 4 * gst.SECOND)
        self.assertEqual(element.get_property('duration'), 4 * gst.SECOND)
        self.assertEqual(
            element.get_property('caps').to_string(),
            'video/x-raw-rgb'
        )

    def test_build_sequence(self):
        b = DummyBuilder(docs)

        element = renderer.build_sequence(b.get_doc(sequence1), b)
        self.assertIsInstance(element, gst.Element)
        self.assertEqual(element.get_factory().get_name(), 'gnlcomposition')
        self.assertEqual(element.get_property('duration'), 7 * gst.SECOND)

        element = b.build(sequence1)
        self.assertIsInstance(element, gst.Element)
        self.assertEqual(element.get_factory().get_name(), 'gnlcomposition')
        self.assertEqual(element.get_property('duration'), 7 * gst.SECOND)

        element = b.build(sequence2)
        self.assertIsInstance(element, gst.Element)
        self.assertEqual(element.get_factory().get_name(), 'gnlcomposition')
        self.assertEqual(element.get_property('duration'), 9 * gst.SECOND)
