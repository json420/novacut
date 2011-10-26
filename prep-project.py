import json
import time

from microfiber import Database, NotFound, random_id, dc3_env

from novacut import schema

framerate = {
    'num': 25,
    'denom': 1,
}

clips = [
    ('subway', 246),
    ('trolly_day', 370),
    ('trolly', 500),
    ('bus', 290),
]

docs = []



slice_ids = []

for (_id, frames) in clips:
    doc = {
        '_id': _id,
        'type': 'dmedia/file',
        'time': time.time(),
        'duration': {
            'frames': frames,
        },
        'framerate': framerate,
    }
    docs.append(doc)

    doc = schema.create_slice(_id, {'frame': 0}, {'frame': frames})
    slice_ids.append(doc['_id'])
    docs.append(doc)

docs.append(schema.create_sequence(slice_ids))


db = Database('project', dc3_env())
db.ensure()
db.bulksave(docs)

print(json.dumps(docs, sort_keys=True, indent=4))

        

