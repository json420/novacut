#!/usr/bin/python3

import sys
import json
import time
import socket

from microfiber import Database, dc3_env, random_id


hostname = socket.gethostname()

db = Database('test', dc3_env())
db.ensure()

last_seq = db.get()['update_seq']
print('[monitoring changes from update_seq {}]'.format(last_seq))
print('')

while True:
    r = db.get('_changes',
        include_docs=True,
        feed='longpoll',
        since=last_seq,
    )
    if last_seq != r['last_seq']:
        last_seq = r['last_seq']
        for row in r['results']:
            doc = row['doc']
            if doc['type'] == 'ping':
                pong = {
                    '_id': random_id(),
                    'type': 'pong',
                    'hostname': hostname,
                    'orig_hostname': doc['hostname'],
                    'orig_time': doc['time']
                }
                db.save(pong)
            if doc['type'] == 'pong' and doc['orig_hostname'] == hostname:
                latency = time.time() - doc['orig_time']
                print('{:.3f}  {}'.format(latency, doc['hostname']))

