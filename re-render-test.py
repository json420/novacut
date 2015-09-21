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
import sys
from os import path
import argparse
import logging

from gi.repository import GLib
from dmedia.service import get_proxy
from microfiber import Database

from novacut.settings import get_default_settings
from novacut.render import Renderer
from novacut.validate import Validator
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


parser = argparse.ArgumentParser()
parser.add_argument('--default', action='store_true', default=False,
    help='Use default render settings rather than OGG/Theora'
)
parser.add_argument('--low', action='store_true', default=False,
    help='Force resolution to 1280x720'
)
args = parser.parse_args()


tree = path.dirname(path.abspath(__file__))
tmp = path.join(tree, 'tmp')
Dmedia = get_proxy()
env = json.loads(Dmedia.GetEnv())
db = Database('novacut-1', env)


def get_settings():
    if args.default:
        if args.low:
            return get_default_settings(width=1280, height=720)
        else:
            return get_default_settings()
    return {
        'muxer': 'oggmux',
        'ext': 'ogg',
        'video': {
            'encoder': 'theoraenc',
            'caps': {
                'format': 'I420',
                'width': 960,
                'height': 540,
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
    log.info('on_complete: success=%r', success)
    mainloop.quit()

fail = []

def add_fail(root_id):
    fail.append(root_id)

def render_one(root_id):
    settings = get_settings()
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
        log.error('fatal error in Renderer')
        return add_fail(root_id)
    v = Validator(on_complete, tmp_dst, False, False)
    v.run()
    mainloop.run()
    if v.success is not True:
        log.error('fatal error in Validator')
        return add_fail(root_id)
    expected_frames = sum(s.stop - s.start for s in slices)
    if expected_frames != v.info['frames']:
        log.error('expected %d frames, got %d',
            expected_frames, v.info['frames']
        )
        return add_fail(root_id)
    os.rename(tmp_dst, dst)
    log.info('Result:\n%s\n', dst)


root_ids = []
for r in db.view('doc', 'type', key='novacut/job', include_docs=True)['rows']:
    root_ids.append(r['doc']['node']['root'])
root_ids.sort()

for _id in root_ids:
    render_one(_id)
log.info('Rendered %d edit graphs', len(root_ids))
if fail:
    log.error('Errors on %d renderes', len(fail))
    print('')
    for _id in fail:
        print(_id)
    sys.exit(2)

