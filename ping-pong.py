#!/usr/bin/python3

import sys
import time
import socket
from threading import Thread

from microfiber import Database, random_id, dc3_env


hostname = socket.gethostname()


def monitor_thread(name, env):
    db = Database(name, env)
    last_seq = db.get()['update_seq']
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


def start_thread(target, *args):
    thread = Thread(target=target, args=args)
    thread.daemon = True
    thread.start()
    return thread

env = dc3_env()
db = Database('test', env)
db.ensure()
start_thread(monitor_thread, 'test', env)


while True:
    doc = {
        '_id': random_id(),
        'time': time.time(),
        'type': 'ping',
        'hostname': hostname,
    }
    db.save(doc)
    time.sleep(5)
