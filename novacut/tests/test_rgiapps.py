# novacut: the collaborative video editor
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
Unit tests for the `novacut.rgiapps` module.
"""

from unittest import TestCase
import os
from hashlib import sha1
from random import SystemRandom
from queue import Queue

from dbase32 import random_id
from degu.base import Request, bodies

from .. import rgiapps


random = SystemRandom()


class MockSession:
    def __init__(self):
        self.store = {}


class TestAuthenticationApp(TestCase):
    def test_init(self):
        my_digest = os.urandom(20)

        def my_app(session, request, bodies):
            return (200, 'OK', {}, b'hello, world')

        app = rgiapps.AuthenticationApp(my_digest, my_app)
        self.assertIs(app.digest, my_digest)
        self.assertIs(app.app, my_app)

    def test_call(self):
        my_auth = random_id()
        my_digest = sha1(my_auth.encode()).digest()

        response_body = os.urandom(16)
        def my_app(session, request, bodies):
            return (200, 'OK', {}, response_body)

        app = rgiapps.AuthenticationApp(my_digest, my_app)

        # No authorization header:
        session = MockSession()
        request = Request('GET', '/', {}, None, [], [], None)
        self.assertEqual(app(session, request, bodies),
            (401, 'Unauthorized', {}, None)
        )
        self.assertEqual(session.store, {})

        # Bad authorization header:
        headers = {'authorization': random_id()}
        request = Request('GET', '/', headers, None, [], [], None)
        self.assertEqual(app(session, request, bodies),
            (401, 'Unauthorized', {}, None)
        )
        self.assertEqual(session.store, {})

        # Good authorization header:
        headers = {'authorization': my_auth}
        request = Request('GET', '/', headers, None, [], [], None)
        self.assertEqual(app(session, request, bodies),
            (200, 'OK', {}, response_body)
        )
        self.assertEqual(session.store, {'authenticated': True})
        self.assertIs(session.store['authenticated'], True)

        # No authorization header, but session is already authenticated:
        request = Request('GET', '/', {}, None, [], [], None)
        self.assertEqual(app(session, request, bodies),
            (200, 'OK', {}, response_body)
        )
        self.assertEqual(session.store, {'authenticated': True})
        self.assertIs(session.store['authenticated'], True)


class TestThumbnailerApp(TestCase):
    def test_init(self):
        def request_thumbnail(q, file_id, frame):
            pass

        app = rgiapps.ThumbnailerApp(request_thumbnail)
        self.assertIs(app.request_thumbnail, request_thumbnail)

    def test_call(self):
        class RequestThumbnail:
            def __init__(self, item):
                self._item = item
                self._calls = []

            def __call__(self, q, file_id, frame):
                self._calls.append((q, file_id, frame))
                q.put(self._item)

        file_id = random_id(30)
        frame = random.randrange(1234567890)
        url = '/{}/{}'.format(file_id, frame)

        def get_path():
            return [file_id, str(frame)]

        request_thumbnail = RequestThumbnail(None)
        app = rgiapps.ThumbnailerApp(request_thumbnail)
        session = MockSession()
        for method in ('HEAD', 'PUT', 'POST', 'DELETE'):
            request = Request(method, url, {}, None, [], get_path(), None)
            self.assertEqual(app(session, request, bodies),
                (405, 'Method Not Allowed', {}, None)
            )
            self.assertEqual(session.store, {})
            self.assertEqual(request_thumbnail._calls, [])

        request = Request('GET', url, {}, None, [], get_path(), None)
        self.assertEqual(app(session, request, bodies),
            (404, 'Not Found', {}, None)
        )
        self.assertEqual(set(session.store), {'queue'})
        q = session.store['queue']
        self.assertIsInstance(q, Queue)
        self.assertEqual(request_thumbnail._calls, [(q, file_id, frame)])

        self.assertEqual(app(session, request, bodies),
            (404, 'Not Found', {}, None)
        )
        self.assertEqual(set(session.store), {'queue'})
        self.assertIs(session.store['queue'], q)
        self.assertEqual(request_thumbnail._calls,
            [(q, file_id, frame), (q, file_id, frame)]
        )

        img = rgiapps.Image(random_id(), os.urandom(69))
        request_thumbnail = RequestThumbnail(img)
        app = rgiapps.ThumbnailerApp(request_thumbnail)
        session = MockSession()
        for method in ('HEAD', 'PUT', 'POST', 'DELETE'):
            request = Request(method, url, {}, None, [], get_path(), None)
            self.assertEqual(app(session, request, bodies),
                (405, 'Method Not Allowed', {}, None)
            )
            self.assertEqual(session.store, {})
            self.assertEqual(request_thumbnail._calls, [])

        request = Request('GET', url, {}, None, [], get_path(), None)
        self.assertEqual(app(session, request, bodies),
            (200, 'OK', {'content-type': img.content_type}, img.data)
        )
        self.assertEqual(set(session.store), {'queue'})
        q = session.store['queue']
        self.assertIsInstance(q, Queue)
        self.assertEqual(request_thumbnail._calls, [(q, file_id, frame)])

        self.assertEqual(app(session, request, bodies),
            (200, 'OK', {'content-type': img.content_type}, img.data)
        )
        self.assertEqual(set(session.store), {'queue'})
        self.assertIs(session.store['queue'], q)
        self.assertEqual(request_thumbnail._calls,
            [(q, file_id, frame), (q, file_id, frame)]
        )

