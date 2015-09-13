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
Realtime preview playback of a Novacut edit graph.
"""

import queue
import logging
from fractions import Fraction

from gi.repository import GLib, Gst

from .timefuncs import nanosecond_to_frame, video_pts_and_duration
from .gsthelpers import Decoder, Pipeline, make_element, add_and_link_elements

log = logging.getLogger(__name__)


class SliceDecoder(Decoder):
    def __init__(self, callback, buffer_queue, s):
        super().__init__(callback, s.filename, video=True)
        self.buffer_queue = buffer_queue
        assert 0 <= s.start < s.stop
        self.s = s
        self.frame = s.start

        # Create elements
        self.sink = make_element('appsink',
            {'emit-signals': True, 'max-buffers': 4}
        )

        # Add elements to pipeline and link:
        self.pipeline.add(self.sink)
        self.video_q.link(self.sink)

        # Connect signal handlers using Pipeline.connect():
        self.connect(self.sink, 'new-sample', self.on_new_sample)

    def run(self):
        log.info('%s[%s:%s]', self.s.src, self.s.start, self.s.stop)
        self.set_state(Gst.State.PAUSED, sync=True)
        self.seek_to_frame(self.s.start)
        self.set_state(Gst.State.PLAYING)

    def check_frame(self, buf):
        frame = nanosecond_to_frame(buf.pts, self.framerate)
        if self.frame == frame:
            return True
        log.error('expected frame %s, got %s from slice %s: %s[%s:%s]',
            self.frame, frame, self.s.id, self.s.src, self.s.start, self.s.stop
        )
        return False

    def on_new_sample(self, appsink):
        if self.frame >= self.s.stop:
            log.warning('Ignoring extra frames past end of slice')
            return Gst.FlowReturn.EOS
        if self.success is not None:
            log.warning(
                'Ignoring frame received after Input.complete() was called'
            )
            return Gst.FlowReturn.EOS
        buf = appsink.emit('pull-sample').get_buffer()
        if self.check_frame(buf) is not True:
            self.complete(False)
            return Gst.FlowReturn.CUSTOM_ERROR
        self.frame += 1
        while self.success is None:
            try:
                self.buffer_queue.put(buf, timeout=0.25)
                break
            except queue.Full:
                pass
        if self.frame >= self.s.stop:
            self.complete(True)
        return Gst.FlowReturn.OK

    def on_eos(self, bus, msg):
        if self.frame < self.s.stop:
            log.error('missing %d frames', self.s.stop - self.frame)
            self.complete(False)


class VideoSink(Pipeline):
    def __init__(self, callback, buffer_queue, xid):
        super().__init__(callback)
        self.buffer_queue = buffer_queue
        self.xid = xid
        self.frame = 0
        self.sent_eos = False
        self.framerate = Fraction(30000, 1001)

        # Create elements:
        caps = Gst.caps_from_string('video/x-raw, format=(string)I420, width=(int)1920, height=(int)1080, interlace-mode=(string)progressive, pixel-aspect-ratio=(fraction)1/1, chroma-site=(string)mpeg2, colorimetry=(string)bt709, framerate=(fraction)30000/1001')

        self.src = make_element('appsrc', {'caps': caps, 'format': 3})
        self.q = make_element('queue')
        self.sink = make_element('xvimagesink', {'double-buffer': True})
        #self.sink = make_element('autovideosink')

        # Add elements to pipeline and link:
        add_and_link_elements(self.pipeline, self.src, self.q, self.sink)

        # Connect signal handlers using Pipeline.connect():
        self.bus.enable_sync_message_emission()
        self.connect(self.bus, 'sync-message::element', self.on_sync_message)
        self.connect(self.src, 'need-data', self.on_need_data)

    def run(self):
        GLib.timeout_add(100, self.wait_for_queue_to_fill)

    def wait_for_queue_to_fill(self):
        log.info('wating for queue...')
        if self.buffer_queue.full():
            self.set_state(Gst.State.PLAYING)
            return False
        return True

    def on_eos(self, bus, msg):
        self.complete(True)

    def on_sync_message(self, bus, msg):
        if msg.get_structure().get_name() == 'prepare-window-handle':
            log.info('setting xid %r', self.xid)
            self.bus.disable_sync_message_emission()
            msg.src.set_window_handle(self.xid)

    def iter_buffers(self):
        q = self.buffer_queue
        Empty = queue.Empty
        while self.success is None:
            try:
                yield q.get(timeout=0.25)
                break
            except Empty:
                pass
        for i in range(7):
            try:
                yield q.get(block=False)
            except Empty:
                break

    def on_need_data(self, appsrc, amount):
        if self.sent_eos:
            log.info('sent_eos is True, nothing to do in need-data callback')
            return
        for buf in self.iter_buffers():
            self.push(appsrc, buf)

    def push(self, appsrc, buf):
        assert self.sent_eos is False
        if buf is None:
            log.info('Output: received end-of-render sentinel')
            self.sent_eos = True
            appsrc.emit('end-of-stream')
            return
        ts = video_pts_and_duration(self.frame, self.framerate)
        buf.pts = ts.pts
        buf.duration = ts.duration
        appsrc.emit('push-buffer', buf)
        self.frame += 1


class Player:
    def __init__(self, callback, slices, xid):
        if not callable(callback):
            raise TypeError(
                'callback: not callable: {!r}'.format(callback)
            )
        self.callback = callback
        self.slices = slices
        self.success = None
        self.total_frames = sum(s.stop - s.start for s in slices)
        self.buffer_queue = queue.Queue(32)
        self.input = None
        self.output = VideoSink(self.on_output_complete, self.buffer_queue, xid)

    def run(self):
        log.info('**** Plaing %s slices, %s frames...',
            len(self.slices), self.total_frames
        )
        self.output.run()
        self.slices_iter = iter(self.slices)
        self.next()

    def destroy(self):
        log.info('Renderer.destroy()')
        if self.input is not None:
            self.input.destroy()
            self.input = None
        if self.output is not None:
            self.output.destroy()
            self.output = None

    def complete(self, success):
        log.info('Renderer.complete(%r)', success)
        if self.success is not None:
            log.error('Renderer.complete() already called, ignoring')
            return
        self.success = (True if success is True else False)
        self.destroy()
        if self.success is True:
            log.info('**** Rendered %s slices, %s frames!',
                len(self.slices), self.total_frames
            )
        self.callback(self, self.success)

    def next_slice(self):
        try:
            return next(self.slices_iter)
        except StopIteration:
            return None

    def next(self):
        if self.success is not None:
            log.error('Ignoring call to Renderer.next()')
            return
        assert self.input is None
        s = self.next_slice()
        if s is None:
            self.buffer_queue.put(None)
        else:
            self.input = SliceDecoder(
                self.on_input_complete, self.buffer_queue, s
            )
            self.input.run()

    def on_input_complete(self, inst, success):
        assert inst is self.input
        if success is True:
            self.input = None
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

