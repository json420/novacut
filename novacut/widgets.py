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
Custom Gtk3 widgets.
"""

from urllib.parse import urlparse, parse_qsl
import json

from gi.repository import GObject, Gtk, WebKit
from microfiber import Database, _oauth_header, _basic_auth_header

from . import dbus


BUS = 'org.freedesktop.DC3'
IFACE = BUS

html = """<!DOCTYPE html>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<style type="text/css">
body {
    font-family: Ubuntu;
    font-size: 24px;
    background-color: #301438;
    color: #e81f3b;
}
</style>
</head>
<body>
Woot
</body>
</html>
"""


class UI(object):
    def __init__(self, benchmark=False):
        self.benchmark = benchmark
        self.window = Gtk.Window()
        self.window.connect('destroy', Gtk.main_quit)
        self.window.set_default_size(960, 540)
        self.window.maximize()

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.ALWAYS, Gtk.PolicyType.ALWAYS)
        self.window.add(self.scroll)

        self.view = CouchView()
        self.scroll.add(self.view)
        self.view.load_string(html, 'text/html', 'UTF-8', 'file:///')

        self.window.show_all()
        GObject.idle_add(self.on_idle)

    def run(self):
        Gtk.main()

    def on_idle(self):
        if self.benchmark:
            Gtk.main_quit()
            return
        dbus.session.get_async(self.on_proxy, 'org.freedesktop.DC3', '/')

    def on_proxy(self, proxy, async_result, *args):
        self.dc3 = proxy
        env = json.loads(self.dc3.GetEnv())
        self.db = Database('novacut', env)
        self.db.ensure()
        self.view._set_env(env)
        uri = self.db._full_url('/_apps/dc3/index.html')
        self.view.load_uri(uri)


class CouchView(WebKit.WebView):
    def __init__(self, env=None):
        super().__init__()
        self.connect('resource-request-starting', self._on_request)
        self._set_env(env)

    def _set_env(self, env):
        self._env = env
        if env is None:
            self._u = None
            self._oauth = None
            self._basic = None
            return
        self._u = urlparse(env['url'])
        self._oauth = env.get('oauth')
        self._basic = env.get('basic')

    def _on_request(self, view, frame, resource, request, response):
        if self._env is None:
            return
        uri = request.get_uri()
        u = urlparse(uri)
        if u.netloc != self._u.netloc:
            return
        if u.scheme != self._u.scheme:
            return
        if self._oauth:
            query = dict(parse_qsl(u.query))
            if u.query and not query:
                query = {u.query: ''}
            baseurl = ''.join([u.scheme, '://', u.netloc, u.path])
            method = request.props.message.props.method
            h = _oauth_header(self._oauth, method, baseurl, query)
        elif self._basic:
            h = _basic_auth_header(self._basic)
        else:
            return
        for (key, value) in h.items():
            request.props.message.props.request_headers.append(key, value)


