#!/usr/bin/python3

import sys
import time

from microfiber import Database, NotFound, dc3_env


if len(sys.argv) != 2:
    print('takes exactly one argument DBNAME')
    sys.exit(1)
name = sys.argv[1]
db = Database(name, dc3_env())

db.ensure()
try:
    doc = db.get('foo')
except NotFound:
    doc = {'_id': 'foo'}
    db.save(doc)
i = 0
while True:
    time.sleep(5)
    doc['i'] = i
    db.save(doc)
    print(doc)
    i += 1
