# novacut: the distributed video editor
# Copyright (C) 2011-2015 Novacut Inc
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
A few Python helpers for working with `gi.repository.Gst`.

Please exercise thoughtful restraint when adding things to this module as we
don't want to accumulate too much magic wrapper sauce!
"""

from fractions import Fraction
import logging

from gi.repository import Gst


log = logging.getLogger(__name__)
Gst.init()


# Provide very clear TypeError messages:
TYPE_ERROR = '{}: need a {!r}; got a {!r}: {!r}'


class ElementFactoryError(Exception):
    """
    Raised when `Gst.ElementFactory.make()` fails.

    When `Gst.ElementFactory.make()` fails to create an element, it returns
    `None` rather than raising an exception.  This can make debugging
    difficult if the calling code doesn't immediately check it, because
    otherwise you'll later get a mystery error like this::

        AttributeError: 'NoneType' object has no attribute 'set_property'

    So the guidance for Novacut is to use the `make_element()` function below,
    which will raise this exception if `Gst.ElementFactory.make()` returns
    `None`.
    """

    def __init__(self, name):
        self.name = name
        super().__init__('Could not make Gst.Element {!r}'.format(name))


def make_element(name, props=None):
    """
    Create a new `Gst.Element`, optionally setting its GObject properties.

    This function will return a new `Gst.Element`, for example:

    >>> enc = make_element('theoraenc')

    If provided, the optional *props* argument must be a `dict` mapping GObject
    property names to the values you wish to set.  This is a nice shorthand when
    setting multiple properties.

    For example, we could now set the "quality" and "keyframe-freq" properties
    on the `enc` element we created above:

    >>> enc.set_property('quality', 56)
    >>> enc.set_property('keyframe-freq', 16)

    Or we could have achieved the same all in one go like this:

    >>> enc = make_element('theoraenc', {'quality': 56, 'keyframe-freq': 16})

    Note: in Novacut code, please use this function instead of directly using
    `Gst.ElementFactory.make()`.

    This function will raise our custom `ElementFactoryError` exception if the
    element could not be created, whereas the latter will simply return `None`.
    """
    if not isinstance(name, str):
        raise TypeError(
            TYPE_ERROR.format('name', str, type(name), name)
        )
    if not (props is None or isinstance(props, dict)):
        raise TypeError(
            TYPE_ERROR.format('props', dict, type(props), props)
        )
    element = Gst.ElementFactory.make(name, None)
    if element is None:
        log.error('could not create GStreamer element %r', name)
        raise ElementFactoryError(name)
    if props:
        for (key, value) in props.items():
            element.set_property(key, value)
    return element


def make_element_from_desc(desc):
    """
    Create a `Gst.Element` from a JSON-serializable description.

    For example:

    >>> enc = make_element_from_desc('theoraenc')
    >>> enc.get_factory().get_name()
    'theoraenc'
    
    Or from a ``dict`` with the element name:

    >>> enc = make_element_from_desc({'name': 'theoraenc'})
    >>> enc.get_factory().get_name()
    'theoraenc'
    >>> enc.get_property('quality')
    48

    Or from a ``dict`` with the element name and props:

    >>> enc = make_element_from_desc({'name': 'theoraenc', 'props': {'quality': 40}})
    >>> enc.get_factory().get_name()
    'theoraenc'
    >>> enc.get_property('quality')
    40

    """
    if isinstance(desc, dict):
        return make_element(desc['name'], desc.get('props'))
    return make_element(desc)


def make_caps_string(mime, desc):
    """
    Build a string for passing to `Gst.caps_from_string()`.

    For example:

    >>> make_caps_string('video/x-raw', {'width': 800, 'height': 450})
    'video/x-raw, height=450, width=800'

    This function is used by `make_caps()`.
    """
    if mime not in ('audio/x-raw', 'video/x-raw'):
        raise ValueError('bad caps mime: {!r}'.format(mime))
    if not isinstance(desc, dict):
        raise TypeError(
            TYPE_ERROR.format('desc', dict, type(desc), desc)
        )
    accum = [mime]
    for (key, val) in sorted(desc.items()):
        if isinstance(val, Fraction):
            val = '(fraction){}/{}'.format(val.numerator, val.denominator)
        accum.append('{}={}'.format(key, val))
    return ', '.join(accum)


def make_caps(mime, desc):
    """
    Build `Gst.Caps` from a JSON-serializable description in *desc*.

    For example:

    >>> caps = make_caps('video/x-raw', {'width': 800, 'height': 450})
    >>> caps.to_string()
    'video/x-raw, height=(int)450, width=(int)800'

    """
    return Gst.caps_from_string(make_caps_string(mime, desc))


def get_framerate_from_struct(s):
    (success, num, denom) = s.get_fraction('framerate')
    if not success:
        raise Exception("could not get 'framerate' from video caps structure")
    return Fraction(num, denom)


