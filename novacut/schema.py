# novacut: the collaborative video editor
# Copyright (C) 2011 Novacut Inc
#
# This file is part of `novacut`.
#
# `novacut` is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# `novacut` is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for
# more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with `novacut`.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#   Jason Gerard DeRose <jderose@novacut.com>

"""
Test-driven definition of novacut edit node schema.

UX wise, the schema is perhaps the most important aspect of Novacut.  The schema
must:

    1. Model user intent - the schema must model what the edit means in the
       artist's head, must capture the semantics as clearly as possible; we
       cannot let implementation details leak in here!

    2. Preserve user intent - the schema must preserve use intent in the face of
       changes to nearby elements; basically we're talking about what we call
       relative positioning (what Apple calls "linked clips")

    3. Provide an excellent API for UI developers - because of our simple
       architecture built around CouchDB, the schema *is* the API for
       manipulating edit state


Example of a slice node:

>>> doc = {
...     '_id': '3HHSRSVXT5ZGY2B6LJPN457P',
...     'type': 'novacut/node',
...     'node': {
...         'type': 'slice',
...         'src': 'VYUG4ON2APZK3GEJULB4I7PHJTKZLXTOIRGU2LU2LW7JBOCU',
...         'start': {
...             'frame': 123,
...         },
...         'stop': {
...             'frame': 456,
...         },
...     },
... }


Another slice from of the same clip:

>>> doc = {
...     '_id': 'RXJM24DMCRZ4YS6L6FOPDQRX',
...     'type': 'novacut/node',
...     'node': {
...         'type': 'slice',
...         'src': 'VYUG4ON2APZK3GEJULB4I7PHJTKZLXTOIRGU2LU2LW7JBOCU',
...         'start': {
...             'frame': 1023,
...         },
...         'stop': {
...             'frame': 1776,
...         },
...     },
... }


A sequence with these two slices back-to-back:

>>> doc = {
...     '_id': 'JG444OBNF5JUUNSPCCE5YPIK',
...     'type': 'novacut/node',
...     'node': {
...         'type': 'sequence',
...         'src': [
...             '3HHSRSVXT5ZGY2B6LJPN457P',
...             'RXJM24DMCRZ4YS6L6FOPDQRX',
...         ],
...     },
... }



Design Decision: hashable semantic content
==========================================

The CouchDB document corresponding to each node in the editing graph has two
distinct purposes: unambiguously store the "meaning" of the edit semantically
speaking, and to provide and extensible place to store other metadata, for
example notes, annotations, tags, etc.

The semantic portion of of the edit is stored in a dictionary under the "node"
key.  For example:

>>> doc = {
...     'node': {},
... }

The "node" dictionary only stores semantic information, the data that uniquely
describes that exact node.  This is perhaps easier to explain in terms of what
is *not* stored in "node".  For example, things like timestamps and annotations
aren't stored in "node" because regardless of what time the node was created or
last changed, the meaning of the edit is the same.

This is done so that "node" can be serialized into a standard form and hashed,
giving us a globally unique way to refer to any node in any editing graph.  This
is enormously useful for two reasons:

    1. It gives us an easy unique ID for caching pre-rendered corresponding to
       a specific node (semantically speaking)

    2. It gives us a globally unique way to refer to nodes for the purpose of
       remixing... this is hyper-linking for our cultural heritage, in a
       decentralized yet global namespace


"""

import time
import json
from base64 import b32encode, b64encode
from copy import deepcopy
from collections import namedtuple

from skein import skein512
from microfiber import random_id, RANDOM_B32LEN, Conflict
from dmedia.schema import (
    _label,
    _value,
    _exists,
    _check,
    _check_if_exists,
    _at_least,
    _lowercase,
    _matches,
    _nonempty,
    _is_in,
    _equals,
    _any_id,
    _random_id,
    _intrinsic_id,
)


# schema-compatibility version:
VER = 0

# versioned primary database name:
DB_NAME = 'novacut-{}'.format(VER)

# Skein personalization string
PERS_NODE = b'20120117 jderose@novacut.com novacut/node'
DIGEST_BITS = 240
DIGEST_BYTES = DIGEST_BITS // 8
DIGEST_B32LEN = DIGEST_BITS // 5
Intrinsic = namedtuple('Intrinsic', 'id data node')


