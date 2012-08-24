# novacut: the distributed video editor
# Copyright (C) 2012 Novacut Inc
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
Map the Novacut edit description into gnonlin semantics.

In terms of abstraction, this module sits between `timefuncs` and `renderer`.
The idea is to map the edit description into the semantics of gnonlin, but
without actually creating any GStreamer elements or setting their properties.

There are 2 reasons to separate this functionality from `renderer`:

    1. Better testability - we can test the math and logic of the mapping in
       the simplest, most isolated way possible

    2. Dynamic updates - we make this functionality easier to re-use between
       the configure-once render pipeline and the dynamically updated preview
       pipeline
"""

from fractions import Fraction

from .timefuncs import video_pts_and_duration, audio_pts_and_duration


def get_fraction(value):
    """
    Get a ``Fraction`` independent of exact fraction representation.

    From a ``dict``:

    >>> get_fraction({'num': 30000, 'denom': 1001})
    Fraction(30000, 1001)

    From a ``list``:

    >>> get_fraction([30000, 1001])
    Fraction(30000, 1001)

    Or from a ``tuple``:

    >>> get_fraction((30000, 1001))
    Fraction(30000, 1001)

    """
    if isinstance(value, Fraction):
        return value
    if isinstance(value, dict):
        return Fraction(value['num'], value['denom'])
    if isinstance(value, (list, tuple)):
        return Fraction(value[0], value[1])
    raise TypeError(
        'invalid fraction type {!r}: {!r}'.format(type(value), value)
    )


def get_framerate(doc):
    return get_fraction(doc['framerate'])


def video_slice_to_gnl(offset, start, stop, framerate):
    """
    Map a video slice into gnlurisource properties.

    For example, say you have a 7:42 slice at offset 200:

    >>> video_slice_to_gnl(200, 7, 42, Fraction(24, 1)) == {
    ...     'media-start': 291666666,
    ...     'media-duration': 1458333334,
    ...     'start': 8333333333,
    ...     'duration': 1458333333,
    ... }
    True
    
    """
    assert 0 <= start < stop

    # These properties are about the slice itself
    (pts1, dur1) = video_pts_and_duration(start, stop, framerate)

    # These properties are about the position of the slice in the composition
    frames = stop - start
    (pts2, dur2) = video_pts_and_duration(offset, offset + frames, framerate)

    assert abs(dur1 - dur2) <= 1
    return {
        'media-start': pts1,
        'media-duration': dur1,
        'start': pts2,
        'duration': dur2,
    }


def audio_slice_to_gnl(offset, start, stop, samplerate):
    assert 0 <= start < stop

    # These properties are about the slice itself
    (pts1, dur1) = audio_pts_and_duration(start, stop, samplerate)

    # These properties are about the position of the slice in the composition
    samples = stop - start
    (pts2, dur2) = audio_pts_and_duration(offset, offset + samples, samplerate)

    assert abs(dur1 - dur2) <= 1
    return {
        'media-start': pts1,
        'media-duration': dur1,
        'start': pts2,
        'duration': dur2,
    }

