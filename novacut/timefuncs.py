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
Convert between frames, samples, and nanoseconds.
"""

from fractions import Fraction

# In case we want to use these functions when GStreamer isn't available, we
# define our own nanosecond constant:
SECOND = 1000000000


def get_fraction(value):
    """
    Get numerator and denominator independent of exact fraction representation.

    From a ``dict``:

    >>> get_fraction({'num': 30000, 'denom': 1001})
    (30000, 1001)
    
    From a ``list``:

    >>> get_fraction([30000, 1001])
    (30000, 1001)

    From a ``tuple``:

    >>> get_fraction((30000, 1001))
    (30000, 1001)

    Or from a ``fractions.Fraction``:

    >>> get_fraction(Fraction(30000, 1001))
    (30000, 1001)

    """
    if isinstance(value, dict):
        return (value['num'], value['denom'])
    if isinstance(value, (list, tuple)):
        return (value[0], value[1])
    if isinstance(value, Fraction):
        return (value.numerator, value.denominator)
    raise TypeError(
        'invalid fraction type {!r}: {!r}'.format(type(value), value)
    )


def frame_to_nanosecond(frame, framerate):
    """
    Convert from frame to nanosecond (GStreamer time).

    >>> frame_to_nanosecond(30, {'num': 30000, 'denom': 1001})
    1001000000

    """
    (num, denom) = get_fraction(framerate)
    return frame * SECOND * denom // num


def nanosecond_to_frame(nanosecond, framerate):
    """
    Convert from nanosecond (GStreamer time) to frame.

    >>> nanosecond_to_frame(1001000000, {'num': 30000, 'denom': 1001})
    30

    This is designed to round-trip values with `frame_to_nanosecond()`.
    """
    (num, denom) = get_fraction(framerate)
    return int(round(nanosecond * num / denom / SECOND))


def sample_to_nanosecond(sample, samplerate):
    """
    Convert from sample to nanosecond (GStreamer time).

    >>> sample_to_nanosecond(48048, 48000)
    1001000000

    """
    return sample * SECOND // samplerate


def nanosecond_to_sample(nanosecond, samplerate):
    """
    Convert from nanosecond (GStreamer time) to sample.

    >>> nanosecond_to_sample(1001000000, 48000)
    48048

    This is designed to round-trip values with `sample_to_nanosecond()`.
    """
    return int(round(nanosecond * samplerate / SECOND))


def frame_to_sample(frame, framerate, samplerate):
    """
    Convert from frame to sample.

    >>> frame_to_sample(30, {'num': 30000, 'denom': 1001}, 48000)
    48048

    Note that this is *not* designed to round-trip with `sample_to_frame()`.
    """
    (num, denom) = get_fraction(framerate)
    return frame * samplerate * denom // num


def sample_to_frame(sample, samplerate, framerate):
    """
    Convert from sample to frame.

    >>> sample_to_frame(48048, 48000, {'num': 30000, 'denom': 1001})
    30

    Note that this is *not* designed to round-trip with `frame_to_sample()`.
    """
    (num, denom) = get_fraction(framerate)
    return sample * num // (samplerate * denom)

def video_pts_and_duration(start, stop, framerate):
    """
    Get the presentation timestamp and duration for a video slice.

    It can be for a single frame:

    >>> video_pts_and_duration(1, 2, (24, 1))
    (41666666, 41666667)

    Or for a multi-frame slice:

    >>> video_pts_and_duration(1, 101, (24, 1))
    (41666666, 4166666667)
    
    """
    assert 0 <= start < stop
    pts = frame_to_nanosecond(start, framerate)
    duration = frame_to_nanosecond(stop, framerate) - pts
    return (pts, duration)


def aslice_pts_and_duration(start, stop, samplerate):
    """
    Get the presentation timestamp and duration for an audio slice.

    It can be for a single sample:

    >>> aslice_pts_and_duration(1, 2, 48000)
    (20833, 20833)

    Or for a multi-sample slice:

    >>> aslice_pts_and_duration(1, 101, 48000)
    (20833, 2083333)
    
    """
    assert 0 <= start < stop
    pts = sample_to_nanosecond(start, samplerate)
    duration = sample_to_nanosecond(stop, samplerate) - pts
    return (pts, duration)
