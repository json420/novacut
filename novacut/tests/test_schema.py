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
    def test_intrinsic_node(self):
        node = {
            'src': 'VQIXPULW3G77W4XLGROMEDGFAH2XJBN4SAVFUGOZRFSIVU7N',
            'type': 'slice',
            'stream': 'video',
            'start': {
                'frame': 200,
            },
            'stop': {
                'frame': 245,
            },
        }
        data = schema.normalized_dumps(node)
        t = schema.intrinsic_node(node)
        self.assertIsInstance(t, schema.Intrinsic)
        self.assertEqual(t.id, schema.hash_node(data))
        self.assertEqual(t.data, data)
        self.assertIs(t.node, node)
        self.assertEqual(schema.normalized_dumps(t.node), data)

    def test_intrinsic_src(self):
        _id = random_id(30)
        self.assertEqual(
            schema.intrinsic_src(_id, None, None),
            _id
        )

        _id = random_id(30)
        src = {'id': _id, 'foo': 'bar'}
        self.assertEqual(
            schema.intrinsic_src(src, None, None),
            {'id': _id, 'foo': 'bar'}
        )

    def test_project_db_name(self):
        self.assertEqual(
            schema.project_db_name('AAAAAAAAAAAAAAAAAAAAAAAA'),
            'novacut-0-aaaaaaaaaaaaaaaaaaaaaaaa',
        )
        _id = random_id()
        self.assertEqual(
            schema.project_db_name(_id),
            'novacut-0-{}'.format(_id.lower())
        )

    def test_create_project(self):
        doc = schema.create_project()
        schema.check_project(doc)
        self.assertEqual(doc['title'], '')

        doc = schema.create_project(title='Hobo Spaceship')
        schema.check_project(doc)
        self.assertEqual(doc['title'], 'Hobo Spaceship')

    def test_create_slice(self):
        src = random_id()
        doc = schema.create_slice(src, {'frame': 17}, {'frame': 1869})
        schema.check_node(doc)
        schema.check_slice(doc)
        self.assertEqual(doc['node'],
            {
                'type': 'slice',
                'src': src,
                'start': {'frame': 17},
                'stop': {'frame': 1869},
                'stream': 'video',
            }
        )

        src = random_id() 
        doc = schema.create_slice(src, {'sample': 48000}, {'sample': 96000},
            'audio'
        )
        schema.check_node(doc)
        schema.check_slice(doc)
        self.assertEqual(doc['node'],
            {
                'type': 'slice',
                'src': src,
                'start': {'sample': 48000},
                'stop': {'sample': 96000},
                'stream': 'audio',
            }
        )

    def test_create_sequence(self):
        one = random_id()
        two = random_id()
        doc = schema.create_sequence([one, two])
        schema.check_node(doc)
        self.assertEqual(doc['node'],
            {
                'type': 'sequence',
                'src': [one, two],
            }
        )

    def test_iter_src(self):
        src = random_id()
        self.assertEqual(
            list(schema.iter_src(src)),
            [src]
        )

        src = [random_id() for i in range(10)]
        self.assertEqual(
            list(schema.iter_src(src)),
            src
        )

        ids = [random_id() for i in range(10)]
        src = [{'id': _id} for _id in ids]
        self.assertEqual(
            list(schema.iter_src(src)),
            ids
        )


        src = {
            'foo': random_id(),
            'bar': random_id(),
            'baz': random_id(),
        }
        self.assertEqual(
            set(schema.iter_src(src)),
            set(v for v in src.values())
        )
        
        ids = [random_id() for i in range(3)]
        src = {
            'foo': {'id': ids[0]},
            'bar': {'id': ids[1]},
            'baz': {'id': ids[2]},
        }
        self.assertEqual(
            set(schema.iter_src(src)),
            set(ids)
        )
