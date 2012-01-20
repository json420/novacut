#!/usr/bin/python3

import json
import time
from microfiber import dmedia_env, Database, Conflict
from novacut import schema
from collections import OrderedDict

docs = json.load(open('demo.json', 'r'))
for doc in docs:
    doc['ver'] = 0
    doc['time'] = time.time()


p = {
    '_id': '5A236DNAC6NMS5XIBUMHTY2A',
    'ver': 0,
    'title': '2 Clip Demo',
    'db_name': 'novacut-0-5a236dnac6nms5xibumhty2a',
    'time': 1327022245.45872,
    'atime': 1327022245.45872,
    'type': 'novacut/project',
}

env = dmedia_env()
db = Database('novacut-0', env)
db.ensure()
project = Database(p['db_name'], env)
if project.ensure():
    project.post(p)
    project.post({'docs': docs}, '_bulk_docs')
try:
    db.save(p)
except Conflict:
    pass
db.post({'docs': docs}, '_bulk_docs')

root = schema.save_to_intrinsic('AUABDULVRZIBH727GQP2HXSA', project, db)
print('root:', root)

node = {
    'muxer': {'name': 'oggmux'},
    'video': {
        'encoder': {
            'name': 'theoraenc',
            'props': {
                'quality': 52,
            },
        },
        'filter': {
            'mime': 'video/x-raw-yuv',
            'caps': {
                'width': 960,
                'height': 540,
            },
        },
    },
}
doc = schema.create_settings(node)
try:
    db.save(doc)
except Conflict:
    pass
print('settings:', doc['_id'])

doc = schema.create_job(root, doc['_id'])
try:
    db.save(doc)
except Conflict:
    pass
print('job:', doc['_id'])


