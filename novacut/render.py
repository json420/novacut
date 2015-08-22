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

import os
from os import path
from fractions import Fraction
from collections import namedtuple
import weakref
from datetime import datetime
import queue
import logging

from gi.repository import GLib, Gst
from microfiber import Database, dumps

from .timefuncs import frame_to_nanosecond, nanosecond_to_frame, video_pts_and_duration, Timestamp
from .gsthelpers import (
    Pipeline,
    make_element,
    make_element_from_desc,
    get_framerate,
    make_caps,
    add_and_link_elements,
)

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

BUFFER_QUEUE_SIZE = 16
TYPE_ERROR = '{}: need a {!r}; got a {!r}: {!r}'
Slice = namedtuple('Slice', 'id src start stop filename')
Sequence = namedtuple('Sequence', 'id src')

log = logging.getLogger(__name__)
Gst.init()


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


class WeakMethod:
    __slots__ = ('proxy', 'method_name')

    def __init__(self, inst, method_name):
        if not callable(getattr(inst, method_name)):
            raise TypeError(
                '{!r} attribute is not callable'.format(method_name)
            )
        self.proxy = weakref.proxy(inst)
        self.method_name = method_name

    def __call__(self, *args):
        try:
            method = getattr(self.proxy, self.method_name)
        except ReferenceError:
            return
        return method(*args)
  

def get_expected_ts(frame, framerate):
    return video_pts_and_duration(frame, frame + 1, framerate)


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


class Validator(Pipeline):
    def __init__(self, filename, full_check=False):
        super().__init__()
        self.bus.connect('message::eos', WeakMethod(self, 'on_eos'))

        # Create elements
        src = self.make_element('filesrc', {'location': filename})
        dec = self.make_element('decodebin')
        self.sink = self.make_element('fakesink', {'signal-handoffs': True})

        # Connect signal handlers
        dec.connect('pad-added', WeakMethod(self, 'on_pad_added'))
        self.sink.connect('handoff', WeakMethod(self, 'on_handoff'))

        # Link elements
        src.link(dec)

        self.frame = 0
        self.framerate = None
        self.info = {'valid': True}
        self.full_check = full_check

    def mark_invalid(self):
        self.info['valid'] = False
        if not self.full_check:
            self.fatal('Stopping check at first inconsistency')

    def run(self):
        self.set_state('PAUSED', sync=True)
        (success, ns) = self.pipeline.query_duration(Gst.Format.TIME)
        if not success:
            self.fatal('Could not query duration')
        log.info('duration: %d ns', ns)
        self.info['duration'] = ns
        self.set_state('PLAYING')

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
                pad.link(self.sink.get_static_pad('sink'))
            else:
                self.fatal('error getting framerate/width/height from video caps')

    def on_handoff(self, sink, buf, pad):
        ts = Timestamp(buf.pts, buf.duration)
        expected_ts = get_expected_ts(self.frame, self.framerate)
        if self.frame == 0 and ts.pts != 0:
            log.warning('non-zero PTS at frame 0: %r', ts)
            self.mark_invalid()
        elif ts != expected_ts:
            log.warning('Timestamp mismatch at frame %d:\n%s',
                self.frame, format_ts_mismatch(ts, expected_ts)
            )
            self.mark_invalid()
        self.frame += 1

    def on_eos(self, bus, msg):
        log.info('eos')
        frames = self.frame
        info = self.info
        info['frames'] = self.frame
        expected_duration = frame_to_nanosecond(frames, self.framerate)
        if info['duration'] != expected_duration:
            log.warning('total duration: %d != %d',
                info['duration'], expected_duration
            )
            info['valid'] = False
        if info['valid'] is True:
            log.info('Success, this is a conforming video!')
        else:
            log.warning('This is not a conforming video!')
        self.destroy()


