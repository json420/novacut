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

from gi.repository import GLib, Gst

from .timefuncs import nanosecond_to_frame, video_pts_and_duration
from .gsthelpers import (
    USE_HACKS,
    VIDEOSCALE_METHOD,
    Pipeline,
    Decoder,
    make_element,
    make_element_from_desc,
    make_caps,
    add_and_link_elements,
)


log = logging.getLogger(__name__)
QUEUE_SIZE = 16
TYPE_ERROR = '{}: need a {!r}; got a {!r}: {!r}'
Slice = namedtuple('Slice', 'id src start stop filename')


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


class Input(Decoder):
    # With GStreamer 1.2, we need the Input.check_eos() time to be fairly long:
    CHECK_EOS = 2000

    def __init__(self, callback, buffer_queue, s, input_caps):
        super().__init__(callback, s.filename, video=True)
        self.buffer_queue = buffer_queue
        assert 0 <= s.start < s.stop
        self.s = s
        self.frame = s.start

        # Create elements
        self.convert = make_element('videoconvert')
        self.scale = make_element('videoscale', {'method': VIDEOSCALE_METHOD})
        self.sink = make_element('appsink',
            {'caps': input_caps, 'emit-signals': True, 'max-buffers': 1}
        )

        # Add elements to pipeline and link:
        add_and_link_elements(self.pipeline,
            self.convert, self.scale, self.sink
        )
        self.video_q.link(self.convert)

        # Connect signal handlers using Pipeline.connect():
        self.connect(self.sink, 'new-sample', self.on_new_sample)

    def run(self):
        try:
            log.info('%s[%s:%s]', self.s.src, self.s.start, self.s.stop)
            self.set_state(Gst.State.PAUSED, sync=True)
            stop = (None if USE_HACKS else self.s.stop)
            self.seek_by_frame(self.s.start, stop)
            self.set_state(Gst.State.PLAYING)
        except:
            log.exception('%s.run():', self.__class__.__name__)
            self.complete(False)

    def check_frame(self, buf):
        frame = nanosecond_to_frame(buf.pts, self.framerate)
        if self.frame == frame:
            return True
        log.error('expected frame %s, got %s from slice %s: %s[%s:%s]',
            self.frame, frame, self.s.id, self.s.src, self.s.start, self.s.stop
        )
        return False

    def done(self):
        log.info('done: %s[%s:%s]', self.s.src, self.s.start, self.s.stop)
        self.remove_check_eos()
        self.do_complete(True)

    def on_new_sample(self, appsink):
        try:
            if self.frame >= self.s.stop:
                log.warning('Ignoring extra frames past end of slice')
                return Gst.FlowReturn.EOS
            buf = appsink.emit('pull-sample').get_buffer()
            if USE_HACKS:
                # FIXME: work-around needed for GStreamer 1.2
                buf = buf.copy()
            if self.check_frame(buf) is not True:
                self.complete(False)
                return Gst.FlowReturn.CUSTOM_ERROR
            self.frame += 1
            while self.success is None:
                try:
                    self.buffer_queue.put(buf, timeout=0.1)
                    if self.frame >= self.s.stop:
                        GLib.idle_add(self.done)
                    return Gst.FlowReturn.OK
                except queue.Full:
                    pass
            return Gst.FlowReturn.CUSTOM_ERROR
        except:
            log.exception('%s.on_new_sample():', self.__class__.__name__)
            self.complete(False)
            return Gst.FlowReturn.ERROR

    def check_eos(self):
        self.remove_check_eos()
        if self.success is not None:
            log.debug('check_eos(): complete() already called, nothing to do')
        elif self.frame >= self.s.stop:
            log.debug(
                'check_eos(): assuming on_new_sample() will call complete()'
            )
        else:
            log.warning('check_eos(): missing %d frames',
                self.s.stop - self.frame
            )
            self.do_complete(False)

    def on_eos(self, bus, msg):
        if self.success is None and self.frame < self.s.stop:
            log.warning('on_eos(): missing %d frames', self.s.stop - self.frame)
            self.add_check_eos()


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
        self.buffer_queue = buffer_queue
        self.frame = 0
        self.sent_eos = False

        desc = settings['video']['caps']
        (self.framerate, self.input_caps, output_caps) = make_video_caps(desc)

        # Create elements:
        self.src = make_element('appsrc', {'caps': output_caps, 'format': 3})
        self.q = make_element('queue')
        self.enc = make_element_from_desc(settings['video']['encoder'])
        self.mux = make_element_from_desc(settings['muxer'])
        self.sink = make_element('filesink',
            {'location': filename, 'buffer-mode': 2}
        )

        # Add elements to pipeline and link:
        add_and_link_elements(self.pipeline,
            self.src, self.q, self.enc, self.mux, self.sink
        )

        # Connect signal handlers using Pipeline.connect():
        self.connect(self.src, 'need-data', self.on_need_data)

    def run(self):
        GLib.timeout_add(3000, self.do_run)

    def do_run(self):
        if self.success is None:
            self.set_state(Gst.State.PLAYING)
        else:
            log.warning('do_run(): success in not None')

    def on_eos(self, bus, msg):
        self.complete(True)

    def get_buffer(self):
        q = self.buffer_queue
        while self.success is None:
            try:
                return q.get(timeout=0.1)
            except queue.Empty:
                pass
        raise Exception('Output.success is not None, wont wait for buffer')

    def on_need_data(self, appsrc, amount):
        try:
            if self.sent_eos:
                log.info('sent_eos is True, nothing to do in on_need_data()')
                return
            buf = self.get_buffer()
            if buf is None:
                log.info('Output: received end-of-render sentinel')
                self.sent_eos = True
                appsrc.emit('end-of-stream')
            else:
                ts = video_pts_and_duration(self.frame, self.framerate)
                buf.pts = ts.pts
                buf.duration = ts.duration
                self.frame += 1
                appsrc.emit('push-buffer', buf)
        except:
            log.exception('%s.on_need_data():', self.__class__.__name__)
            self.complete(False)


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
        self.buffer_queue = queue.Queue(QUEUE_SIZE)
        self.input = None
        self.output = Output(
            self.on_output_complete, self.buffer_queue, settings, filename
        )
        self.input_caps = self.output.input_caps

    def run(self):
        log.info('**** Rendering %s slices, %s frames...',
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

