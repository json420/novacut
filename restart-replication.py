#!/usr/bin/python3

from microfiber import Server, PreconditionFailed, NotFound, dc3_env

authurl = 'https://U4JFH6U3FYI554UU:PGPJDS7QF37XMFWP@novacut.iriscouch.com/'

s = Server(dc3_env())


def restart(doc):
    try:
        rev = s.get('_replicator', doc['_id'])['_rev']
        s.delete('_replicator', doc['_id'], rev=rev)
        print('deleted existing {!r}'.format(doc['_id']))
    except NotFound:
        pass
    s.post(doc, '_replicator')
    print('saved replication {!r}'.format(doc['_id']))


for name in ['novacut', 'dmedia']:
    try:
        s.put(None, name)
    except PreconditionFailed:
        pass
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

