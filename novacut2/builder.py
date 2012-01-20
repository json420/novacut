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

import json
import time

import dbus
from dc3lib.microfiber import Database, NotFound, random_id

from renderer import Builder


VER = 0
session = dbus.SessionBus()


def project_db_name(_id):
    """
    Return the CouchDB database name for the project with *_id*.

    For example:

    >>> project_db_name('HB6YSCKAY27KIWUTWKGKCTNI')
    'novacut-0-hb6ysckay27kiwutwkgkctni'

    """
    return '-'.join(['novacut', str(VER), _id.lower()])


def create_project(title=''):
    _id = random_id()
    ts = time.time()
    return {
        '_id': _id,
        'ver': VER,
        'type': 'novacut/project',
        'time': ts,
        'atime': ts,
        'db_name': project_db_name(_id),
        'title': title,
    }



class LiveBuilder(Builder):
    def __init__(self):
        self.Dmedia = session.get_object('org.freedesktop.Dmedia', '/')
        env = json.loads(self.Dmedia.GetEnv())
        env['url'] = env['url'].encode('utf-8')
        self.db = Database('novacut-0', env)
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
