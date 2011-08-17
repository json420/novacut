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

import json
from os import urandom
from base64 import b32encode
import re


DIGEST_BYTES = 30


def random_id():
    """
    Returns a 120-bit base32-encoded random ID.

    The ID will be 24-characters long, URL and filesystem safe.  For example:

    >>> random_id()  #doctest: +SKIP
    'OVRHK3TUOUQCWIDMNFXGC4TP'

    """
    return b32encode(urandom(15))


# Some private helper functions that don't directly define any schema.
#
# If this seems unnecessary or even a bit un-Pythonic (where's my duck typing?),
# keep in mind that the goal of this module is to:
#
#   1. Unambiguously define the schema
#
#   2. Provide exceedingly helpful error messages when values do not conform
#      with the schema
#
# That is all.


def _label(path):
    """
    Create a helpful debugging label to indicate the attribute in question.

    For example:

    >>> _label([])
    'doc'
    >>> _label(['log'])
    "doc['log']"
    >>> _label(['log', 'considered', 2, 'src'])
    "doc['log']['considered'][2]['src']"

    See also `_value()`.
    """
    return 'doc' + ''.join('[{!r}]'.format(key) for key in path)


def _value(doc, path):
    """
    Retrieve value from *doc* by traversing *path*.

    For example:

    >>> doc = {'log': {'considered': [None, None, {'src': 'hello'}, None]}}
    >>> _value(doc, [])
    {'log': {'considered': [None, None, {'src': 'hello'}, None]}}
    >>> _value(doc, ['log'])
    {'considered': [None, None, {'src': 'hello'}, None]}
    >>> _value(doc, ['log', 'considered', 2, 'src'])
    'hello'

    Or if you try to retrieve something that doesn't exist:

    >>> _value(doc, ['log', 'considered', 7])
    Traceback (most recent call last):
      ...
    ValueError: doc['log']['considered'][7] does not exist

    Or if a key/index is missing higher up in the path:

    >>> _value(doc, ['dog', 'considered', 7])
    Traceback (most recent call last):
      ...
    ValueError: doc['dog'] does not exist

    See also `_label()`.
    """
    value = doc
    p = []
    for key in path:
        p.append(key)
        try:
            value = value[key]
        except (KeyError, IndexError):
            raise ValueError(
                '{} does not exist'.format(_label(p))
            )
    return value


def _exists(doc, path):
    """
    Return ``True`` if the end of *path* exists.

    For example:

    >>> doc = {'foo': {'hello': 'world'}, 'bar': ['hello', 'naughty', 'nurse']}
    >>> _exists(doc, ['foo', 'hello'])
    True
    >>> _exists(doc, ['foo', 'sup'])
    False
    >>> _exists(doc, ['bar', 2])
    True
    >>> _exists(doc, ['bar', 3])
    False

    Or if a key/index is missing higher up the path:

    >>> _exists(doc, ['stuff', 'junk'])
    Traceback (most recent call last):
      ...
    ValueError: doc['stuff'] does not exist

    See also `_check_if_exists()`.
    """
    if len(path) == 0:
        return True
    base = _value(doc, path[:-1])
    key = path[-1]
    try:
        value = base[key]
        return True
    except (KeyError, IndexError):
        return False


def _isinstance(value, label, allowed):
    """
    Verify that *value* is an instance of *allowed*.

    For example:

    >>> _isinstance('18', "doc['bytes']", int)
    Traceback (most recent call last):
      ...
    TypeError: doc['bytes']: need a <type 'int'>; got a <type 'str'>: '18'

    """
    if not isinstance(value, allowed):
        raise TypeError('{}: need a {!r}; got a {!r}: {!r}'.format(
                label, allowed, type(value), value
            )
        )


