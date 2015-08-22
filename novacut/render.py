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

from fractions import Fraction
from collections import namedtuple
import queue
import logging

from gi.repository import Gst

from .timefuncs import frame_to_nanosecond, nanosecond_to_frame, video_pts_and_duration
from .gsthelpers import (
    Pipeline,
    make_element,
    make_element_from_desc,
    get_framerate,
    make_caps,
    add_and_link_elements,
)


log = logging.getLogger(__name__)
TYPE_ERROR = '{}: need a {!r}; got a {!r}: {!r}'
Slice = namedtuple('Slice', 'id src start stop filename')

# FIXME: NEEDS_YUCKY_COPY?
#
# In GStreamer 1.2 (Trusty), appsink.emit('pull-sample') is, at least from the
# Python GI perspective, returning the same buffer object *every* time.
# Presumably it isn't actually reusing the same underlying memory region on the
# C side, as that fundamentally breaks the GStreamer data model.
#
# But the symptom is this: if Output.push() sets buf.pts, buf.duration just
# before Input.on_new_sample() reads buf.pts, buf.duration from (what should be)
# the unique and unrelated buffer returned by
# appsink.emit('pull-sample').get_buffer(), Input.on_new_sample() will fail
# because it thinks it received the wrong frame... a frame with the exact same
# timestamps just set by Output.push().
#
# The only work-around known currently is to copy the buffer, which of course
# we normally would never want to do.  A very yucky copy indeed.
NEEDS_YUCKY_COPY = (True if Gst.version() < (1, 4) else False)


def _get(d, key, t):
    assert type(d) is dict
    val = d.get(key)
    if type(val) is not t:
        raise TypeError(TYPE_ERROR.format(key, t, type(val), val))
    return val


def _int(d, key, minval=None):
    val = _get(d, key, int)
    if minval is not None:
        assert type(minval) is int
        if val < minval:
            raise ValueError(
                'need {!r} >= {}; got {}'.format(key, minval, val)
            )
    return val


def _str(d, key):
    return _get(d, key, str)


def _dict(d, key):
    return _get(d, key, dict)


def _fraction(obj):
    if isinstance(obj, Fraction):
        return obj
    elif isinstance(obj, dict):
        return Fraction(
            _int(obj, 'num',   1),
            _int(obj, 'denom', 1)
        )
    else:
        raise TypeError(
            'invalid fraction: {!r}: {!r}'.format(type(obj), obj)
        )


class Input(Pipeline):
    def __init__(self, callback, buffer_queue, s, input_caps):
        super().__init__(callback)
        self.buffer_queue = buffer_queue
        assert 0 <= s.start < s.stop
        self.s = s
        self.frame = s.start
        self.framerate = None
        self.bus.connect('message::eos', self.on_eos)

        # Create elements
        src = make_element('filesrc', {'location': s.filename})
        dec = make_element('decodebin')
        self.q = make_element('queue')
        convert = make_element('videoconvert')
        scale = make_element('videoscale', {'method': 3})
        appsink = make_element('appsink',
            {'caps': input_caps, 'emit-signals': True, 'max-buffers': 8}
        )

        # Add elements to pipeline and link:
        add_and_link_elements(self.pipeline, src, dec)
        add_and_link_elements(self.pipeline, self.q, convert, scale, appsink)

        # Connect element signal handlers:
        dec.connect('pad-added', self.on_pad_added)
        appsink.connect('new-sample', self.on_new_sample)

    def run(self):
        log.info('Input slice %s[%s:%s]', self.s.src, self.s.start, self.s.stop)
        self.set_state(Gst.State.PAUSED, sync=True)
        self.pipeline.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
            frame_to_nanosecond(self.s.start, self.framerate)
        )
        self.set_state(Gst.State.PLAYING)

    def on_pad_added(self, dec, pad):
        caps = pad.get_current_caps()
        string = caps.to_string()
        if string.startswith('video/'):
            self.framerate = get_framerate(caps.get_structure(0))
            pad.link(self.q.get_static_pad('sink'))

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
        buf = appsink.emit('pull-sample').get_buffer()
        if NEEDS_YUCKY_COPY:  # See "FIXME: NEEDS_YUCKY_COPY?" at top of module:
            buf = buf.copy()
        if self.check_frame(buf) is not True:
            self.complete(False)
            return Gst.FlowReturn.CUSTOM_ERROR
        while self.success is None:
            try:
                self.buffer_queue.put(buf, timeout=2)
                break
            except queue.Full:
                pass
        self.frame += 1
        if self.frame == self.s.stop:
            self.complete(True)
        return Gst.FlowReturn.OK

    def on_eos(self, bus, msg):
        if self.frame < self.s.stop:
            log.error('recieved EOS before end of slice, some frame were lost')
            self.complete(False)


