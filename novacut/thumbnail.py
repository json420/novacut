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

from gi.repository import Gst

from .gsthelpers import Pipeline, make_element, get_framerate, add_elements, link_elements


log = logging.getLogger(__name__)


class Thumbnailer(Pipeline):
    def __init__(self, callback, filename, frames):
        super().__init__(callback)
        self.frames = sorted(set(frames))
        self.framerate = None

        # Create elements
        self.src = make_element('filesrc', {'location': filename})
        self.dec = make_element('decodebin')
        self.convert = make_element('videoconvert')
        self.scale = make_element('videoscale', {'method': 3})
        self.enc = make_element('jpegenc', {'idct-method': 2})
        self.sink = make_element('fakesink', {'signal-handoffs': True})

        # Add elements to pipeline and link:
        add_elements(self.pipeline,
            self.src, self.dec, self.convert, self.scale, self.enc, self.sink
        )
        self.src.link(self.dec)
        link_elements(self.convert, self.scale, self.enc, self.sink)

        # Connect signal handlers using Pipeline.connect():
        self.connect(self.bus, 'message::eos', self.on_eos)
        self.connect(self.dec, 'pad-added', self.on_pad_added)
        self.connect(self.sink, 'handoff', self.on_handoff)

    def run(self):
        self.set_state(Gst.State.PAUSED, sync=True)
        self.set_state(Gst.State.PLAYING)

    def on_pad_added(self, dec, pad):
        caps = pad.get_current_caps()
        string = caps.to_string()
        log.debug('on_pad_added(): %s', string)
        if string.startswith('video/'):
            self.framerate = get_framerate(caps.get_structure(0))
            pad.link(self.convert.get_static_pad('sink'))

    def on_handoff(self, element, buf, pad):
        pass

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

