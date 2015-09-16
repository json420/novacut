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
Realtime preview playback of a (flattened) Novacut edit graph.
"""

from fractions import Fraction
from queue import Queue, Full, Empty
import logging

from gi.repository import GLib, Gst

from .timefuncs import video_pts_and_duration
from .gsthelpers import Decoder, Pipeline, make_element, add_and_link_elements


log = logging.getLogger(__name__)
QUEUE_SIZE = 16
PREROLL_COUNT = 2


class SliceDecoder(Decoder):
    def __init__(self, callback, sample_queue, s):
        super().__init__(callback, s.filename, video=True)
        self.sample_queue = sample_queue
        assert 0 <= s.start < s.stop
        self.s = s
        self.frame = s.start
        self.isprerolled = False

        # Create elements
        self.sink = make_element('appsink',
            {'emit-signals': True, 'max-buffers': 1}
        )

        # Add elements to pipeline and link:
        self.pipeline.add(self.sink)
        self.video_q.link(self.sink)

        # Connect signal handlers using Pipeline.connect():
        self.connect(self.sink, 'new-sample', self.on_new_sample)

    def preroll(self):
        self.set_state(Gst.State.PAUSED, sync=True)
        if self.framerate is None:
            log.info('%s.preroll(): no framerate', self.__class__.__name__)
            self.complete(False)
        else:
            self.seek_by_frame(self.s.start, self.s.stop)
            self.isprerolled = True

    def run(self):
        assert self.isprerolled is True
        self.set_state(Gst.State.PLAYING)

    def on_new_sample(self, appsink):
        try:
            if self.frame >= self.s.stop:
                return Gst.FlowReturn.CUSTOM_ERROR
            sample = appsink.emit('pull-sample')
            self.frame += 1
            while self.success is None:
                try:
                    self.sample_queue.put(sample, timeout=0.1)
                    if self.frame >= self.s.stop:
                        self.complete(True)
                    return Gst.FlowReturn.OK
                except Full:
                    pass
            return Gst.FlowReturn.CUSTOM_ERROR
        except:
            log.exception('%s.on_new_sample():', self.__class__.__name__)
            self.complete(False)
            raise

    def on_eos(self, bus, msg):
        log.info('%s.on_eos()', self.__class__.__name__)
        if self.success is None:
            self.complete(False)


class VideoSink(Pipeline):
    def __init__(self, callback, sample_queue, xid):
        super().__init__(callback)
        self.sample_queue = sample_queue
        self.xid = xid
        self.frame = 0
        self.sent_eos = False
        self.framerate = Fraction(30000, 1001)
        self.misses = 0

        # Create elements:
        self.src = make_element('appsrc', {'format': 3})
        self.q = make_element('queue')
        self.sink = make_element('xvimagesink',
            {'double-buffer': True, 'show-preroll-frame': False}
        )

        # Add elements to pipeline and link:
        add_and_link_elements(self.pipeline, self.src, self.q, self.sink)

        # Connect signal handlers using Pipeline.connect():
        self.bus.enable_sync_message_emission()
        self.connect(self.bus, 'sync-message::element', self.on_sync_message)
        self.connect(self.src, 'need-data', self.on_need_data)

    def run(self):
        GLib.timeout_add(50, self.wait_for_queue_to_fill)

    def wait_for_queue_to_fill(self):
        if self.sample_queue.full():
            GLib.timeout_add(5000, self.set_state, Gst.State.PLAYING)
            return False
        log.info('waiting for sample queue to fill...')
        return True

    def on_eos(self, bus, msg):
        self.complete(True)

    def on_sync_message(self, bus, msg):
        if msg.get_structure().get_name() == 'prepare-window-handle':
            log.info('setting xid %r', self.xid)
            self.bus.disable_sync_message_emission()
            msg.src.set_window_handle(self.xid)

    def get_sample(self):
        while self.success is None:
            try:
                return self.sample_queue.get(timeout=0.05)
            except Empty:
                self.misses += 1
                log.warning('miss %d', self.misses)

    def on_need_data(self, appsrc, amount):
        try:
            if self.sent_eos:
                log.info('sent_eos is True, ignoring need-data signal')
                return
            sample = self.get_sample()
            if sample is None:
                log.info('received end-of-render sentinel')
                self.sent_eos = True
                appsrc.emit('end-of-stream')
                return
            ts = video_pts_and_duration(self.frame, self.framerate)
            self.frame += 1
            buf = sample.get_buffer()
            buf.pts = ts.pts
            buf.duration = ts.duration
            appsrc.emit('push-sample', sample)    
        except:
            log.exception('%s.on_need_data():', self.__class__.__name__)
            self.complete(False)
            raise


class Player:
    def __init__(self, callback, slices, xid):
        if not callable(callback):
            raise TypeError(
                'callback: not callable: {!r}'.format(callback)
            )
        self.callback = callback
        self.slices = list(slices)
        self.success = None
        self.total_frames = sum(s.stop - s.start for s in slices)
        self.sample_queue = Queue(QUEUE_SIZE)
        self.prerolled = []
        self.input = None
        self.output = VideoSink(self.on_output_complete, self.sample_queue, xid)

    def next_preroll(self):
        if not self.slices:
            return False
        s = self.slices.pop(0)
        dec = SliceDecoder(self.on_input_complete, self.sample_queue, s)
        dec.preroll()
        self.prerolled.append(dec)
        return True

    def init_preroll(self):
        for i in range(PREROLL_COUNT):
            if not self.next_preroll():
                break

    def next(self):
        if self.success is not None:
            log.error('Ignoring call to Player.next()')
            return
        if not self.prerolled:
            self.sample_queue.put(None)
        else:
            if self.input is not None:
                self.input.destroy()
                self.input = None
            self.input = self.prerolled.pop(0)
            self.input.run()
            self.next_preroll()

    def run(self):
        log.info('**** Plaing %s slices, %s frames...',
            len(self.slices), self.total_frames
        )
        self.init_preroll()
        self.next()
        self.output.run()

    def destroy(self):
        if self.success is not True:
            self.success = False
        log.info('%s.destroy()', self.__class__.__name__)
        while self.prerolled:
            dec = self.prerolled.pop(0)
            dec.destroy()
        if self.input is not None:
            self.input.destroy()
            self.input = None
        if self.output is not None:
            self.output.destroy()
            self.output = None

    def complete(self, success):
        log.info('%s.complete()', self.__class__.__name__)
        self.success = (True if success is True else False)
        self.destroy()
        if self.success is True:
            log.info('**** Played %s slices, %s frames!',
                len(self.slices), self.total_frames
            )
        self.callback(self, self.success)

    def on_input_complete(self, inst, success):
        if success is True:
            self.next()
        else:
            self.complete(False)

    def check_output_frames(self):
        if self.total_frames == self.output.frame:
            log.info('Output received all %s frames from Input!',
                self.total_frames
            )
            return True
        log.error('Expected %s total frames, output received %s',
            self.total_frames, self.output.frame
        )
        return False

    def on_output_complete(self, inst, success):
        assert inst is self.output
        if success is True and self.check_output_frames() is True:
            self.complete(True)
        else:
            self.complete(False)

