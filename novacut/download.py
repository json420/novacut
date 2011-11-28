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
Temporary hack to download the demo assets so people can play with the demo.
"""

import os
import tempfile
from hashlib import md5

from dmedia.client import HTTPClient
from microfiber import Database, dc3_env, NotFound
from filestore import _start_thread

from gi.repository import GObject

GObject.threads_init()

class Downloader:
    def __init__(self):
        self.client = HTTPClient('http://cdn.novacut.com/')

    def do_download(self):
        response = self.client.request('GET', 'novacut.json')
        data = response.read()
        if md5(data).hexdigest() != '440ddef5c14d648fd998218ce679d47b':
            raise Exception('bad checksum')
        return data

    def download(self):
        for retry in range(3):
            try:
                return self.do_download()
            except Exception:
                pass
        raise Exception('could not download')

    def run(self):
        data = self.download()
        (fileno, filename) = tempfile.mkstemp()
        tmp_fp = open(filename, 'wb')
        os.close(fileno)
        tmp_fp.write(data)
        tmp_fp.close()
        tmp_fp = open(tmp_fp.name, 'rb')
        db = Database('novacut', dc3_env())
        try:
            db.delete()
        except NotFound:
            pass
        db.put(None)
        db.load(tmp_fp)


mainloop = GObject.MainLoop()

def done(success):
    print('done', success)
    mainloop.quit()


def download():
    try:
        d = Downloader()
        d.run()
        success = True
    except Exception:
        success = False
    GObject.idle_add(done, success)


_start_thread(download)

mainloop.run()

