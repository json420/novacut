# novacut: the distributed video editor
# Copyright (C) 2011 Novacut Inc
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

from os import path

from dmedia.filestore import FileStore
import gobject
import gst

import logging

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger()

gobject.threads_init()
fs = FileStore('/media/dmedia1')

FRAMERATE = 25  # Static framerate for test

docs = [
    {
        '_id': 'NPY3IW5SQJUNSP2KV47GVB24G7SWX6XF',
        'type': 'dmedia/file',
        'ext': 'mov',
    },

    {
        '_id': 'MBHRKQ4F4UI53ECXKQSKELUT',
        'type': 'novacut/node',
        'node': {
            'type': 'slice',
            'src': 'NPY3IW5SQJUNSP2KV47GVB24G7SWX6XF',
            'start': {
                'frame': 120,
            },
            'stop': {
                'frame': 400,
            },
        },
    },

    {
        '_id': 'NIPXXOZAM2MQGKCLE5KVH74V',
        'type': 'novacut/node',
        'node': {
            'type': 'sequence',
            'src': [
                'MBHRKQ4F4UI53ECXKQSKELUT',
            ],
        },
    },
]

docmap = dict(
    (doc['_id'], doc) for doc in docs
)


def resolve(doc):
    return fs.path(doc['_id'], doc.get('ext'))


def get(_id):
    return docmap[_id]


def build_slice(doc):
    log.debug('build_slice\n%r', doc)
    src = resolve(get(doc['node']['src']))
    element = gst.element_factory_make('gnlfilesource')
    element.set_property('location', src)
    start = doc['node']['start']['frame'] * gst.SECOND / FRAMERATE
    stop = doc['node']['stop']['frame'] * gst.SECOND / FRAMERATE
    element.set_property('media-start', start)
    element.set_property('media-duration', stop - start)
    element.set_property('duration', stop - start)
    return element


def build_sequence(doc):
    log.debug('build_sequence\n%r', doc)
    element = gst.element_factory_make('gnlcomposition', doc['_id'])
    start = 0
    for src in doc['node']['src']:
        child = build(src)
        element.add(child)
        child.set_property('start', start)
        start += child.get_property('duration')
    return element


builders = {
    'slice': build_slice,
    'sequence': build_sequence,
}


def build(_id):
    doc = get(_id)
    assert doc['type'] == 'novacut/node'
    func = builders[doc['node']['type']]
    el = func(doc)
    return el
    for key in ('active', 'caps', 'duration', 'media-duration', 'media-start', 'media-stop', 'priority', 'rate', 'start', 'stop', 'expandable'):
        print '{}: {!r}'.format(key, el.get_property(key))
    print '{}: {!r}'.format('caps', el.get_property('caps').to_string())
    return el



def caps_string(mime, caps):
    """
    Build a GStreamer caps string.

    For example:

    >>> caps_string('video/x-raw-yuv', {'width': 800, 'height': 450})
    'video/x-raw-yuv, height=450, width=800'
    """
    accum = [mime]
    for key in sorted(caps):
        accum.append('{}={}'.format(key, caps[key]))
    return ', '.join(accum)



class TranscodeBin(gst.Bin):
    """
    Base class for `AudioTranscoder` and `VideoTranscoder`.
    """
    def __init__(self, d):
        super(TranscodeBin, self).__init__()
        self._d = d
        self._q1 = self._make('queue2')
        self._enc = self._make(d['enc'], d.get('props'))
        self._q2 = self._make('queue2')
        self._enc.link(self._q2)
        self.add_pad(
            gst.GhostPad('sink', self._q1.get_pad('sink'))
        )
        self.add_pad(
            gst.GhostPad('src', self._q2.get_pad('src'))
        )

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self._d)

    def _make(self, name, props=None):
        """
        Create gst element, set properties, and add to this bin.
        """
        element = gst.element_factory_make(name)
        if props:
            for (key, value) in props.iteritems():
                element.set_property(key, value)
        self.add(element)
        return element


