#!/usr/bin/python3

import sys
import time
import socket
from threading import Thread
from copy import deepcopy

from microfiber import Server, Database, NotFound, random_id, dc3_env


authurl = 'https://U4JFH6U3FYI554UU:PGPJDS7QF37XMFWP@novacut.iriscouch.com/'
hostname = socket.gethostname()
accum = {}


def monitor_thread(name, env):
    db = Database(name, env)
    last_seq = db.get()['update_seq']
    while True:
        r = db.get('_changes',
            include_docs=True,
            feed='longpoll',
            since=last_seq,
        )
        if last_seq == r['last_seq']:
            continue
        last_seq = r['last_seq']
        for row in r['results']:
            doc = row['doc']
            if doc['type'] == 'ping' and doc['hostname'] != hostname:
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
                h = doc['hostname']
                if h not in accum:
                    accum[h] = []
                accum[h].append(latency)
                print('{:.3f}  {}'.format(latency, h))


def start_thread(target, *args):
    thread = Thread(target=target, args=args)
    thread.daemon = True
    thread.start()
    return thread


env = dc3_env()
name = 'test'
db = Database(name, env)
db.ensure()


s = Server(env)


def restart(doc):
    try:
        rev = s.get('_replicator', doc['_id'])['_rev']
        s.delete('_replicator', doc['_id'], rev=rev)
    except NotFound:
        pass
    s.post(doc, '_replicator')


doc = {
    '_id': name + '_from_iris',
    'source': authurl + name,
    'target': name,
    'continuous': True,
}
restart(doc)
doc = {
    '_id': name + '_to_iris',
    'target': authurl + name,
    'source': name,
    'continuous': True,
}
restart(doc)
print('\nGiving Couches 10 seconds to sync before starting...')
time.sleep(10)
print('')

start_thread(monitor_thread, 'test', env)


try:
    while True:
        doc = {
            '_id': random_id(),
            'time': time.time(),
            'type': 'ping',
            'hostname': hostname,
        }
        db.save(doc)
        time.sleep(4)
except KeyboardInterrupt:
    pass


print('\n\nAverages:')
a = deepcopy(accum)
for host in sorted(a):
    times = a[host]
    avg = sum(times) / len(times)
    print('  {:.3f}  {}'.format(avg, host))


for end in ['_from_iris', '_to_iris']:
    _id = name + end
    try:
        rev = s.get('_replicator', _id)['_rev']
        s.delete('_replicator', _id, rev=rev)
    except NotFound:
        pass
        
db.post(None, '_compact')
        

