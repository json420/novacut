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

from microfiber import random_id
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


def normalized_dumps(obj):
    """
    Return *obj* encoded as normalized JSON, the hashing form.

    >>> normalized_dumps({'see': 1, 'aye': 2, 'bee': 3})
    '{"aye":2,"bee":3,"see":1}'

    """
    return json.dumps(obj, sort_keys=True, separators=(',',':'))


def create_node(node):
    return {
        '_id': random_id(),
        'type': 'novacut/node',
        'time': time.time(),
        'node': node,
    }


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
    node = {
        'type': 'sequence',
        'src': src,
    }
    return create_node(node)


def project_db_name(_id):
    """
    Return the CouchDB database name for the project with *_id*.

    For example:

    >>> project_db_name('HB6YSCKAY27KIWUTWKGKCTNI')
    'novacut-hb6ysckay27kiwutwkgkctni'

    """
    return 'novacut-' + _id.lower()


def create_project():
    _id = random_id()
    return {
        '_id': _id,
        'type': 'novacut/project',
        'time': time.time(),
        'db': project_db_name(_id),
    }

