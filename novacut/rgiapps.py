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
Degu RGI server applications.
"""

from hashlib import sha1
from queue import Queue
from collections import namedtuple

from dbase32 import check_db32


Image = namedtuple('Image', 'content_type data')


class AuthenticationApp:
    __slots__ = ('digest', 'app')

    def __init__(self, digest, app):
        self.digest = digest
        self.app = app

    def __call__(self, session, request, bodies):
        if session.store.get('authenticated') is not True:
            auth = request.headers.get('authorization')
            if auth is None or sha1(auth.encode()).digest() != self.digest:
                return (401, 'Unauthorized', {}, None)
            session.store['authenticated'] = True
        return self.app(session, request, bodies)


class ThumbnailerApp:
    __slots__ = ('request_thumbnail',)

    def __init__(self, request_thumbnail):
        assert callable(request_thumbnail)
        self.request_thumbnail = request_thumbnail

    def __call__(self, session, request, bodies):
        if request.method != 'GET':
            return (405, 'Method Not Allowed', {}, None)
        (file_id, frame) = request.path
        check_db32(file_id)
        frame = int(frame)
        if frame < 0:
            raise ValueError('need frame >= 0, got {!r}'.format(frame))
        q = session.store.get('queue')
        if q is None:
            q = Queue()
            session.store['queue'] = q
        self.request_thumbnail(q, file_id, frame)
        img = q.get()
        if img is None:
            return (404, 'Not Found', {}, None)
        return (200, 'OK', {'content-type': img.content_type}, img.data)

