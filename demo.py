#!/usr/bin/env python

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

from novacut.schema import random_id
from novacut.renderer import Renderer
from novacut.tests.test_renderer import DummyBuilder, sample1, sample2

docs = [
    {
        '_id': sample1,
        'type': 'dmedia/file',
        'framerate': {'num': 25, 'denom': 1},
        'samplerate': 48000,
    },

    {
        '_id': sample2,
        'type': 'dmedia/file',
        'framerate': {'num': 25, 'denom': 1},
        'samplerate': 48000,
    },
]

start_frames = {
    sample1: 180,
    sample2: 68,
}


slices = []
offset = 0
for dur in (50, 38, 25, 15):
    for src in (sample2, sample1):
        origin = start_frames[src]
        _id = random_id()
        doc = {
            '_id': _id,
            'type': 'novacut/node',
            'node': {
                'src': src,
                'type': 'slice',
                'stream': 'video',
                'start': {'frame': origin + offset},
                'stop': {'frame': origin + offset + dur},
            },
        }
        slices.append(_id)
        docs.append(doc)
        offset += dur


sequence_id = random_id()
docs.append(
    {
        '_id': sequence_id,
        'type': 'novacut/node',
        'node': {
            'type': 'sequence',
            'src': slices,
        },
    }
)



job = {
    'src': sequence_id,
    'muxer': {'name': 'oggmux'},
    'video': {
        'encoder': {
            'name': 'theoraenc',
            'props': {
                'quality': 44,
            },
        },
        'filter': {
            'mime': 'video/x-raw-yuv',
            'caps': {
                'width': '960',
                'height': '540',
            },
        },
    },
}


b = DummyBuilder(docs)
r = Renderer(job, b, 'tmp-demo.ogv')
r.run()
