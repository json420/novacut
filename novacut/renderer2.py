# novacut: the distributed video editor
# Copyright (C) 2015 Novacut Inc
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

import os
from os import path
from fractions import Fraction
import logging
from hashlib import sha1
from collections import namedtuple

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst

from .timefuncs import frame_to_nanosecond, nanosecond_to_frame
from .misc import random_slice

Gst.init(None)
mainloop = GLib.MainLoop()

_format = [
    '%(levelname)s',
    '%(threadName)s',
    '%(message)s',
]
logging.basicConfig(
    level=logging.DEBUG,
    format='\t'.join(_format),
)
log = logging.getLogger()


#class Encoder:
#    def prerolled(self, src):
#        pass

#    def

Info = namedtuple('Info', 'filename framerate start stop')


class VideoSlice:
    def __init__(self, info, helper):
        assert info.start < info.stop
        self.info = info
        self.helper = helper
        self.cur = info.start

        self.pipeline = Gst.Pipeline()
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::segment-done', self.on_segment_done)
        self.bus.connect('message::eos', self.on_eos)
        self.bus.connect('message::error', self.on_error)

        # Create elements
        self.src = Gst.ElementFactory.make('filesrc', None)
        self.dec = Gst.ElementFactory.make('decodebin', None)
        self.sink = Gst.ElementFactory.make('appsink', None)

        # Add elements to pipeline
        for element in (self.src, self.dec, self.sink):        
            self.pipeline.add(element)

        # Set properties
        self.src.set_property('location', info.filename)
        self.sink.set_property('emit-signals', True)

        # Connect signal handlers
        self.dec.connect('pad-added', self.on_pad_added)
        self.dec.connect('no-more-pads', self.on_no_more_pads)
        self.dec.connect('drained', self.on_drained)
        self.sink.connect('new-preroll', self.on_new_preroll)
        self.sink.connect('new-sample', self.on_new_sample)

        # Link elements
        self.src.link(self.dec)

    def destroy(self):
        self.pipeline.set_state(Gst.State.NULL)

    def run(self):
        self.pipeline.set_state(Gst.State.PAUSED)
        self.pipeline.get_state(Gst.CLOCK_TIME_NONE)
        self.pipeline.seek(
            1.0,  # rate
            Gst.Format.TIME,        
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.SEGMENT | Gst.SeekFlags.ACCURATE,
            Gst.SeekType.SET,
            frame_to_nanosecond(self.info.start, self.info.framerate),
            Gst.SeekType.SET,
            frame_to_nanosecond(self.info.stop, self.info.framerate),
        )
        self.pipeline.set_state(Gst.State.PLAYING)

    def on_pad_added(self, dec, pad):
        caps = pad.get_current_caps()
        string = caps.to_string()
        #log.info('on_pad_added(): %s', string)
        if string.startswith('video/'):
            pad.link(self.sink.get_static_pad('sink'))

    def on_no_more_pads(self, dec):
        log.info('on_no_more_pads()')

    def on_drained(self, dec):
        log.info('on_drained()')

    def on_new_preroll(self, sink):
        log.info('on_new_preroll()')
        return Gst.FlowReturn.OK

    def _fatal(self):
        log.info('shuting down after fatal error')
        self.destroy()
        mainloop.quit()

    def fatal(self, msg, *args):
        log.error(msg, *args)
        GLib.idle_add(self._fatal)

    def on_new_sample(self, sink):
        buf = sink.get_property('last-sample').get_buffer()
        cur = nanosecond_to_frame(buf.pts, self.info.framerate)
        data = buf.extract_dup(0, buf.get_size())
        h = sha1(data).hexdigest()
        log.info('new-sample: %s [%s:%s] @%s',
            h, self.info.start, self.info.stop, cur
        )

        if self.cur != cur:
            self.fatal('cur: %s != %s', self.cur, cur)
        if not (self.info.start <= cur < self.info.stop):
            self.fatal('false inequality: %s <= %s < %s',
                self.info.start, cur, self.info.stop
            )

        if cur not in self.helper.hashes:
            self.helper.hashes[cur] = h
        elif self.helper.hashes[cur] != h:
            self.fatal('hash mismatch: %s: %s != %s',
                cur, self.helper.hashes[cur], h
            )

        self.cur += 1
        if self.cur == self.info.stop:
            log.info('last frame in slice')
            GLib.idle_add(self.helper.on_stop)
        return Gst.FlowReturn.OK

    def on_segment_done(self, bus, msg):
        log.info('on_segment_done')

    def on_eos(self, bus, msg):
        log.info('on_eos()')

    def on_error(self, bus, msg):
        self.fatal('on_error: %s', msg.parse_error())



class Helper:
    def __init__(self, filename, framerate):
        self.filename = filename
        self.framerate = framerate
        self.hashes = {}
        self.count = 0

    def next_slice(self):
        (start, stop) = random_slice(107)
        return Info(self.filename, self.framerate, start, stop)

    def start(self):
        self.count += 1
        log.info('**** slice %s ****', self.count)
        self.slice = VideoSlice(self.next_slice(), self)
        self.slice.run()

    def on_stop(self):
        log.info('Helper.on_stop()')
        self.slice.destroy()
        del self.slice
        self.start()

filename = path.join(path.dirname(path.dirname(path.abspath(__file__))), 'MVI_5751.MOV')
framerate = Fraction(30000, 1001)


if __name__ == '__main__':


    test = Helper(filename, framerate)
    test.start()
    mainloop.run()