class Input(Pipeline):
    def __init__(self, callback, buffer_queue, s, input_caps):
        super().__init__(callback)
        self.buffer_queue = buffer_queue
        assert 0 <= s.start < s.stop
        self.s = s
        self.frame = s.start
        self.framerate = None
        self.drained = False
        self.bus.connect('message::eos', self.on_eos)

        # Create elements
        src = make_element('filesrc', {'location': s.filename})
        dec = make_element('decodebin')
        self.q = make_element('queue')
        convert = make_element('videoconvert')
        scale = make_element('videoscale', {'method': 3})
        appsink = make_element('appsink',
            {
                'caps': input_caps,
                'emit-signals': True,
                'max-buffers': BUFFER_QUEUE_SIZE,
            }
        )

        # Add elements to pipeline and link:
        add_and_link_elements(self.pipeline, src, dec)
        add_and_link_elements(self.pipeline, self.q, convert, scale, appsink)

        # Connect element signal handlers:
        dec.connect('pad-added', self.on_pad_added)
        appsink.connect('new-sample', self.on_new_sample)

    def run(self):
        log.info('starting slice %s: %s[%s:%s]',
            self.s.id, self.s.src, self.s.start, self.s.stop
        )
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
        log.info('on_pad_added(): %s', string)
        if string.startswith('video/'):
            self.framerate = get_framerate(caps.get_structure(0))
            log.info('framerate: %r', self.framerate)
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
        buf = appsink.emit('pull-sample').get_buffer()
        if NEEDS_YUCKY_COPY:  # See "FIXME: NEEDS_YUCKY_COPY?" at top of module:
            buf = buf.copy()
        if self.check_frame(buf) is not True:
            GLib.idle_add(self.complete, False)  
            return Gst.FlowReturn.CUSTOM_ERROR
        self.buffer_queue.put(buf)
        self.frame += 1
        if self.frame == self.s.stop:
            log.info('finished slice %s: %s[%s:%s]',
                self.s.id, self.s.src, self.s.start, self.s.stop
            )
            self.drained = True
            GLib.idle_add(self.complete, True)
        return Gst.FlowReturn.OK

    def on_eos(self, bus, msg):
        if self.drained is not True:
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
        log.info('Output.on_eos()')
        self.complete(True)

    def on_need_data(self, appsrc, amount):
        if self.sent_eos:
            log.info('sent_eos is True, nothing to do in need-need callback')
            return
        for i in range(BUFFER_QUEUE_SIZE):
            if self.push(appsrc, self.buffer_queue.get()) is True:
                break
        log.info('output frame %s', self.frame)

    def push(self, appsrc, buf):
        if buf is None:
            log.info('received end-of-render sentinel')
            appsrc.emit('end-of-stream')
            self.sent_eos = True
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
        self.expected_frames = sum(s.stop - s.start for s in slices)
        self.buffer_queue = queue.Queue(BUFFER_QUEUE_SIZE)
        self.input = None
        self.output = Output(
            self.on_output_complete, self.buffer_queue, settings, filename
        )
        self.input_caps = self.output.input_caps

    def run(self):
        self.slices_iter = iter(self.slices)
        self.output.run()
        self.next()

    def complete(self, success):
        log.info('Manager complete, success=%r', success)
        if self.input is not None:
            self.input.destroy()
            self.input = None
        if self.output is not None:
            self.output.destroy()
            self.output = None
        self.success = success
        self.callback(self, success)

    def next_slice(self):
        try:
            return next(self.slices_iter)
        except StopIteration:
            return None

    def next(self):
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
        log.info('input complete, success=%r', success)
        assert inst is self.input
        if success is True:
            self.input = None
            self.next()
        else:
            self.complete(False)

    def on_output_complete(self, inst, success):
        log.info('output complete, success=%r', success)
        assert inst is self.output
        self.complete(success)


class Worker:
    def __init__(self, Dmedia, env):
        self.Dmedia = Dmedia
        self.novacut_db = Database('novacut-1', env)
        self.dmedia_db = Database('dmedia-1', env)

    def run(self, job_id):
        job = self.novacut_db.get(job_id)
        log.info('Rendering: %s', dumps(job, pretty=True))
        settings = self.novacut_db.get(job['node']['settings'])
        log.info('With settings: %s', dumps(settings['node'], pretty=True))

        root_id = job['node']['root']
        slices = SliceIter(self.Dmedia, self.novacut_db, root_id)

        dst = self.Dmedia.AllocateTmp()
        renderer = Manager(slices, settings['node'], dst)
        renderer.run()
        if renderer.error:
            raise SystemExit('renderer encountered a fatal error')
        if path.getsize(dst) < 1:
            raise SystemExit('file-size is zero for {}'.format(job_id))

        obj = self.Dmedia.HashAndMove(dst, 'render')
        _id = obj['file_id']
        doc = self.dmedia_db.get(_id)
        doc['render_of'] = job_id

        # Create the symlink
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if settings['node'].get('ext'):
            ts += '.' + settings['node']['ext']

        home = path.abspath(os.environ['HOME'])
        name = path.join('Novacut', ts)
        link = path.join(home, name)
        d = path.dirname(link)
        if not path.isdir(d):
            os.mkdir(d)
        target = obj['file_path']
        os.symlink(target, link)
        doc['link'] = name

        self.dmedia_db.save(doc)
        job['renders'][_id] = {
            'bytes': doc['bytes'],
            'time': doc['time'],
            'link': name,
        }
        self.novacut_db.save(job)

        obj['link'] = name


        return obj

