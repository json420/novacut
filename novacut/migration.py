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

from .mapper import get_fraction
from .timefuncs import frame_to_sample
from . import schema


def remove_unneeded(doc):
    for key in ('ver', 'session_id'):
        try:
            del doc[key]
        except Exception:
            pass


def migrate_slice(db, doc):
    assert doc['type'] == 'novacut/node'
    node = doc['node']
    assert node['type'] == 'slice'
    assert node['stream'] in ('video', 'both')
    start = node['start']['frame']
    stop = node['stop']['frame']

    video = deepcopy(doc)
    video['audio'] = []
    del video['node']['stream']
    video['node']['type'] = 'video/slice'
    video['node']['start'] = start
    video['node']['stop'] = stop
    remove_unneeded(video)

    if node['stream'] == 'both':
        clip = db.get(node['src'])
        framerate = get_fraction(clip['framerate'])
        samplerate = clip['samplerate']
        audio = schema.create_audio_slice(node['src'],
            frame_to_sample(start, framerate, samplerate),
            frame_to_sample(stop, framerate, samplerate),
        )
        video['audio'].append(
            {'offset': 0, 'id': audio['_id']}
        )
        schema.check_audio_slice(audio)
        yield audio

    schema.check_video_slice(video)
    yield video


def migrate_sequence(db, doc):
    assert doc['type'] == 'novacut/node'
    node = doc['node']
    assert node['type'] == 'sequence'
    new = deepcopy(doc)
    new['node']['type'] = 'video/sequence'
    new['audio'] = []
    remove_unneeded(new)
    yield new


def migrate_db(db):
    for row in db.get('_all_docs', endkey='_')['rows']:
        _id = row['id']
        doc = db.get(_id)
        if not doc.get('type') == 'novacut/node':
            continue
        node = doc.get('node')
        if not isinstance(node, dict):
            continue
        type_ = node.get('type')
        if type_ == 'slice':
            for new in migrate_slice(db, doc):
                yield new
        elif type_ == 'sequence':
            for new in migrate_sequence(db, doc):
                yield new

