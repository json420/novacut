#!/usr/bin/python3

import sys
from os import path
import json
import optparse
from subprocess import check_output, check_call
import time
import random
from datetime import datetime

import dbus
from microfiber import Database, NotFound

from novacut import schema, views


parser = optparse.OptionParser()
parser.add_option('--slices',
    type='int',
    help='number of slices; default=25',
    metavar='N',
    default=25,
)
parser.add_option('--frames',
    type='int',
    help='max slice length in frames; default=100',
    metavar='MAX',
    default=100,
)
(options, args) = parser.parse_args()


session = dbus.SessionBus()
Dmedia = session.get_object('org.freedesktop.Dmedia', '/')
env = json.loads(Dmedia.GetEnv())
dmedia_0 = Database('dmedia-0', env)
dmedia_0.ensure()
novacut_0 = Database('novacut-0', env)
novacut_0.ensure()

docs = []
slices = []

for row in dmedia_0.view('user', 'video', limit=options.slices)['rows']:
    _id = row['id']
    src = Dmedia.Resolve(_id)
    cmd = ['dmedia-extract', src]
    doc = json.loads(check_output(cmd).decode('utf-8'))
    if doc['framerate'] != {'num': 30000, 'denom': 1001}:
        print('skipping', _id)
    doc.update(
        _id=_id,
        time=time.time(),
        type='dmedia/file',
        ver=0,
    )
    docs.append(doc)


frames = []

for doc in list(docs):
    count = doc['duration']['frames']
    start = random.randint(0, count - 1)
    end = min(count, start + options.frames)
    stop = random.randint(start + 1, end)
    s = schema.create_slice(doc['_id'], {'frame': start}, {'frame': stop})
    slices.append(s['_id'])
    docs.append(s)

    assert 0 <= start < stop <= count
    assert 1 <= (stop - start) <= options.frames
    frames.append((stop - start))

    _id = doc['_id']
    for frame in (start, stop - 1): 
        cmd = ['./novacut-thumbnailer', _id, '--frame', str(frame)]
        print(cmd)
        check_call(cmd)


seq = schema.create_sequence(slices)
docs.append(seq)


project = schema.create_project('Random, ' + datetime.now().strftime('%a %H:%M'))
project_db = Database(project['db_name'], env)

novacut_0.post(project)
assert project_db.ensure() is True
project['root_id'] = seq['_id']
project_db.post(project)
project_db.post({'docs': docs}, '_bulk_docs')

print('project_id:', project['_id'])
print('sequence_id:', seq['_id'])
