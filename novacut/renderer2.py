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
from collections import namedtuple
import weakref
import logging

from gi.repository import GLib, Gst

from .timefuncs import frame_to_nanosecond, nanosecond_to_frame, video_pts_and_duration, Timestamp
from .misc import random_slice, random
from .gsthelpers import make_element, get_framerate_from_struct, make_caps, make_element_from_desc


Gst.init()
mainloop = GLib.MainLoop()


log = logging.getLogger(__name__)
TYPE_ERROR = '{}: need a {!r}; got a {!r}: {!r}'
Slice = namedtuple('Slice', 'id src start stop filename')
Sequence = namedtuple('Sequence', 'id src')


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


def _list(d, key, item_type=None, as_tuple=False):
    val = _get(d, key, list)
    if item_type is not None:
        for (i, item) in enumerate(val):
            if type(item) is not item_type:
                label = '{}[{}]'.format(key, i)
                raise TypeError(
                    TYPE_ERROR.format(label, item_type, type(item), item)
                )
    if as_tuple is True:
        return tuple(val)
    return val


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


def _framerate(doc):
    return _fraction(_dict(doc, 'framerate'))


def _sequence(_id, node):
    return Sequence(_id, _list(node, 'src', item_type=str, as_tuple=True))


class SliceIter:
    def __init__(self, Dmedia, db, root_id):
        self.Dmedia = Dmedia
        self.db = db
        self.root_id = root_id
        self._map = {
            'video/slice': self._slice,
            'video/sequence': _sequence,
        }

    def _slice(self, _id, node):
        src = _str(node, 'src')
        start = _int(node, 'start', 0)
        stop = _int(node, 'stop', 0)
        if start > stop:
            raise ValueError(
                'need start <= stop; got {} > {}'.format(start, stop)
            )
        filename = self.resolve(src)
        return Slice(_id, src, start, stop, filename)

    def _doc_to_tuple(self, doc):
        _id = _str(doc, '_id')
        node = _dict(doc, 'node')
        _type = _str(node, 'type')
        func = self._map.get(_type)
        if func is None:
            raise ValueError(
                '{}: bad node type: {!r}'.format(_id, _type)
            )
        n = func(_id, node)
        return n

    def get(self, _id):
        return self._doc_to_tuple(self.db.get(_id))

    def get_many(self, ids):
        docs = self.db.get_many(ids)
        if None in docs:
            raise ValueError(
                'Not Found: {!r}'.format(ids[docs.index(None)])
            )
        return tuple(self._doc_to_tuple(d) for d in docs)

    def resolve(self, file_id):
        (_id, status, name) = self.Dmedia.Resolve(file_id)
        assert _id == file_id
        if status != 0:
            msg = 'not local: {}'.format(file_id)
            log.error(msg)
            raise ValueError(msg)
        return name

    def get_framerate(self, file_id):
        return _framerate(self.db.get(file_id))

    def iter_slices(self, s):
        if type(s) is Slice:
            # Only yield a non-empty slice:
            if s.stop > s.start:
                yield s
        elif type(s) is Sequence:
            # Only yield from a non-empty sequence:
            if len(s.src) > 0:
                for child in self.get_many(s.src):
                    yield from self.iter_slices(child)
        else:
            TypeError('bad node: {!r}: {!r}'.format(type(s), s))

    def __iter__(self):
        return self.iter_slices(self.get(self.root_id))


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


class Pipeline:
    def __init__(self):
        self.pipeline = Gst.Pipeline()
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::error', WeakMethod(self, 'on_error'))
        self.error = False

    def set_state(self, name, sync=False):
        log.info('%s.set_state(%r, sync=%r)',
            self.__class__.__name__, name, sync
        )
        assert sync in (True, False)
        state = getattr(Gst.State, name)
        self.pipeline.set_state(state)
        if sync is True:
            self.pipeline.get_state(Gst.CLOCK_TIME_NONE)

    def destroy(self):
        log.info('%s.destroy()', self.__class__.__name__)
        self.set_state('NULL')
        # bus.remove_signal_watch() might be the fix for this error:
        #
        #   "GStreamer-CRITICAL **: gst_poll_read_control: assertion 'set != NULL' failed"
        #
        # Which is happening after a large number of VideoSlice have been
        # created and destroyed (~500 ish), which then leads to the process
        # crashing with a "too many open file descriptors" OSError.
        self.bus.remove_signal_watch()
        del self.bus
        del self.pipeline

    def _fatal(self):
        log.info('shuting down after fatal error')
        self.destroy()
        mainloop.quit()

    def fatal(self, msg, *args):
        log.error(msg, *args)
        GLib.idle_add(self._fatal)

    def on_error(self, bus, msg):
        self.error = True
        self.fatal('on_error: %s', msg.parse_error())

    def make_element(self, name, props=None):
        element = make_element(name, props)
        self.pipeline.add(element)
        return element

    def make_element_from_desc(self, desc):
        element = make_element_from_desc(desc)
        self.pipeline.add(element)
        return element   


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
        mainloop.quit()