def normalized_dumps(obj):
    """
    Return *obj* encoded as normalized JSON, the hashing form.

    >>> normalized_dumps({'see': 1, 'aye': 2, 'bee': 3})
    b'{"aye":2,"bee":3,"see":1}'

    """
    return json.dumps(obj, sort_keys=True, separators=(',',':')).encode('utf-8')


def hash_node(data):
    """
    Hash the normalized JSON-encoded node value.

    For example:

    >>> node = {
    ...     'src': 'VQIXPULW3G77W4XLGROMEDGFAH2XJBN4SAVFUGOZRFSIVU7N',
    ...     'type': 'slice',
    ...     'stream': 'video',
    ...     'start': {
    ...         'frame': 200,
    ...     },
    ...     'stop': {
    ...         'frame': 245,
    ...     },
    ... }
    ...
    >>> hash_node(normalized_dumps(node))
    'JCQ3YMFDNOBY4V5LB6IFTRYMJT5BLPFQUINEZNKU7W6DKC7S'


    Note that even a small change in the edit will result in a different hash:

    >>> node['start']['frame'] = 201
    >>> hash_node(normalized_dumps(node))
    'SPD2YAMBM3YP3I2L32BKMXQ5JAU2PD6XUQHCEC4LPERAS54J'

    """
    skein = skein512(data, digest_bits=DIGEST_BITS, pers=PERS_NODE)
    return b32encode(skein.digest()).decode('utf-8')


def iter_src(src):
    if isinstance(src, str):
        yield src
    elif isinstance(src, list):
        for value in src:
            if isinstance(value, str):
                yield value
            else:
                yield value['id']
    elif isinstance(src, dict):
        for value in src.values():
            if isinstance(value, str):
                yield value
            else:
                yield value['id']


def intrinsic_node(node):
    data = normalized_dumps(node)
    _id = hash_node(data)
    return Intrinsic(_id, data, node)


def intrinsic_src(src, get_doc, results):
    id1 = (src if isinstance(src, str) else src['id'])
    id2 = intrinsic_graph(id1, get_doc, results)
    if isinstance(src, str):
        return id2
    src['id'] = id2
    return src


def intrinsic_graph(_id, get_doc, results):
    try:
        return results[_id]['_id']
    except KeyError:
        pass
    doc = get_doc(_id)
    if len(_id) != RANDOM_B32LEN:
        results[_id] = doc
        return _id
    node = deepcopy(doc['node'])
    src = node['src']
    assert isinstance(src, (str, list, dict))
    if isinstance(src, str):
        new = intrinsic_src(src, get_doc, results)
    elif isinstance(src, list):
        new = [intrinsic_src(value, get_doc, results) for value in src]
    elif isinstance(src, dict):
        new = dict(
            (key, intrinsic_src(value, get_doc, results))
            for (key, value) in src.items()
        )
    node['src'] = new
    inode = intrinsic_node(node)
    results[_id] = create_inode(inode)
    return inode.id


def save_to_intrinsic(root, src, dst):
    results = {}
    iroot = intrinsic_graph(root, src.get, results)
    for doc in results.values():
        for key in ('_rev', '_attachments'):
            try:
                del doc[key]
            except KeyError:
                pass
        try:
            dst.save(doc)
        except Conflict:
            pass
    return iroot


def check_novacut(doc):
    """
    Verify the common schema that all Novacut docs should have.

    For example, a conforming value:

    >>> doc = {
    ...     '_id': 'NZXXMYLDOV2F6ZTUO5PWM5DX',
    ...     'ver': 0,
    ...     'type': 'novacut/foo',
    ...     'time': 1234567890,
    ... }
    ...
    >>> check_novacut(doc)

    """
    _check(doc, [], dict)
    _check(doc, ['_id'], None,
        _any_id,
    )
    _check(doc, ['ver'], int,
        (_equals, VER),
    )
    _check(doc, ['type'], str,
        (_matches, 'novacut/[a-z]+$'),
    )
    _check(doc, ['time'], (int, float),
        (_at_least, 0),
    )


def project_db_name(_id):
    """
    Return the CouchDB database name for the project with *_id*.

    For example:

    >>> project_db_name('HB6YSCKAY27KIWUTWKGKCTNI')
    'novacut-0-hb6ysckay27kiwutwkgkctni'

    """
    return '-'.join(['novacut', str(VER), _id.lower()])


