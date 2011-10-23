#!/usr/bin/python3

import sys
import time
import socket

from microfiber import Database, NotFound, random_id, dc3_env


if len(sys.argv) != 2:
    print('takes exactly one argument DBNAME')
    sys.exit(1)
name = sys.argv[1]
db = Database(name, dc3_env())

db.ensure()
i = 0
while True:
    time.sleep(5)
    doc = {
        '_id': random_id(),
        'time': time.time(),
        'type': 'test',
        'hostname': socket.gethostname(),
        'i': i,
    }
    db.save(doc)
    print(doc)
    i += 1