class Input(Pipeline):
    def __init__(self, s, manager):
        super().__init__()
        self.s = s
        self.manager = manager
        self.cur = s.start
        self.framerate = None

        # Create elements
        src = self.make_element('filesrc', {'location': s.filename})
        dec = self.make_element('decodebin')
        convert = self.make_element('videoconvert')
        scale = self.make_element('videoscale', {'method': 3})
        sink = self.make_element('appsink',
            {
                'caps': manager.output.input_caps,
                'emit-signals': True,
                'max-buffers': 1,
                'enable-last-sample': False,
            }
        )

        # Connect signal handlers
        dec.connect('pad-added', WeakMethod(self, 'on_pad_added'))
        sink.connect('new-sample', WeakMethod(self, 'on_new_sample'))

        # Link elements
        src.link(dec)
        convert.link(scale)
        scale.link(sink)

        # Needed in on_pad_added():
        self.sink_pad = convert.get_static_pad('sink')

    def run(self):
        log.info('Playing %r', self.s)
        self.set_state('PAUSED', sync=True)
        assert self.framerate is not None
        self.pipeline.seek(
            1.0,  # rate
            Gst.Format.TIME,        
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.SEGMENT | Gst.SeekFlags.ACCURATE,
            Gst.SeekType.SET,
            frame_to_nanosecond(self.s.start, self.framerate),
            Gst.SeekType.SET,
            frame_to_nanosecond(self.s.stop, self.framerate),
        )
        self.set_state('PLAYING')

    def on_pad_added(self, dec, pad):
        caps = pad.get_current_caps()
        string = caps.to_string()
        log.info('on_pad_added(): %s', string)
        if string.startswith('video/'):
            self.framerate = get_framerate_from_struct(caps.get_structure(0))
            log.info('framerate: %r', self.framerate)
            pad.link(self.sink_pad)

    def on_new_sample(self, sink):
        buf = sink.emit('pull-sample').get_buffer()
        cur = nanosecond_to_frame(buf.pts, self.framerate)
        #log.info('new-sample: [%s:%s] @%s', self.s.start, self.s.stop, cur)
        if self.cur != cur:
            self.fatal('cur: %s != %s', self.cur, cur)
        if not (self.s.start <= cur < self.s.stop):
            self.fatal('false inequality: %s <= %s < %s',
                self.s.start, cur, self.s.stop
            )
        self.manager.output.push(buf)
        self.cur += 1
        if self.cur == self.s.stop:
            log.info('last frame in slice')
            self.manager.input_complete(self)
        return Gst.FlowReturn.OK


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
    def __init__(self, settings, filename):
        super().__init__()
        self.bus.connect('message::eos', WeakMethod(self, 'on_eos'))

        desc = settings['video']['caps']
        (self.framerate, self.input_caps, output_caps) = make_video_caps(desc)
        
        self.i = 0

        self.src = self.make_element('appsrc',
            {
                'caps': output_caps,
                'emit-signals': False,
                'format': 3,
                'max-bytes': 64 * 1024 * 1024,
                'block': True,
            }
        )
        self.enc = self.make_element_from_desc(settings['video']['encoder'])
        self.mux = self.make_element_from_desc(settings['muxer'])
        self.sink = self.make_element('filesink', {'location': filename})

        self.src.link(self.enc)
        self.enc.link(self.mux)
        self.mux.link(self.sink)

    def run(self):
        self.set_state('PLAYING')

    def push(self, buf):
        ts = video_pts_and_duration(self.i, self.i + 1, self.framerate)
        buf.pts = ts.pts
        buf.dts = ts.pts
        buf.duration = ts.duration
        assert buf.pts == buf.dts == ts.pts
        #log.info('push %s, %s', self.i, ts)
        self.i += 1
        self.src.emit('push-buffer', buf)

    def done(self):
        log.info('appsrc will emit EOS')
        self.src.emit('end-of-stream')

    def on_eos(self, bus, msg):
        log.info('eos')
        self.destroy()
        mainloop.quit()


class Manager:
    __slots__ = ('slices_iter', 'input', 'output', 'frames')

    def __init__(self, slices, settings, filename):
        self.slices_iter = iter(slices)
        self.input = None
        self.output = Output(settings, filename)
        self.frames = 0

    def run(self):
        self.output.run()
        self.next()

    def next_slice(self):
        try:
            return next(self.slices_iter)
        except StopIteration:
            return None

    def next(self):
        assert self.input is None
        s = self.next_slice()
        if s is None:
            self.output.done()
        else:
            self.frames += (s.stop - s.start)
            self.input = Input(s, self)
            self.input.run()

    def __input_complete(self, inst):
        assert inst is self.input
        self.input.destroy()
        self.input = None
        self.next()

    def input_complete(self, inst):
        log.info('Manager.input_complete(<%r>)', inst.s)
        GLib.idle_add(self.__input_complete, inst)

