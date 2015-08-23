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
Adds CouchDB and Dmedia integration atop `novacut.render`.
"""

import os
from os import path
from datetime import datetime
import logging

from gi.repository import GLib
from microfiber import Database, dumps

from .render import Slice, Renderer


log = logging.getLogger(__name__)


# MAX_DEPTH of edit graph (to prevent recursive loops within sequences):
MAX_DEPTH = 10

TYPE_ERROR = '{}: need a {!r}; got a {!r}: {!r}'


################################################################################
# Helpers functions for extracting values from CouchDB docs:

def _get(d, key, t):
    assert type(d) is dict
    assert type(key) is str
    val = d.get(key)
    if type(val) is not t:
        raise TypeError(TYPE_ERROR.format(key, t, type(val), val))
    return val


def _get_str(d, key):
    val = _get(d, key, str)
    if not val:
        raise ValueError('str {!r} is empty'.format(key))
    return val


def _get_int(d, key, minval):
    val = _get(d, key, int)
    assert type(minval) is int
    if val < minval:
        raise ValueError(
            'need {!r} >= {}; got {}'.format(key, minval, val)
        )
    return val


def _get_slice(node):
    src = _get_str(node, 'src')
    start = _get_int(node, 'start', 0)
    stop = _get_int(node, 'stop', 0)
    if start > stop:
        raise ValueError(
            'need start <= stop; got {} > {}'.format(start, stop)
        )
    return (src, start, stop)


def _get_sequence(node):
    src = _get(node, 'src', list)
    for (i, item) in enumerate(src):
        if type(item) is not str:
            label = "node['src'][{}]".format(i)
            raise TypeError(
                TYPE_ERROR.format(label, str, type(item), item)
            )
    return src


################################################################################
# Helpers functions for traversing edit graph, resolving files with Dmedia:

def _iter_raw_slices(db, _id, depth):
    assert isinstance(depth, int) and depth >= 0
    if depth > MAX_DEPTH:
        raise ValueError(
            'MAX_DEPTH exceeded: {} > {}'.format(depth, MAX_DEPTH)
        )
    doc = db.get(_id)
    node = _get(doc, 'node', dict)
    ntype = _get_str(node, 'type')
    if ntype == 'video/slice':
        (src, start, stop) = _get_slice(node)
        if start < stop:  # Only yield a non-empty slice
            yield (_id, src, start, stop)
    elif ntype == 'video/sequence':
        for child_id in _get_sequence(node):
            yield from _iter_raw_slices(db, child_id, depth + 1)
    else:
        TypeError('bad node type: {}: {!r}'.format(_id, ntype))


def get_raw_slices(db, root_id):
    return tuple(_iter_raw_slices(db, root_id, 0))


def resolve_files(Dmedia, files):
    _map = {}
    for _id in files:
        (file_id, status, name) = Dmedia.Resolve(_id)
        assert file_id == _id
        assert status in (0, 1, 2)
        if status == 1:
            raise ValueError(
                'File {} not available in local Dmedia stores'.format(_id)
            )
        if status == 2:
            raise ValueError(
                'File {} not in Dmedia library'.format(_id)
            )
        _map[_id] = str(name)
    return _map


def get_slices(Dmedia, db, root_id):
    raw_slices = get_raw_slices(db, root_id)
    files = sorted(set(r[1] for r in raw_slices))
    _map = resolve_files(Dmedia, files)
    return tuple(
        Slice(_id, src, start, stop, _map[src])
        for (_id, src, start, stop) in raw_slices
    )


class Worker:
    def __init__(self, Dmedia, env):
        self.Dmedia = Dmedia
        self.novacut_db = Database('novacut-1', env)
        self.dmedia_db = Database('dmedia-1', env)
        self.mainloop = GLib.MainLoop()

    def on_complete(self, renderer, success):
        log.info('Renderer completed with success=%r', success)
        self.mainloop.quit()

    def run(self, job_id):
        job = self.novacut_db.get(job_id)
        log.info('Rendering: %s', dumps(job, pretty=True))
        settings = self.novacut_db.get(job['node']['settings'])
        log.info('With settings: %s', dumps(settings['node'], pretty=True))

        root_id = job['node']['root']
        slices = get_slices(self.Dmedia, self.novacut_db, root_id)

        dst = self.Dmedia.AllocateTmp()
        renderer = Renderer(self.on_complete, slices, settings['node'], dst)
        renderer.run()
        self.mainloop.run()
        if renderer.success is not True:
            raise SystemExit('renderer encountered a fatal error')
        if path.getsize(dst) < 1:
            raise SystemExit('file-size is zero for {}'.format(job_id))

        obj = self.Dmedia.HashAndMove(dst, 'render')
        _id = obj['file_id']
        doc = self.dmedia_db.get(_id)
        doc['render_of'] = job_id

        # Create the symlink
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if settings['node'].get('ext'):
            ts += '.' + settings['node']['ext']

        home = path.abspath(os.environ['HOME'])
        name = path.join('Novacut', ts)
        link = path.join(home, name)
        d = path.dirname(link)
        if not path.isdir(d):
            os.mkdir(d)
        target = obj['file_path']
        os.symlink(target, link)
        doc['link'] = name

        self.dmedia_db.save(doc)
        job['renders'][_id] = {
            'bytes': doc['bytes'],
            'time': doc['time'],
            'link': name,
        }
        self.novacut_db.save(job)

        obj['link'] = name

        return obj

