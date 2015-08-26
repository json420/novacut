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
Check video for timestamp conformance.
"""

from fractions import Fraction
import logging

from gi.repository import Gst

from .timefuncs import (
    Timestamp,
    frame_to_nanosecond,
    nanosecond_to_frame,
    video_pts_and_duration,
)
from .gsthelpers import Pipeline, make_element, add_elements


log = logging.getLogger(__name__)


def _row(label, ts):
    return (label, str(ts.pts), str(ts.duration))

def _ts_diff(ts, expected_ts):
    return Timestamp(
        ts.pts - expected_ts.pts,
        ts.duration - expected_ts.duration
    )


def format_ts_mismatch(ts, expected_ts):
    rows = (
        ('', 'PTS', 'DURATION'),
        _row('GOT:', ts),
        _row('EXPECTED:', expected_ts),
        _row('DIFF', _ts_diff(ts, expected_ts)),
    )
    widths = tuple(
        max(len(r[i]) for r in rows) for i in range(3)
    )
    lines = [
        ' '.join(row[i].rjust(widths[i]) for i in range(3))
        for row in rows
    ]
    return '\n'.join('    ' + l for l in lines)


def get_expected_ts(frame, framerate):
    return video_pts_and_duration(frame, frame + 1, framerate)


class Validator(Pipeline):
    def __init__(self, callback, filename, full, strict):
        super().__init__(callback)
        assert isinstance(full, bool)
        assert isinstance(strict, bool)
        self.full = full
        self.strict = strict
        self.frame = 0
        self.framerate = None
        self.info = {'valid': True}

        # Create elements:
        self.src = make_element('filesrc', {'location': filename})
        self.dec = make_element('decodebin')
        self.q = make_element('queue')
        self.sink = make_element('fakesink', {'signal-handoffs': True})

        # Add elements to pipeline and link:
        add_elements(self.pipeline, self.src, self.dec, self.q, self.sink)
        self.src.link(self.dec)
        self.q.link(self.sink)

        # Connect signal handlers with Pipeline.connect():
        self.connect(self.bus, 'message::eos', self.on_eos)
        self.connect(self.dec, 'pad-added', self.on_pad_added)
        self.connect(self.sink, 'handoff', self.on_handoff)

    def mark_invalid(self):
        if self.full is False and self.info['valid'] is True:
            log.info('Stopping check at first error')
            self.complete(False)
        self.info['valid'] = False

    def check_frame(self, ts):
        frame = nanosecond_to_frame(ts.pts, self.framerate)
        if frame != self.frame:
            log.error('Expected frame %s, got %s (pts=%s, duration=%s)',
                self.frame, frame, ts.pts, ts.duration
            )
            self.mark_invalid()
        if self.strict is False:
            return
        expected_ts = video_pts_and_duration(frame, frame + 1, self.framerate)
        if ts != expected_ts:
            log.warning('Timestamp mismatch at frame %d:\n%s',
                self.frame, format_ts_mismatch(ts, expected_ts)
            )
            self.mark_invalid()

    def check_duration(self):
        frames = self.info['frames']
        duration = self.info['duration']
        expected_frames = nanosecond_to_frame(duration, self.framerate)
        expected_duration = frame_to_nanosecond(frames, self.framerate)
        if expected_frames != frames:
            log.error('Expected %s total frames, got %s',
                expected_frames, frames
            )
            self.info['valid'] = False
        if self.strict is False:
            return
        if expected_duration != duration:
            log.warning('Expected duration of %s nanoseconds, got %s',
                expected_duration, duration
            )
            self.info['valid'] = False

    def run(self):
        self.set_state(Gst.State.PAUSED, sync=True)
        (success, ns) = self.pipeline.query_duration(Gst.Format.TIME)
        if not success:
            log.error('Could not query duration')
            self.complete(False)
            return
        log.info('duration: %d ns', ns)
        self.info['duration'] = ns
        self.set_state(Gst.State.PLAYING)

    def _info_from_caps(self, caps):
        s = caps.get_structure(0)

        (success, num, denom) = s.get_fraction('framerate')
        if not success:
            log.error('could not get framerate from video stream')
            return False

        (sucess, width) = s.get_int('width')
        if not success:
            log.error('could not get width from video stream')
            return False

        (sucess, height) = s.get_int('height')
        if not success:
            log.error('could not get height from video stream')
            return False

        self.framerate = Fraction(num, denom)
        self.info['framerate'] = {'num': num, 'denom': denom}
        self.info['width'] = width
        self.info['height'] = height

        log.info('framerate: %d/%d', num, denom)
        log.info('resolution: %dx%d', width, height)
        return True

    def on_pad_added(self, dec, pad):
        caps = pad.get_current_caps()
        string = caps.to_string()
        log.info('on_pad_added(): %s', string)
        if string.startswith('video/'):
            if self._info_from_caps(caps) is True:
                pad.link(self.q.get_static_pad('sink'))

    def on_handoff(self, sink, buf, pad):
        self.check_frame(Timestamp(buf.pts, buf.duration))
        self.frame += 1

    def on_eos(self, bus, msg):
        log.info('eos')
        self.info['frames'] = self.frame
        self.check_duration()
        if info['valid'] is True:
            log.info('Success, this is a conforming video!')
        else:
            log.warning('This is not a conforming video!')
        self.complete(info['valid'])

