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

import logging
from hashlib import sha1
from collections import namedtuple
from random import SystemRandom

from gi.repository import GLib, Gst

from .timefuncs import (
    Timestamp,
    video_pts_and_duration,
)
from .gsthelpers import Decoder, make_element, get_int


log = logging.getLogger(__name__)
BufferInfo = namedtuple('BufferInfo', 'sha1 duration pts')
random = SystemRandom()


def _row(label, ts):
    return (label, str(ts.pts), str(ts.duration))


def _ts_diff(ts, expected_ts):
    return Timestamp(
        ts.pts - expected_ts.pts,
        ts.duration - expected_ts.duration
    )


def _format_ts_mismatch(ts, expected_ts):
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
    return '\n'.join('  ' + l for l in lines)


class Validator(Decoder):
    def __init__(self, callback, filename, full, strict):
        super().__init__(callback, filename, video=True)
        assert isinstance(full, bool)
        assert isinstance(strict, bool)
        self.full = full
        self.strict = strict
        self.frame = 0
        self.info = {'valid': True}

        # Create elements:
        self.sink = make_element('fakesink', {'signal-handoffs': True})

        # Add elements to pipeline and link:
        self.pipeline.add(self.sink)
        self.video_q.link(self.sink)

        # Connect signal handlers with Pipeline.connect():
        self.connect(self.sink, 'handoff', self.on_handoff)

    def mark_invalid(self):
        if self.full is False and self.info['valid'] is True:
            log.warning(
                'Stopping video check at first error, use --full to check all'
            )
            self.complete(False)
        self.info['valid'] = False

    def check_frame(self, ts):
        frame = self.nanosecond_to_frame(ts.pts)
        if self.frame != frame:
            log.error('Expected frame %s, got %s (pts=%s, duration=%s)',
                self.frame, frame, ts.pts, ts.duration
            )
            self.mark_invalid()
        if self.strict is False:
            return
        expected_ts = video_pts_and_duration(frame, self.framerate)
        if ts != expected_ts:
            log.warning('Timestamp mismatch at frame %d:\n%s',
                self.frame, _format_ts_mismatch(ts, expected_ts)
            )
            self.mark_invalid()

    def check_duration(self):
        frames = self.info['frames']
        duration = self.info['duration']
        expected_frames = self.nanosecond_to_frame(duration)
        expected_duration = self.frame_to_nanosecond(frames)
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
        if self.strict is not True:
            log.warning(
                'Checking video in NON-strict mode, consider using --strict'
            )
        self.set_state(Gst.State.PAUSED, sync=True)
        (success, ns) = self.pipeline.query_duration(Gst.Format.TIME)
        if not success:
            log.error('Could not query duration')
            self.complete(False)
            return
        log.info('Duration in nanoseconds: %d ns', ns)
        self.info['duration'] = ns
        self.set_state(Gst.State.PLAYING)

    def extract_video_info(self, structure):
        super().extract_video_info(structure)
        self.info['framerate'] = {
            'num': self.framerate.numerator,
            'denom': self.framerate.denominator,
        }
        self.info['width'] = get_int(structure, 'width')
        self.info['height'] = get_int(structure, 'height')

    def on_handoff(self, sink, buf, pad):
        self.check_frame(Timestamp(buf.pts, buf.duration))
        self.frame += 1

    def on_eos(self, bus, msg):
        log.debug('Got EOS from message bus')
        self.info['frames'] = self.frame
        self.check_duration()
        valid = self.info.get('valid')
        if valid is not True:
            log.warning('This is NOT a conforming video!')
        elif self.strict is True:
            log.info('Success, video is conformant under STRICT checking!')
        else:
            log.info('Success, video is conformant under NON-strict checking!')
            log.info('[Use the --strict option to enable strict checking.]')
        self.complete(valid)


def get_buffer_info(buf):
    data = buf.extract_dup(0, buf.get_size())
    digest = sha1(data).hexdigest()
    return BufferInfo(digest, buf.duration, buf.pts)


def shuffle_indexes(count):
    indexes = list(range(count))
    random.shuffle(indexes)
    random.shuffle(indexes)  # Shuffle twice for higher quality random order
    return tuple(indexes)


