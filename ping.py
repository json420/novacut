#!/usr/bin/python3

import sys
import time
import socket

from microfiber import Database, NotFound, random_id, dc3_env

db = Database('test', dc3_env())
db.ensure()

hostname = socket.gethostname()

while True:
    doc = {
        '_id': random_id(),
        'time': time.time(),
        'type': 'ping',
        'hostname': hostname,
    }
    db.save(doc)
    print(doc)
    time.sleep(5)
