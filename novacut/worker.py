# novacut: the distributed video editor
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
Higher level worker that executes a render.
"""

import os
from os import path
import json
from datetime import datetime

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GObject
from microfiber import Database

from .renderer import Builder, Renderer


GObject.threads_init()
DBusGMainLoop(set_as_default=True)
session = dbus.SessionBus()
HOME = path.abspath(os.environ['HOME'])


class LiveBuilder(Builder):
    def __init__(self, Dmedia, db):
        super().__init__()
        self.Dmedia = Dmedia
        self.db = db
        self._cache = {}

    def resolve_file(self, _id):
        return self.Dmedia.Resolve(_id)

    def get_doc(self, _id):
        try:
            return self._cache[_id]
        except KeyError:
            doc = self.db.get(_id)
            self._cache[_id] = doc
            return doc


class Worker:
    def __init__(self):
        self.Dmedia = session.get_object('org.freedesktop.Dmedia', '/')
        env = json.loads(self.Dmedia.GetEnv())
        self.novacut = Database('novacut-0', env)
        self.dmedia = Database('dmedia-0', env)

    def run(self, job_id):
        job = self.novacut.get(job_id)
        root = job['node']['root']
        settings = self.novacut.get(job['node']['settings'])
        builder = LiveBuilder(self.Dmedia, self.novacut)
        dst = self.Dmedia.AllocateTmp()
        renderer = Renderer(root, settings['node'], builder, dst)
        renderer.run()

        obj = self.Dmedia.HashAndMove(dst, 'render')
        _id = obj['file_id']
        doc = self.dmedia.get(_id)
        doc['render_of'] = job_id

        # Create the symlink
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if settings['node'].get('ext'):
            ts += '.' + settings['node']['ext']
        name = path.join('Novacut', ts)
        link = path.join(HOME, name)
        d = path.dirname(link)
        if not path.isdir(d):
            os.mkdir(d)
        target = obj['file_path']
        os.symlink(target, link)
        doc['link'] = name

        self.dmedia.save(doc)
        job['renders'][_id] = {
            'bytes': doc['bytes'],
            'time': doc['time'],
            'link': name,
        }
        self.novacut.save(job)
        
        obj['link'] = name
        return obj
