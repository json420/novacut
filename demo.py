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

from novacut.renderer import Renderer
from novacut.tests.test_renderer import DummyBuilder, docs, sequence3

b = DummyBuilder(docs)

job = {
    'src': sequence3,
    'muxer': {'name': 'oggmux'},
    'video': {
        'encoder': {'name': 'theoraenc'},
        'filter': {
            'mime': 'video/x-raw-yuv',
            'caps': {
                'width': '640',
                'height': '360',
            },
        },
    },
}

r = Renderer(job, b, 'demo.ogv')
r.run()
