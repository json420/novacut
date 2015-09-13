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

from gi.repository import GLib, Gst

from .timefuncs import nanosecond_to_frame
from .gsthelpers import (
    Decoder,
    make_element,
    add_elements,
    make_caps,
)


log = logging.getLogger(__name__)


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

