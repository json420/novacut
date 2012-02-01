#!/usr/bin/python3

import sys
import os
from os import path
import shutil
from subprocess import check_call
import json
import tempfile
from base64 import b64encode

from microfiber import Database, NotFound
import dbus
from dmedia.units import bytes10
from novacut import schema


def pipeline(*elements):
    p = ['gst-launch-0.10']
    for el in elements:
        if len(p) > 1:
            p.append('!')
        p.extend(el)
    check_call(p)

def thumbnails_pipeline(src, dst):
    pipeline(
        ['filesrc', 'location={}'.format(src)],
        ['decodebin2'],
        ['queue'],
        ['ffvideoscale', 'method=10'],
        ['video/x-raw-yuv,height=126'], # 126 or 108
        ['queue'],
        ['jpegenc', 'quality=90'],
        ['multifilesink', 'location={}'.format(dst)]
    )

session = dbus.SessionBus()
Dmedia = session.get_object('org.freedesktop.Dmedia', '/')
db = Database('thumbnails', json.loads(Dmedia.GetEnv()))
db.ensure()

_id = sys.argv[1]
src = Dmedia.Resolve(_id)

tmp = tempfile.mkdtemp()
dst = path.join(tmp, '%d')
thumbnails_pipeline(src, dst)


att = {}
count = len(os.listdir(tmp))
for i in range(count):
    fp = open(path.join(tmp, str(i)), 'rb')
    att[i] = {
        'content_type': 'image/jpeg',
        'data': b64encode(fp.read()).decode('utf-8'),
    }

doc = {
    '_id': _id,
    '_attachments': att,
    'count': count,
}
s = schema.normalized_dumps(doc)
print(bytes10(len(s)))
print('')
    

try:
    old = db.get(_id)
    doc['_rev'] = old['_rev']
    db.save(doc)
except NotFound:
    db.save(doc)

shutil.rmtree(tmp)
#db.post(None, '_compact')

    

