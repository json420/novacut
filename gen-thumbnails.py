#!/usr/bin/python3

import sys
import os
from os import path
import shutil
from subprocess import check_call
import json
import tempfile

from microfiber import Database, NotFound
import dbus


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
        ['video/x-raw-yuv,height=108'], # 126
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

try:
    doc = db.get(_id)
    db.delete(_id, rev=doc['_rev'])
except NotFound:
    pass

rev = None
for i in sorted(os.listdir(tmp)):
    fp = open(path.join(tmp, i), 'rb')
    if rev is None:
        rev = db.put_att('image/jpeg', fp, _id, i)['rev']
    else:
        rev = db.put_att('image/jpeg', fp, _id, i, rev=rev)['rev']

shutil.rmtree(tmp)
db.post(None, '_compact')

    

