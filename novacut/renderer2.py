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

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst
from dbase32 import random_id

from .timefuncs import frame_to_nanosecond, nanosecond_to_frame, video_pts_and_duration
from .misc import random_slice, random
from .renderer import make_element

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


# Provide very clear TypeError messages:
TYPE_ERROR = '{}: need a {!r}; got a {!r}: {!r}'

Slice = namedtuple('Slice', 'id src start stop filename framerate')
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


def _framerate(doc):
    d = _dict(doc, 'framerate') 
    return Fraction(
        _int(d, 'num',   1),
        _int(d, 'denom', 1)
    )


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
        framerate = self.get_framerate(src)
        return Slice(_id, src, start, stop, filename, framerate)

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
        self.fatal('on_error: %s', msg.parse_error())

    def make_element(self, name, props=None):
        element = make_element(name, props)
        self.pipeline.add(element)
        return element        


class Input(Pipeline):
    def __init__(self, s, manager):
        super().__init__()
        self.s = s
        self.manager = manager
        self.cur = s.start

        # Create elements
        src = self.make_element('filesrc', {'location': s.filename})
        dec = self.make_element('decodebin')
        self.sink = self.make_element('appsink',
            {
                'emit-signals': True,
                'max-buffers': 1,
                'enable-last-sample': False,
            }
        )

        # Connect signal handlers
        dec.connect('pad-added', WeakMethod(self, 'on_pad_added'))
        self.sink.connect('new-sample', WeakMethod(self, 'on_new_sample'))

        # Link elements
        src.link(dec)

    def run(self):
        log.info('Playing %r', self.s)
        self.set_state('PAUSED', sync=True)
        self.pipeline.seek(
            1.0,  # rate
            Gst.Format.TIME,        
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.SEGMENT | Gst.SeekFlags.ACCURATE,
            Gst.SeekType.SET,
            frame_to_nanosecond(self.s.start, self.s.framerate),
            Gst.SeekType.SET,
            frame_to_nanosecond(self.s.stop, self.s.framerate),
        )
        self.set_state('PLAYING')

    def on_pad_added(self, dec, pad):
        caps = pad.get_current_caps()
        string = caps.to_string()
        log.info('on_pad_added(): %s', string)
        if string.startswith('video/'):
            pad.link(self.sink.get_static_pad('sink'))

    def on_new_sample(self, sink):
        buf = sink.emit('pull-sample').get_buffer()
        cur = nanosecond_to_frame(buf.pts, self.s.framerate)
        log.info('new-sample: [%s:%s] @%s', self.s.start, self.s.stop, cur)
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


class Output(Pipeline):
    def __init__(self, filename, framerate):
        super().__init__()
        self.bus.connect('message::eos', WeakMethod(self, 'on_eos'))

        self.framerate = framerate
        self.i = 0
        caps = Gst.caps_from_string('video/x-raw, format=(string)I420, width=(int)1920, height=(int)1080, interlace-mode=(string)progressive, pixel-aspect-ratio=(fraction)1/1, chroma-site=(string)mpeg2, colorimetry=(string)bt709, framerate=(fraction)30000/1001')

        self.src = self.make_element('appsrc',
            {
                'caps': caps,
                'emit-signals': False,
                'format': 3,
                'max-bytes': 64 * 1024 * 1024,
                'block': True,
            }
        )
        self.enc = self.make_element('x264enc',
            {'bitrate': 12288, 'psy-tune': 5}
        )
        self.mux = self.make_element('matroskamux')
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
        log.info('push %s, %s', self.i, ts)
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
    __slots__ = ('slices', 'slices_iter', 'input', 'output')

    def __init__(self, slices, output):
        self.slices = slices
        self.slices_iter = iter(slices)
        self.input = None
        self.output = output

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
            self.input = Input(s, self)
            self.input.run()

    def __input_complete(self, inst):
        assert inst is self.input
        self.input.destroy()
        self.input = None
        self.next()

    def input_complete(self, inst):
        log.info('Manager.input_complete(<%r>)', inst.s.id)
        GLib.idle_add(self.__input_complete, inst)



if __name__ == '__main__':
    tree = path.dirname(path.dirname(path.abspath(__file__)))
    sources = []
    for name in sorted(os.listdir(tree)):
        if name.endswith('.MOV'):
            sources.append(path.join(tree, name))
#    for i in range(1):
#        sources += sources
    cnt = len(sources)
    random.shuffle(sources)
    framerate = Fraction(30000, 1001)
    slices = []
    for filename in sources:
        (start, stop) = random_slice(550)
        s = Slice(random_id(), random_id(30), start, stop, filename, framerate)
        slices.append(s)
    del sources

    output = Output(path.join(tree, 'test.mkv'), framerate)
    manager = Manager(slices, output)
    manager.run()
    mainloop.run()
    print(cnt)

