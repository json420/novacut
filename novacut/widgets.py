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

from gi.repository import GObject, Gtk, Gdk, WebKit
from microfiber import _oauth_header, _basic_auth_header


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


class Inspector(Gtk.VBox):
    def __init__(self, env):
        super().__init__()

        hbox = Gtk.HBox()
        self.pack_start(hbox, False, False, 1)

        close = Gtk.Button(stock=Gtk.STOCK_CLOSE)
        hbox.pack_end(close, False, False, 1)
        close.connect('clicked', self.on_close)

        scroll = Gtk.ScrolledWindow()
        self.pack_start(scroll, True, True, 0)
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.view = CouchView(env)
        scroll.add(self.view)

    def on_close(self, button):
        self.destroy()
        


