#!/usr/bin/python

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

from os import path
import json

from dc3lib.microfiber import Database, random_id
from novacut2.renderer import Renderer
from novacut2.builder import LiveBuilder

tree = path.dirname(path.abspath(__file__))


sample1 = 'VQIXPULW3G77W4XLGROMEDGFAH2XJBN4SAVFUGOZRFSIVU7N'
sample2 = 'W62OZLFQUSKE4K6SLJWJ4EHFDUTRLD7JKQXUQMDJSSUG6TAQ'


docs = [
    {
        '_id': sample1,
        'type': 'dmedia/file',
        'framerate': {'num': 25, 'denom': 1},
        'samplerate': 48000,
    },
]


def make_slice(start):
    return {
        '_id': random_id(),
        'type': 'novacut/node',
        'node': {
            'src': sample1,
            'type': 'slice',
            'stream': 'video',
            'start': {'frame': start},
            'stop': {'frame': start + 1},
        },
    }


frame = 200
slices = []
for loop in range(4):
    for i in range(45):
        frame += 1
        doc = make_slice(frame)
        docs.append(doc)
        slices.append(doc['_id'])
    for i in range(20):
        frame -= 1
        doc = make_slice(frame)
        docs.append(doc)
        slices.append(doc['_id'])


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


render = {
    '_id': random_id(),
    'type': 'novacut/render',
    'node': {
        'src': sequence_id,
        'muxer': {'name': 'oggmux'},
        'video': {
            'encoder': {
                'name': 'theoraenc',
                'props': {
                    'quality': 52,
                },
            },
            'filter': {
                'mime': 'video/x-raw-yuv',
                'caps': {
                    'width': 1280,
                    'height': 720,
                },
            },
        },
    }
}
docs.append(render)


project_id = random_id()
b = LiveBuilder(project_id)
b.db.ensure()
b.db.bulksave(docs)


r = Renderer(render['node'], b, path.join(tree, 'tmp-demo.ogv'))
r.run()

docs.reverse()
fp = open(path.join(tree, 'tmp-demo.json'), 'wb')
json.dump(docs, fp, sort_keys=True, indent=4)
print(len(docs))

print(project_id)
print(sequence_id)