class PlayThrough(Decoder):
    def __init__(self, callback, filename):
        super().__init__(callback, filename, video=True)
        self.filename = filename
        self.duration = None
        self.video = []

        # Create elements:
        self.sink = make_element('fakesink', {'signal-handoffs': True})

        # Add elements to pipeline and link:
        self.pipeline.add(self.sink)
        self.video_q.link(self.sink)

        # Connect signal handlers with Pipeline.connect():
        self.connect(self.sink, 'handoff', self.on_handoff)

    def run(self):
        try:
            log.info('Play-through test: %r', self.filename)
            self.set_state(Gst.State.PAUSED, sync=True)
            log.info('Framerate: %s', self.framerate)
            self.duration = self.get_duration()
            log.info('Duration: %d nanoseconds', self.duration)
            self.set_state(Gst.State.PLAYING)
        except:
            log.exception('%s.run():', self.__class__.__name__)
            self.complete(False)

    def on_handoff(self, sink, buf, pad):
        try:
            info = get_buffer_info(buf)
            log.debug('%s %d %d %d',
                info.sha1, info.duration, info.pts, len(self.video)
            )
            self.video.append(info)
        except:
            log.exception('%s.on_handoff():', self.__class__.__name__)
            self.complete(False)

    def on_eos(self, bus, msg):
        try:
            log.info('Frames: %d', len(self.video))
            self.complete(True)
        except:
            log.exception('%s.on_eos():', self.__class__.__name__)
            self.complete(False)


class PrerollTester(Decoder):
    def __init__(self, callback, filename, seek_times):
        super().__init__(callback, filename, video=True)
        assert isinstance(seek_times, list)
        self.filename = filename
        self.seek_times = seek_times
        self.video = []

        # Create elements:
        self.sink = make_element('fakesink')

        # Add elements to pipeline and link:
        self.pipeline.add(self.sink)
        self.video_q.link(self.sink)

        # Connect signal handlers with Pipeline.connect():
        self.connect(self.sink, 'preroll-handoff', self.on_preroll_handoff)

    def run(self):
        try:
            log.info('Preroll test: %r', self.filename)
            self.set_state(Gst.State.PAUSED, sync=True)
            self.sink.set_property('signal-handoffs', True)
            GLib.idle_add(self.next)
        except:
            log.exception('%s.run():', self.__class__.__name__)
            self.complete(False)

    def next(self):
        try:
            if self.seek_times:
                ns = self.seek_times.pop(0)
                self.seek_simple(ns)
            else:
                self.complete(True)
        except:
            log.exception('%s.next():', self.__class__.__name__)
            self.complete(False)

    def on_preroll_handoff(self, sink, buf, pad):
        try:
            info = get_buffer_info(buf)
            log.debug('%s %d %d %d',
                info.sha1, info.duration, info.pts, len(self.video)
            )
            self.video.append(info)
            GLib.idle_add(self.next)
        except:
            log.exception('%s.on_preroll_handoff():', self.__class__.__name__)
            self.complete(False)


class SeekTester(Decoder):
    def __init__(self, callback, filename, slices):
        super().__init__(callback, filename, video=True)
        assert isinstance(slices, list)
        self.filename = filename
        self.slices = slices
        self.video = []

        # Create elements:
        self.sink = make_element('fakesink', {'signal-handoffs': True})

        # Add elements to pipeline and link:
        self.pipeline.add(self.sink)
        self.video_q.link(self.sink)

        # Connect signal handlers with Pipeline.connect():
        self.connect(self.sink, 'handoff', self.on_handoff)

    def run(self):
        try:
            log.info('Seek test: %r', self.filename)
            self.set_state(Gst.State.PAUSED, sync=True)
            self.next()
            self.set_state(Gst.State.PLAYING)
        except:
            log.exception('%s.run():', self.__class__.__name__)
            self.complete(False)

    def next(self):
        try:
            if self.slices:
                (start, stop) = self.slices.pop(0)
                self.seek(start, stop)
            else:
                self.complete(True)
        except:
            log.exception('%s.next():', self.__class__.__name__)
            self.complete(False)

    def on_handoff(self, sink, buf, pad):
        try:
            info = get_buffer_info(buf)
            log.debug('%s %d %d %d',
                info.sha1, info.duration, info.pts, len(self.video)
            )
            self.video.append(info)
        except:
            log.exception('%s.on_handoff():', self.__class__.__name__)
            self.complete(False)

    def on_eos(self, bus, msg):
        log.debug('%s.on_eos', self.__class__.__name__)
        self.next()

