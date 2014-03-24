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

Although a nanosecond is a very precise unit, nanoseconds can't *exactly*
represent the timestamps and durations in typical media.  To do this, you
need to use rational (fractional) timestamps.

Here you can see what "perfect" timestamps look like when converted to
nanoseconds:

>>> for i in range(10):
...     (pts, dur) = video_pts_and_duration(i, i + 1, Fraction(24, 1))
...     print(dur, pts)
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

The first thing to notice is that the duration isn't constant.  This is
because it's impossible to exactly represent the duration in nanoseconds.
So the duration is different depending on which frame (globally) you're
considering.

FYI, MOV files from Canon HDSLR cameras have exactly the sort of "perfect"
timestamps illustrated above.  And in our testing, GStreamer has been able to
produce flawless frame accuracy when it comes to cutting slices out of such
video (confirmed by doing md5sums of the video buffers).

It's easy to calculate perfect timestamps for selecting a slice because it
only involves local time.

For example, the start and stop timestamps for the slice ``23:104`` from
30000/1001 video can be calculated like this:

>>> 23 * SECOND * 1001 // 30000  # start
767433333
>>> 104 * SECOND * 1001 // 30000  # stop
3470133333

Which is exactly the calculation that the `frame_to_nanosecond()` function
does:

>>> frame_to_nanosecond(23, Fraction(30000, 1001))
767433333
>>> frame_to_nanosecond(104, Fraction(30000, 1001))
3470133333

And the slice duration is simply ``stop - start``:

>>> 3470133333 - 767433333
2702700000

The `video_pts_and_duration()` function returns the start timestamp and the
same duration as above:

>>> video_pts_and_duration(23, 104, Fraction(30000, 1001))
Timestamp(pts=767433333, duration=2702700000)

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
    assert isinstance(framerate, Fraction)
    return frame * SECOND * framerate.denominator // framerate.numerator


def nanosecond_to_frame(nanosecond, framerate):
    """
    Convert from nanosecond (GStreamer time) to frame.

    >>> nanosecond_to_frame(1001000000, Fraction(30000, 1001))
    30

    This is designed to round-trip values with `frame_to_nanosecond()`.
    """
    assert isinstance(framerate, Fraction)
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


def video_pts_and_duration(start, stop, framerate):
    """
    Get the presentation timestamp and duration for a video slice.

    It can be for a single frame:

    >>> video_pts_and_duration(1, 2, Fraction(24, 1))
    Timestamp(pts=41666666, duration=41666667)

    Or for a multi-frame slice:

    >>> video_pts_and_duration(1, 101, Fraction(24, 1))
    Timestamp(pts=41666666, duration=4166666667)

    This function returns a `Timestamp` namedtuple with *pts* and *duration*
    attributes. For example:

    >>> ts = video_pts_and_duration(1, 101, Fraction(24, 1))
    >>> ts.pts
    41666666
    >>> ts.duration
    4166666667

    """
    assert 0 <= start < stop
    pts = frame_to_nanosecond(start, framerate)
    duration = frame_to_nanosecond(stop, framerate) - pts
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


def video_slice_to_gnl_old(offset, start, stop, framerate):
    """
    Map a video slice at global *offset* into gnlurisource properties.

    For example, say at global frame offset 200 you have a slice from frame
    7 to frame 42:

    >>> video_slice_to_gnl_old(200, 7, 42, Fraction(24, 1)) == {
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


def audio_slice_to_gnl_old(offset, start, stop, samplerate):
    """
    Map an audio slice at global *offset* into gnlurisource properties.

    The is the old function for gnonlin 0.10 semantics.

    For example, say at global sample offset 2000 you have a slice from
    sample 30,000 to sample 90,000:

    >>> audio_slice_to_gnl_old(2000, 30000, 90000, 48000) == {
    ...     'media-start': 625000000,
    ...     'media-duration': 1250000000,
    ...     'start': 41666666,
    ...     'duration': 1250000000,
    ... }
    True

    """
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


def video_slice_to_gnl(offset, start, stop, framerate):
    """
    Map a video slice at global *offset* into gnlurisource properties.

    This version is for the gnonlin 1.0 API.

    Note that the gnonlin 1.0 API currently seems somewhat ambiguous because
    even when the incoming and outgoing slices are at the same framerate and the
    duration ratio (in frames) is 1:1, the duration of the incoming and outgoing
    slices in *nanoseconds* might not be the same because of rounding error
    (although they will be within one nanosecond of each other).

    For example, say at global frame offset 200 you have a slice from frame 7 to
    frame 42:

    >>> video_slice_to_gnl(200, 7, 42, Fraction(24, 1)) == {
    ...     'inpoint': 291666666,
    ...     'start': 8333333333,
    ...     'duration': 1458333333,
    ... }
    True

    Whereas note that the correctly rounded nanosecond duration on the incoming
    slice is not ``1458333333``:

    >>> video_pts_and_duration(7, 42, Fraction(24, 1))
    Timestamp(pts=291666666, duration=1458333334)

    """
    assert 0 <= start < stop

    # Starting timestamp of the source slice:
    inpoint = frame_to_nanosecond(start, framerate)

    # Slice duration in frames:
    frames = stop - start

    # Timestamp and duration of outgoing slice:
    (pts2, dur2) = video_pts_and_duration(offset, offset + frames, framerate)

    return {
        'inpoint': inpoint,
        'start': pts2,
        'duration': dur2,
    }