def check_project(doc):
    """
    Verify that *doc* is a valid novacut/project document.

    For example, a conforming value:

    >>> doc = {
    ...     '_id': 'HB6YSCKAY27KIWUTWKGKCTNI',
    ...     'ver': 0,
    ...     'type': 'novacut/project',
    ...     'time': 1234567890,
    ...     'db_name': 'novacut-0-hb6ysckay27kiwutwkgkctni',
    ...     'title': 'Bewitched, Bothered and Bewildered',
    ... }
    ...
    >>> check_project(doc)

    """
    check_novacut(doc)
    _check(doc, ['_id'], None,
        _random_id,
    )
    _check(doc, ['type'], str,
        (_equals, 'novacut/project'),
    )
    _check(doc, ['db_name'], str,
        (_equals, project_db_name(doc['_id'])),
    )
    _check(doc, ['title'], str),


def create_project(title=''):
    _id = random_id()
    ts = time.time()
    return {
        '_id': _id,
        'ver': VER,
        'type': 'novacut/project',
        'time': ts,
        'atime': ts,
        'db_name': project_db_name(_id),
        'title': title,
	'isdeleted': False,
    }


def check_node(doc):
    """
    Verify that *doc* is a valid novacut/node document.

    For example, a conforming value:

    >>> doc = {
    ...     '_id': 'HB6YSCKAY27KIWUTWKGKCTNI',
    ...     'ver': 0,
    ...     'type': 'novacut/node',
    ...     'time': 1234567890,
    ...     'node': {
    ...         'type': 'foo',
    ...         'src': 'XBU6VM2QW76FLGOIJZ24GMRMXSIEICIV723NX4AGR2B4Q44M',
    ...     },
    ... }
    ...
    >>> check_node(doc)

    """
    check_novacut(doc)
    _check(doc, ['_id'], None,
        _random_id,
    )
    _check(doc, ['type'], str,
        (_equals, 'novacut/node'),
    )
    _check(doc, ['node'], dict)
    _check(doc, ['node', 'type'], str,
        _nonempty,
    )
    _check(doc, ['node', 'src'], (str, list, dict))


def create_node(node):
    return {
        '_id': random_id(),
        'ver': VER,
        'type': 'novacut/node',
        'time': time.time(),
        'node': node,
    }


def create_inode(inode):
    return {
        '_id': inode.id,
        '_attachments': {
            'node': {
                'data': b64encode(inode.data).decode('utf-8'),
                'content_type': 'application/json',
            }
        },
        'ver': VER,
        'type': 'novacut/inode',
        'time': time.time(),
        'node': inode.node,
        'renders': {},
    }


def create_settings(node):
    inode = intrinsic_node(node)
    return {
        '_id': inode.id,
        '_attachments': {
            'node': {
                'data': b64encode(inode.data).decode('utf-8'),
                'content_type': 'application/json',
            }
        },
        'ver': VER,
        'type': 'novacut/settings',
        'time': time.time(),
        'node': inode.node,
    }


def create_job(root, settings):
    node = {
        'root': root,
        'settings': settings,
    }
    inode = intrinsic_node(node)
    return {
        '_id': inode.id,
        '_attachments': {
            'node': {
                'data': b64encode(inode.data).decode('utf-8'),
                'content_type': 'application/json',
            }
        },
        'ver': VER,
        'type': 'novacut/job',
        'time': time.time(),
        'node': inode.node,
        'renders': {},
    }


def check_slice(doc):
    check_node(doc)
    _check(doc, ['node', 'type'], str,
        (_equals, 'slice'),
    )
    _check(doc, ['node', 'src'], str,
        _any_id,
    )
    _check(doc, ['node', 'start'], dict,
        _nonempty
    )
    _check(doc, ['node', 'stop'], dict,
        _nonempty
    )
    _check(doc, ['node', 'stream'], str,
        (_is_in, 'video', 'audio'),
    )


def create_slice(src, start, stop, stream='video'):
    node = {
        'type': 'slice',
        'src': src,
        'start': start,
        'stop': stop,
        'stream': stream,
    }
    return create_node(node)


def create_sequence(src):
    assert isinstance(src, list)
    node = {
        'type': 'sequence',
        'src': src,
    }
    doc = create_node(node)
    doc['doodle'] = []
    return doc
            
        