class AudioTranscoder(TranscodeBin):
    def __init__(self, d):
        super(AudioTranscoder, self).__init__(d)

        # Create processing elements:
        self._conv = self._make('audioconvert')
        self._rsp = self._make('audioresample', {'quality': 10})
        self._rate = self._make('audiorate')

        # Link elements:
        self._q1.link(self._conv)
        self._conv.link(self._rsp)
        if d.get('caps'):
            # FIXME: There is probably a better way to do this, but the caps API
            # has always been a bit of a mystery to me.  --jderose
            if d['enc'] == 'vorbisenc':
                mime = 'audio/x-raw-float'
            else:
                mime = 'audio/x-raw-int'
            caps = gst.caps_from_string(
                caps_string(mime, d['caps'])
            )
            self._rsp.link(self._rate, caps)
        else:
            self._rsp.link(self._rate)
        self._rate.link(self._enc)


class VideoTranscoder(TranscodeBin):
    def __init__(self, d):
        super(VideoTranscoder, self).__init__(d)

        # Create processing elements:
        self._scale = self._make('ffvideoscale', {'method': 10})
        self._color = self._make('ffmpegcolorspace')
        self._q = self._make('queue2')

        # Link elements:
        self._q1.link(self._scale)
        self._scale.link(self._color)
        if d.get('caps'):
            caps = gst.caps_from_string(
                caps_string('video/x-raw-yuv', d['caps'])
            )
            self._color.link(self._q, caps)
        else:
            self._color.link(self._q)
        self._q.link(self._enc)



class Renderer(object):
    def __init__(self, job):
        """
        Initialize.

        :param job: a ``dict`` describing the transcode to perform.
        :param fs: a `FileStore` instance in which to store transcoded file
        """
        self.job = job
        self.mainloop = gobject.MainLoop()
        self.pipeline = gst.Pipeline()

        # Create bus and connect several handlers
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::eos', self.on_eos)
        self.bus.connect('message::error', self.on_error)

        # Create elements
        self.src = build(job['node'])
        print(repr(self.src))
        self.mux = gst.element_factory_make(job['mux'])
        self.sink = gst.element_factory_make('filesink')

        # Set properties
        self.sink.set_property('location', 'test.' + job['ext'])

        # Connect handler for 'new-decoded-pad' signal
        self.src.connect('pad-added', self.on_pad_added)

        # Add elements to pipeline
        self.pipeline.add(self.src, self.mux, self.sink)

        # Link *some* elements
        # This is completed in self.on_new_decoded_pad()
        self.mux.link(self.sink)

        self.audio = None
        self.video = None

    def run(self):
        self.pipeline.set_state(gst.STATE_PAUSED)
        self.mainloop.run()

    def kill(self):
        self.pipeline.set_state(gst.STATE_NULL)
        self.pipeline.get_state()
        self.mainloop.quit()

    def link_pad(self, pad, name, key):
        log.info('link_pad: %r, %r, %r', pad, name, key)
        if key in self.job:
            klass = {'audio': AudioTranscoder, 'video': VideoTranscoder}[key]
            el = klass(self.job[key])
        else:
            el = gst.element_factory_make('fakesink')
        self.pipeline.add(el)
        log.info('Linking pad %r with %r', name, el)
        pad.link(el.get_compatible_pad(pad, pad.get_caps()))
        if key in self.job:
            el.link(self.mux)
        el.set_state(gst.STATE_PLAYING)
        self.pipeline.set_state(gst.STATE_PLAYING)
        return el

    def on_pad_added(self, element, pad):
        name = pad.get_caps()[0].get_name()
        log.debug('pad-added: %r', name)
        if name.startswith('audio/'):
            assert self.audio is None
            self.audio = self.link_pad(pad, name, 'audio')
        elif name.startswith('video/'):
            assert self.video is None
            self.video = self.link_pad(pad, name, 'video')

    def on_eos(self, bus, msg):
        log.info('eos')
        self.kill()

    def on_error(self, bus, msg):
        error = msg.parse_error()[1]
        log.error(error)
        self.kill()



job = {
    'node': 'NIPXXOZAM2MQGKCLE5KVH74V',
    'mux': 'oggmux',
    'video': {
        'enc': 'theoraenc',
        'caps': {'width': 960, 'height': 540},
    },
    'ext': 'ogv',
}

r = Renderer(job)
r.run()
