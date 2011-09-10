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

"""
Unit tests for the `novacut.widgets` module.
"""

from unittest import TestCase
import os
from base64 import b32encode
from urllib.parse import urlparse
from random import SystemRandom

from novacut import widgets


random = SystemRandom()


def random_key():
    return b32encode(os.urandom(10)).decode('ascii')


def random_oauth():
    return dict(
        (k, random_key())
        for k in ('consumer_key', 'consumer_secret', 'token', 'token_secret')
    )


def random_basic():
    return dict(
        (k, random_key())
        for k in ('username', 'password')
    )


def random_env():
    port = random.randint(2000, 50000)
    return {
        'port': port,
        'url': 'http://localhost:{}/'.format(port),
        'oauth': random_oauth(),
        'basic': random_basic(),
    }


class TestCouchView(TestCase):
    def test_init(self):
        view = widgets.CouchView()
        self.assertIsNone(view._env)
        self.assertIsNone(view._u)
        self.assertIsNone(view._oauth)
        self.assertIsNone(view._basic)
        
        view = widgets.CouchView(None)
        self.assertIsNone(view._env)
        self.assertIsNone(view._u)
        self.assertIsNone(view._oauth)
        self.assertIsNone(view._basic)
        
        env = random_env()
        view = widgets.CouchView(env)
        self.assertIs(view._env, env)
        self.assertEqual(view._u, urlparse(env['url']))
        self.assertEqual(view._oauth, env['oauth'])
        self.assertEqual(view._basic, env['basic'])

    def test_set_env(self):
        view = widgets.CouchView()
        
        env = random_env()
        self.assertIsNone(view._set_env(env))
        self.assertIs(view._env, env)
        self.assertEqual(view._u, urlparse(env['url']))
        self.assertEqual(view._oauth, env['oauth'])
        self.assertEqual(view._basic, env['basic'])

        env = random_env()
        del env['oauth']
        del env['basic']
        self.assertIsNone(view._set_env(env))
        self.assertIs(view._env, env)
        self.assertEqual(view._u, urlparse(env['url']))
        self.assertIsNone(view._oauth)
        self.assertIsNone(view._basic)
        
        self.assertIsNone(view._set_env(None))
        self.assertIsNone(view._env)
        self.assertIsNone(view._u)
        self.assertIsNone(view._oauth)
        self.assertIsNone(view._basic)

    def test_on_request(self):
        # Make sure on_request() immediately returns when env is None:
        view = widgets.CouchView()
        self.assertIsNone(view._env)
        self.assertIsNone(view._on_request(None, None, None, None, None))
        
        

