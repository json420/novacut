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
Lossless migration between schema versions.
"""

from copy import deepcopy
import re

from dmedia.migration import b32_to_db32

from . import schema


V0_PROJECT_DB = re.compile('^novacut-0-([234567abcdefghijklmnopqrstuvwxyz]{24})$')


def iter_v0_project_dbs(server):
    for name in server.get('_all_dbs'):
        match = V0_PROJECT_DB.match(name)
        if match:
            _id = match.group(1).upper()
            yield (name, _id)


def migrate_project(old):
    assert old['type'] == 'novacut/project'
    v1_id = b32_to_db32(old['_id'])
    new = deepcopy(old)
    new.pop('_rev', None)
    new.pop('ver', None)
    new['_id'] = v1_id
    new['db_name'] = schema.project_db_name(v1_id)
    if 'root_id' in old:
        new['root_id'] = b32_to_db32(old['root_id'])
    return new


def migrate_sequence(old):
    assert old['type'] == 'novacut/node'
    node = old['node']
    assert isinstance(node, dict)
    assert node['type'] == 'sequence'
    src = node['src']
    assert isinstance(src, list)
    doodle = old.get('doodle', [])
    assert isinstance(doodle, list)

    new = {
        '_id': b32_to_db32(old['_id']),
        'type': 'novacut/node',
        'time': old.get('time', 0),
        'node': {
            'type': 'video/sequence',
            'src': [b32_to_db32(src_id) for src_id in src],
        },
        'audio': [],
        'doodle': [],
    }

    for d in doodle:
        if d['id'] == 'shortcuts':
            continue
        new['doodle'].append(
            {'id': b32_to_db32(d['id']), 'x': d.get('x'), 'y': d.get('y')}
        )

    if old.get('selected'):
        new['selected'] = b32_to_db32(old['selected'])
        
    schema.check_video_sequence(new)
    return new


def migrate_slice(old, id_map):
    assert old['type'] == 'novacut/node'
    node = old['node']
    assert node['type'] == 'slice'
    assert node.get('stream', 'video') in ('video', 'both')
    start = node['start']['frame']
    stop = node['stop']['frame']
    src_id = node['src']
    assert isinstance(start, int)
    assert isinstance(stop, int)
    assert 0 <= start <= stop
    assert src_id in id_map

    new = {
        '_id': b32_to_db32(old['_id']),
        'type': 'novacut/node',
        'time': old.get('time', 0),
        'audio': [],
        'node': {
            'type': 'video/slice',
            'src': id_map[src_id],
            'start': start,
            'stop': stop,
        },
    }
    return new


def migrate_dmedia_file(old, id_map):
    assert old['type'] == 'dmedia/file'
    new = deepcopy(old)
    new.pop('_rev', None)
    new['_id'] = id_map[old['_id']]
    return new