def _check(doc, path, allowed, *checks):
    """
    Run a series of *checks* on the value in *doc* addressed by *path*.

    For example:

    >>> doc = {'foo': [None, {'bar': 'aye'}, None]}
    >>> _check(doc, ['foo', 1, 'bar'], str,
    ...     (_is_in, 'bee', 'sea'),
    ... )
    ...
    Traceback (most recent call last):
      ...
    ValueError: doc['foo'][1]['bar'] value 'aye' not in ('bee', 'sea')

    Or if a value is missing:

    >>> _check(doc, ['foo', 3], str,
    ...     (_equals, 'hello'),
    ... )
    ...
    Traceback (most recent call last):
      ...
    ValueError: doc['foo'][3] does not exist

    See also `_check_if_exists()`.
    """
    value = _value(doc, path)
    label = _label(path)
    _isinstance(value, label, allowed)
    if value is None:
        return
    for c in checks:
        if isinstance(c, tuple):
            (c, args) = (c[0], c[1:])
        else:
            args = tuple()
        c(value, label, *args)


def _check_if_exists(doc, path, allowed, *checks):
    """
    Run *checks* only if value at *path* exists.

    For example:

    >>> doc = {'name': 17}
    >>> _check_if_exists(doc, ['dir'], str)
    >>> _check_if_exists(doc, ['name'], str)
    Traceback (most recent call last):
      ...
    TypeError: doc['name']: need a <type 'str'>; got a <type 'int'>: 17


    See also `_check()` and `_exists()`.
    """
    if _exists(doc, path):
        _check(doc, path, allowed, *checks)


def _at_least(value, label, minvalue):
    """
    Verify that *value* is greater than or equal to *minvalue*.

    For example:

    >>> _at_least(0, "doc['bytes']", 1)
    Traceback (most recent call last):
      ...
    ValueError: doc['bytes'] must be >= 1; got 0

    """
    if value < minvalue:
        raise ValueError(
            '%s must be >= %r; got %r' % (label, minvalue, value)
        )


def _lowercase(value, label):
    """
    Verify that *value* is lowercase.

    For example:

    >>> _lowercase('MOV', "doc['ext']")
    Traceback (most recent call last):
      ...
    ValueError: doc['ext'] must be lowercase; got 'MOV'

    """
    if not value.islower():
        raise ValueError(
            "{} must be lowercase; got {!r}".format(label, value)
        )


def _matches(value, label, pattern):
    """
    Verify that *value* matches regex *pattern*.

    For example:

    >>> _matches('hello_world', "doc['plugin']", '^[a-z][_a-z0-9]*$')
    >>> _matches('hello-world', "doc['plugin']", '^[a-z][_a-z0-9]*$')
    Traceback (most recent call last):
      ...
    ValueError: doc['plugin']: 'hello-world' does not match '^[a-z][_a-z0-9]*$'

    """
    if not re.match(pattern, value):
        raise ValueError(
            '{}: {!r} does not match {!r}'.format(label, value, pattern)
        )


def _nonempty(value, label):
    """
    Verify that *value* is not empty (ie len() > 0).

    For example:

    >>> _nonempty({}, 'stored')
    Traceback (most recent call last):
      ...
    ValueError: stored cannot be empty; got {}

    """
    if len(value) == 0:
        raise ValueError('{} cannot be empty; got {!r}'.format(label, value))


def _is_in(value, label, *possible):
    """
    Check that *value* is one of *possible*.

    For example:

    >>> _is_in('foo', "doc['media']", 'video', 'audio', 'image')
    Traceback (most recent call last):
      ...
    ValueError: doc['media'] value 'foo' not in ('video', 'audio', 'image')

    """
    if value not in possible:
        raise ValueError(
            '{} value {!r} not in {!r}'.format(label, value, possible)
        )


def _equals(value, label, expected):
    """
    Check that *value* equals *expected*.

    For example:

    >>> _equals('file', "doc['type']", 'dmedia/file')
    Traceback (most recent call last):
      ...
    ValueError: doc['type'] must equal 'dmedia/file'; got 'file'

    """
    if value != expected:
        raise ValueError(
            '{} must equal {!r}; got {!r}'.format(label, expected, value)
        )


def normalized_dumps(obj):
    """
    Return *obj* encoded as normalized JSON, the hashing form.

    >>> normalized_dumps({'see': 1, 'aye': 2, 'bee': 3})
    '{"aye":2,"bee":3,"see":1}'

    """
    return json.dumps(obj, sort_keys=True, separators=(',',':'))