def make_video_caps(desc):
    framerate = _fraction(desc.pop('framerate'))
    _int(desc, 'width', 32)
    _int(desc, 'height', 32)
    _str(desc, 'format')
    _str(desc, 'interlace-mode')
    _str(desc, 'pixel-aspect-ratio')
    assert 'framerate' not in desc
    input_caps = make_caps('video/x-raw', desc)
    desc['framerate'] = framerate
    output_caps = make_caps('video/x-raw', desc)
    return (framerate, input_caps, output_caps)


class Output(Pipeline):
    def __init__(self, callback, buffer_queue, settings, filename):
        super().__init__(callback)
        self.bus.connect('message::eos', self.on_eos)
        self.buffer_queue = buffer_queue
        self.frame = 0
        self.sent_eos = False

        desc = settings['video']['caps']
        (self.framerate, self.input_caps, output_caps) = make_video_caps(desc)

        # Create elements:
        appsrc = make_element('appsrc', {'caps': output_caps, 'format': 3})
        q1 = make_element('queue')
        enc = make_element_from_desc(settings['video']['encoder'])
        q2 = make_element('queue')
        mux = make_element_from_desc(settings['muxer'])
        sink = make_element('filesink', {'location': filename})

        # Add elements to pipeline and link:
        add_and_link_elements(self.pipeline, appsrc, q1, enc, q2, mux, sink)

        # Connect element signal handlers:
        appsrc.connect('need-data', self.on_need_data)

    def run(self):
        self.set_state(Gst.State.PLAYING)

    def on_eos(self, bus, msg):
        self.complete(True)

    def on_need_data(self, appsrc, amount):
        if self.sent_eos:
            log.info('sent_eos is True, nothing to do in need-data callback')
            return

        # We need to block on Queue.get() for the first buffer because if we
        # don't push at least one buffer, "need-data" wont fire again:
        if self.push(appsrc, self.buffer_queue.get()) is True:
            return

        # But as long as we're here, we'd like to push quite a few buffers, but
        # for the remaining ones we wont block on Queue.get():
        for i in range(17):
            try:
                buf = self.buffer_queue.get(block=False)
            except queue.Empty:
                break
            if self.push(appsrc, buf) is True:
                break
        #log.info('pushed %s frames', i + 2)

    def push(self, appsrc, buf):
        assert self.sent_eos is False
        if buf is None:
            log.info('Output: received end-of-render sentinel')
            self.sent_eos = True
            appsrc.emit('end-of-stream')
            return True
        ts = video_pts_and_duration(self.frame, self.frame + 1, self.framerate)
        buf.pts = ts.pts
        buf.duration = ts.duration
        appsrc.emit('push-buffer', buf)
        self.frame += 1
        return False


class Renderer:
    def __init__(self, callback, slices, settings, filename):
        if not callable(callback):
            raise TypeError(
                'callback: not callable: {!r}'.format(callback)
            )
        self.callback = callback
        self.slices = slices
        self.success = None
        self.total_frames = sum(s.stop - s.start for s in slices)
        self.buffer_queue = queue.Queue(24)
        self.input = None
        self.output = Output(
            self.on_output_complete, self.buffer_queue, settings, filename
        )
        self.input_caps = self.output.input_caps

    def run(self):
        log.info('**** Rendering %s slices, %s frames...',
            len(self.slices), self.total_frames
        )
        self.slices_iter = iter(self.slices)
        self.output.run()
        self.next()

    def destroy(self):
        log.info('Renderer.destroy()')

        # First shutdown the Input pipeline, as we want to prevent it from
        # putting further items into the queue because of some trickiness below:
        if self.input is not None:
            self.input.destroy()
            self.input = None

        # Then shutdown the Output pipeline, but very carefully: we must first
        # *try* putting the end-of-render sentinel into the queue before we call
        # Output.destroy(), otherwise Output.pipeline.set_state(Gst.State.NULL)
        # can deadlock if Output.on_need_data() happens to be waiting for an
        # item from the queue:
        if self.output is not None:
            try:
                self.buffer_queue.put(None, timeout=2)
            except queue.Full:
                log.warning('Could not add pre-destroy end-of-render sentinel')
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
            self.input = Input(
                self.on_input_complete, self.buffer_queue, s, self.input_caps
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
            return True
        log.error('expected %s total frames, output recieved %s',
            self.total_frames, self.output.frame
        )
        return False

    def on_output_complete(self, inst, success):
        assert inst is self.output
        if success is True and self.check_output_frames() is True:
            self.complete(True)
        else:
            self.complete(False)

