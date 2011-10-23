#!/usr/bin/python3

from microfiber import Server, NotFound, dc3_env


s = Server(dc3_env())
for name in ['novacut', 'dmedia']:
    for end in ['_from_iris', '_to_iris']:
        _id = name + end
        try:
            rev = s.get('_replicator', _id)['_rev']
            s.delete('_replicator', _id, rev=rev)
            print('deleted existing {!r}'.format(_id))
        except NotFound:
            pass
        
        
