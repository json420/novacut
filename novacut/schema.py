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


Above sequence with "nigelb" effect applied:

>>> doc = {
...     '_id': 'AJU33MYHLQLVSRPTEUZA5KQ3',
...     'type': 'novacut/node',
...     'node': {
...         'type': 'nigelb',
...         'src': 'JG444OBNF5JUUNSPCCE5YPIK',
...         'alpha': 0.7,
...         'awesome': True,
...     },
... }

Happy birthday, Nigel!



Design Decision: hashable semantic content
==========================================

The CouchDB document corresponding to each node in the editing graph has two
distinct purposes: unambiguously store the "meaning" of the edit semantically
speaking, and to provide and extensible place to store various annotations.

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

    2. It gives us a globally unique way to refer.


"""

import json
from os import urandom
from base64 import b32encode


def random_id():
    """
    Returns a 120-bit base32-encoded random ID.

    The ID will be 24-characters long, URL and filesystem safe.  For example:

    >>> random_id()  #doctest: +SKIP
    'OVRHK3TUOUQCWIDMNFXGC4TP'

    """
    return b32encode(urandom(15))
