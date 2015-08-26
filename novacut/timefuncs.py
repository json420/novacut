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

For typical industry-standard video framerates, you cannot *exactly* express the
needed timestamps using integers, no matter how precise the unit.  Exact
expression requires rational numbers (fractions).  The same is true with typical
industry-standard audio samplerates.

It's not fundamentally a problem that GStreamer works in nanoseconds (an
incredibly precise unit when it comes to human perception).  But rounding error
can lead to ambiguity (if not outright error) in the context of an NLE.

For example, here's the correct pts (presentation time stamp) and duration for
the first 10 frames of a video with a framerate of 24/1:

>>> from fractions import Fraction
>>> from novacut.timefuncs import video_pts_and_duration
>>> framerate = Fraction(24, 1)
>>> for frame in range(10):
...     ts = video_pts_and_duration(frame, framerate)
...     print(ts.duration, ts.pts)
...
41666666 0
41666667 41666666
41666667 83333333
41666666 125000000
41666667 166666666
41666667 208333333
41666666 250000000
41666667 291666666
41666667 333333333
41666666 375000000

The first thing to notice is that the duration isn't constant (although note
that the difference in duration is never more than 1 nanosecond).  To know what
the correct duration is for a given frame, you need to know the index of the
frame (starting from zero).

The same is true when considering multi-frame slices of video.  For example,
a 10 frame slice starting at frame-index 12:

But how many frames does GStreamer give you if you add just one extra nanosecond
to that first slice?  It (correctly) gives you 11 frames, despite the last one
having a meaninglessly short duration.

No one would notice if a frame was displayed 1 nanosecond longer than it should
be.  But an editor will certainly notice an additional frame when editing 24/1
video.  And the audience will too, depending on the footage.  In modern shooting
and editing, a frame is the difference between a cut feeling off and it having
that perfect, ethereal flow.

Editing is fundamentally done in discrete units, frames for video, samples for
audio.  It is for this reason that the Novacut edit description is done it terms
of frames and samples, and not time.  It keeps us honest, and allows us to more
easily determine if our render is delivering what was asked for.

GStreamer is capable of delivering perfect frame and sample accuracy.  But you
need to do your math correctly, and the only way to do that is to do things in
terms of frames and sample up to the last moment, and only then convert to
nanoseconds.
"""

from fractions import Fraction
from collections import namedtuple


# In case we want to use these functions when GStreamer isn't available, we
# define our own nanosecond constant:
SECOND = 1000000000

# namedtuple with pts, duration
Timestamp = namedtuple('Timestamp', 'pts duration')


def frame_to_nanosecond(frame, framerate):
    """
    Convert from frame to nanosecond (GStreamer time).

    >>> frame_to_nanosecond(30, Fraction(30000, 1001))
    1001000000

    """
    return frame * SECOND * framerate.denominator // framerate.numerator


def nanosecond_to_frame(nanosecond, framerate):
    """
    Convert from nanosecond (GStreamer time) to frame.

    >>> nanosecond_to_frame(1001000000, Fraction(30000, 1001))
    30

    This is designed to round-trip values with `frame_to_nanosecond()`.
    """
    return int(round(
        nanosecond * framerate.numerator / framerate.denominator / SECOND
    ))


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

    >>> frame_to_sample(30, Fraction(30000, 1001), 48000)
    48048

    Note that this is *not* designed to round-trip with `sample_to_frame()`.
    """
    assert isinstance(framerate, Fraction)
    return frame * samplerate * framerate.denominator // framerate.numerator


def sample_to_frame(sample, samplerate, framerate):
    """
    Convert from sample to frame.

    >>> sample_to_frame(48048, 48000, Fraction(30000, 1001))
    30

    Note that this is *not* designed to round-trip with `frame_to_sample()`.
    """
    assert isinstance(framerate, Fraction)
    return sample * framerate.numerator // (samplerate * framerate.denominator)


def video_pts_and_duration(frame, framerate):
    """
    Get the presentation timestamp and duration for a video frame.

    For example:

    >>> video_pts_and_duration(1, Fraction(24, 1))
    Timestamp(pts=41666666, duration=41666667)

    This function returns a `Timestamp` namedtuple with *pts* and *duration*
    attributes. For example:

    >>> ts = video_pts_and_duration(1, Fraction(24, 1))
    >>> ts.pts
    41666666
    >>> ts.duration
    41666667

    """
    pts = frame_to_nanosecond(frame, framerate)
    duration = frame_to_nanosecond(frame + 1, framerate) - pts
    return Timestamp(pts, duration)


def audio_pts_and_duration(start, stop, samplerate):
    """
    Get the presentation timestamp and duration for an audio slice.

    It can be for a single sample:

    >>> audio_pts_and_duration(1, 2, 48000)
    Timestamp(pts=20833, duration=20833)

    Or for a multi-sample slice:

    >>> audio_pts_and_duration(1, 101, 48000)
    Timestamp(pts=20833, duration=2083333)

    This function returns a `Timestamp` namedtuple with *pts* and *duration*
    attributes. For example:

    >>> ts = audio_pts_and_duration(1, 101, 48000)
    >>> ts.pts
    20833
    >>> ts.duration
    2083333

    """
    assert 0 <= start < stop
    pts = sample_to_nanosecond(start, samplerate)
    duration = sample_to_nanosecond(stop, samplerate) - pts
    return Timestamp(pts, duration)

