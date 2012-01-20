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
    project.bulksave(docs)
try:
    db.save(p)
except Conflict:
    pass

root = 'AUABDULVRZIBH727GQP2HXSA'
print(schema.save_to_intrinsic(root, project, db))


