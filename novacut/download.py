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
import json
import time

from dmedia.client import HTTPClient
from microfiber import Database, dc3_env, NotFound, random_id

from novacut import schema


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


def init_project():
    framerate = {
        'num': 25,
        'denom': 1,
    }

    clips = [
        ('subway', 246),
        ('trolly_day', 370),
        ('trolly', 500),
        ('bus', 290),
    ]

    docs = []
    slice_ids = []

    for (_id, frames) in clips:
        doc = {
            '_id': _id,
            'type': 'dmedia/file',
            'time': time.time(),
            'duration': {
                'frames': frames,
            },
            'framerate': framerate,
        }
        docs.append(doc)

        doc = schema.create_slice(_id, {'frame': 0}, {'frame': frames})
        slice_ids.append(doc['_id'])
        docs.append(doc)

    docs.append(schema.create_sequence(slice_ids))

    db = Database('project', dc3_env())
    try:
        db.delete()
    except NotFound:
        pass
    db.put(None)
    db.bulksave(docs)




