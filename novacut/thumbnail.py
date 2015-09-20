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
Create frame-accurate JPEG thumbnail images.
"""

import logging
from base64 import b64encode
from collections import namedtuple

from gi.repository import GLib, Gst

from .timefuncs import nanosecond_to_frame
from .gsthelpers import (
    Decoder,
    make_element,
    add_elements,
    make_caps,
)


log = logging.getLogger(__name__)
StartStop = namedtuple('StartStop', 'start stop')


class GenericThumbnailer(Decoder):
    def __init__(self, callback, filename, frame, **kw):
        super().__init__(callback, filename, video=True)
        self.frame = frame
        self.data = None

        # Create elements
        self.convert = make_element('videoconvert')
        self.scale = make_element('videoscale', {'method': 3})
        self.enc = make_element('jpegenc', {'quality': 90, 'idct-method': 2})
        self.sink = make_element('fakesink')

        # Add elements to pipeline and link:
        add_elements(self.pipeline,
            self.convert, self.scale, self.enc, self.sink
        )
        self.video_q.link(self.convert)
        self.convert.link(self.scale)
        desc = {'pixel-aspect-ratio': '1/1', 'format': 'I420'}
        for key in ('width', 'height'):
            value = kw.get(key)
            if value is not None:
                desc[key] = value
        caps = make_caps('video/x-raw', desc)
        self.scale.link_filtered(self.enc, caps)
        self.enc.link(self.sink)

        # Connect signal handlers using Pipeline.connect():
        self.connect(self.sink, 'preroll-handoff', self.on_preroll_handoff)

    def run(self):
        self.set_state(Gst.State.PAUSED, sync=True)
        self.sink.set_property('signal-handoffs', True)
        self.seek_by_frame(self.frame)

    def on_preroll_handoff(self, element, buf, pad):
        log.info('preroll-handoff')
        self.data = buf.extract_dup(0, buf.get_size())
        self.complete(True)

    def on_eos(self, bus, msg):
        log.debug('Got EOS from message bus')
        self.complete(False)


def walk_backward(existing, frame, steps=1):
    assert frame >= 0
    assert frame not in existing
    assert steps >= 1
    for i in range(steps):
        frame -= 1
        if frame < 0 or frame in existing:
            return frame + 1
    return frame


def walk_forward(existing, frame, file_stop, steps=1):
    assert 0 <= frame < file_stop
    assert frame not in existing
    assert steps >= 1
    for i in range(steps):
        frame += 1
        if frame >= file_stop or frame in existing:
            return frame - 1
    return frame


def get_slice_for_thumbnail(existing, frame, file_stop):
    assert 0 <= frame < file_stop
    if frame in existing:
        return None
    start = walk_backward(existing, frame)
    end = walk_forward(existing, frame, file_stop)
    if start < frame and end == frame:
        start = walk_backward(existing, start, steps=8)
    elif end > frame and start == frame:
        end = walk_forward(existing, end, file_stop, steps=8)
    return StartStop(start, end + 1)


class Thumbnailer(Decoder):
    def __init__(self, callback, filename, indexes, attachments):
        super().__init__(callback, filename, video=True)
        self.indexes = sorted(set(indexes))
        self.attachments = attachments
        self.changed = False
        self.target = None

        # Create elements
        self.convert = make_element('videoconvert')
        self.scale = make_element('videoscale', {'method': 2})
        self.enc = make_element('jpegenc', {'idct-method': 2})
        self.sink = make_element('fakesink', {'signal-handoffs': True})

        # Add elements to pipeline and link:
        add_elements(self.pipeline,
            self.convert, self.scale, self.enc, self.sink
        )
        self.video_q.link(self.convert)
        self.convert.link(self.scale)
        caps = make_caps('video/x-raw',
            {'pixel-aspect-ratio': '1/1', 'height': 108, 'format': 'I420'}
        )
        self.scale.link_filtered(self.enc, caps)
        self.enc.link(self.sink)

        # Connect signal handlers using Pipeline.connect():
        self.connect(self.sink, 'handoff', self.on_handoff)

    def run(self):
        self.set_state(Gst.State.PAUSED, sync=True)
        self.next()
        self.set_state(Gst.State.PLAYING)

    def seek_by_frame(self, frame):
        log.info('seeking to frame %d', frame)
        self.target = frame
        super().seek_by_frame(frame, key_unit=True)

    def next(self):
        while self.indexes:
            frame = self.indexes.pop(0)
            if str(frame) in self.attachments:
                log.info('next: already have frame %d', frame)
            else:
                self.seek_by_frame(frame)
                return
        self.complete(True)

    def on_handoff(self, element, buf, pad):
        frame = nanosecond_to_frame(buf.pts, self.framerate)
        key = str(frame)
        if key in self.attachments:
            log.info('Already have frame %d', frame)
        else:
            self.changed = True
            data = buf.extract_dup(0, buf.get_size())
            self.attachments[key] = {
                'content_type': 'image/jpeg',
                'data': b64encode(data).decode(),
            }
            log.info('Created thumbnail for frame %d', frame)
        if frame >= self.target + 5:
            GLib.idle_add(self.next)

    def on_eos(self, bus, msg):
        log.debug('Got EOS from message bus')
        self.complete(True)

