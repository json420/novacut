#!/usr/bin/env python3

# novacut: the distributed video editor
# Copyright (C) 2011-2015 Novacut Inc
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
Script to re-render all existing jobs in novacut-1 Database.
"""

import json
import os
from os import path
import logging

from gi.repository import GLib
from dmedia.service import get_proxy
from microfiber import Database

from novacut.render import Renderer
from novacut.settings import get_default_settings
from novacut.renderservice import get_slices


logging.basicConfig(
    level=logging.DEBUG,
    format='\t'.join([
        '%(levelname)s',
        '%(threadName)s',
        '%(message)s',
    ]),
)
log = logging.getLogger(__name__)


tree = path.dirname(path.abspath(__file__))
tmp = path.join(tree, 'tmp')
Dmedia = get_proxy()
env = json.loads(Dmedia.GetEnv())
db = Database('novacut-1', env)


def get_settings():
    return {
        'muxer': 'oggmux',
        'ext': 'ogg',
        'video': {
            'encoder': 'theoraenc',
            'caps': {
                'format': 'I420',
                'width': 1920,
                'height': 1080,
                'interlace-mode': 'progressive',
                'pixel-aspect-ratio': '1/1',
                'chroma-site': 'mpeg2',
                'colorimetry': 'bt709',
                'framerate': {'num': 30000, 'denom': 1001},
            },
        },
    }


mainloop = GLib.MainLoop()

def on_complete(r, success):
    log.info('[re-render complete, success=%r]', success)
    mainloop.quit()


def render_one(root_id):
    settings = get_default_settings()
    name = '.'.join([root_id, settings['ext']])
    dst = path.join(tmp, name)
    tmp_dst = path.join(tmp, 'tmp-' + name)
    if path.exists(dst):
        log.info('Already exists: %s', dst)
        return
    if path.exists(tmp_dst):
        log.info('Already in progress: %s', dst)
        return
    log.info('[re-rendering edit graph at root node %s]', root_id)
    log.info(tmp_dst)
    slices = get_slices(Dmedia, db, root_id)
    r = Renderer(on_complete, slices, settings, tmp_dst)
    r.run()
    mainloop.run()
    if r.success is not True:
        raise SystemExit('fatal error in renderer')
    os.rename(tmp_dst, dst)
    log.info('Result:\n%s\n', dst)


for r in db.view('doc', 'type', key='novacut/job', include_docs=True)['rows']:
    root_id = r['doc']['node']['root']
    render_one(root_id)

