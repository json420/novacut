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

"""
Build GnonLin composition from Novacut edit description.
"""

from datetime import datetime
import logging
import os
from os import path

from microfiber import Database, dumps
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst

from .timefuncs import video_pts_and_duration, audio_pts_and_duration
from .timefuncs import video_slice_to_gnl_new
from .mapper import get_framerate


Gst.init(None)
log = logging.getLogger()
log.info('**** Gst.version(): %r', Gst.version())


stream_map = {
    'video': 'video/x-raw',
    'audio': 'audio/x-raw',
}

# Provide very clear TypeError messages:
TYPE_ERROR = '{}: need a {!r}; got a {!r}: {!r}'


def stream_caps(stream):
    return Gst.caps_from_string(stream_map[stream])


class NoSuchElement(Exception):
    def __init__(self, name):
        self.name = name
        super().__init__('GStreamer element {!r} not available'.format(name))


def make_element(name, props=None):
    if not isinstance(name, str):
        raise TypeError(
            TYPE_ERROR.format('name', str, type(name), name)
        )
    if not (props is None or isinstance(props, dict)):
        raise TypeError(
            TYPE_ERROR.format('props', dict, type(props), props)
        )
    element = Gst.ElementFactory.make(name, None)
    if element is None:
        log.error('could not create GStreamer element %r', name)
        raise NoSuchElement(name)
    if props:
        for (key, value) in props.items():
            element.set_property(key, value)
    return element


def element_from_desc(desc):
    """
    Create a GStreamer element from a JSON serializable description.

    For example:

    >>> enc = element_from_desc('theoraenc')
    >>> enc.get_factory().get_name()
    'theoraenc'
    
    Or from a ``dict`` with the element name:

    >>> enc = element_from_desc({'name': 'theoraenc'})
    >>> enc.get_factory().get_name()
    'theoraenc'
    >>> enc.get_property('quality')
    48

    Or from a ``dict`` with the element name and props:

    >>> enc = element_from_desc({'name': 'theoraenc', 'props': {'quality': 40}})
    >>> enc.get_factory().get_name()
    'theoraenc'
    >>> enc.get_property('quality')
    40

    """
    if isinstance(desc, dict):
        return make_element(desc['name'], desc.get('props'))
    return make_element(desc)


def caps_string(mime, caps=None):
    """
    Build a GStreamer caps string.

    For example:

    >>> caps_string('video/x-raw')
    'video/x-raw'

    Or with specific caps:

    >>> caps_string('video/x-raw', {'width': 800, 'height': 450})
    'video/x-raw, height=450, width=800'

    """
    assert mime in ('audio/x-raw', 'video/x-raw')
    accum = [mime]
    if caps:
        for key in sorted(caps):
            accum.append('{}={}'.format(key, caps[key]))
    return ', '.join(accum)


def make_caps(mime, caps):
    if caps is None:
        return None
    return Gst.caps_from_string(caps_string(mime, caps))



def to_gst_time(spec, doc):
    """
    Convert a time specified by frame or sample to nanoseconds.

    For example, both of these specify 2 seconds into a stream, first by frame,
    then by sample:

    >>> doc = {
    ...     'framerate': {'num': 24, 'denom': 1},
    ...     'samplerate': 48000,
    ... }
    ...
    >>> to_gst_time({'frame': 48}, doc)  #doctest: +ELLIPSIS
    2000000000...
    >>> to_gst_time({'sample': 96000}, doc)  #doctest: +ELLIPSIS
    2000000000...

    """
    if 'frame' in spec:
        num = doc['framerate']['num']
        denom = doc['framerate']['denom']
        return spec['frame'] * Gst.SECOND * denom // num
    if 'sample' in spec:
        rate = doc['samplerate']
        return spec['sample'] * Gst.SECOND // rate
    raise ValueError('invalid time spec: {!r}'.format(spec))


def build_slice(builder, doc, offset=0):
    node = doc['node']
    clip = builder.get_doc(node['src'])
    start = to_gst_time(node['start'], clip)
    stop = to_gst_time(node['stop'], clip)
    duration = stop - start

    if node['stream'] == 'both':
        streams = ['video', 'audio']
    else:
        streams = [node['stream']]

    #streams = ['video', 'audio']
    #streams = ['audio']

    for stream in streams:
        # Create the element, set the URI, and select the stream
        element = make_element('gnlurisource')
        element.set_property('uri', builder.resolve_file(clip['_id']))
        element.set_property('caps', stream_caps(stream))

        # These properties are about the slice itself
        element.set_property('inpoint', start)
        #element.set_property('media-duration', duration)

        # These properties are about the position of the slice in the composition
        element.set_property('start', offset)
        element.set_property('duration', duration)
        
        log.info('%s %d:%d %s', stream, start, duration, clip['_id'])

        builder.add(element, stream)

    return duration


def build_video_slice(builder, doc, offset):
    node = doc['node']
    clip = builder.get_doc(node['src'])
    framerate = get_framerate(clip)
    start = node['start']
    stop = node['stop']
    frames = stop - start
    log.info('video/slice %d:%d %s', start, stop, node['src'])

    element = make_element('gnlurisource')
    element.set_property('caps', Gst.caps_from_string('video/x-raw'))
    element.set_property('uri', builder.resolve_file(node['src']))

    # These properties are about the slice itself
    (pts, duration) = video_pts_and_duration(start, stop, framerate)
    element.set_property('inpoint', pts)
    #element.set_property('media-duration', duration)

    # These properties are about the position of the slice in the composition
    (pts, duration) = video_pts_and_duration(offset, offset+frames, framerate)
    element.set_property('start', pts)
    element.set_property('duration', duration)

    return (frames, element)


def build_audio_slice(builder, doc, offset):
    node = doc['node']
    samplerate = builder.get_doc(node['src'])['samplerate']
    start = node['start']
    stop = node['stop']
    samples = stop - start
    log.info('audio/slice %d:%d %s', start, stop, node['src'])

    element = make_element('gnlurisource')
    element.set_property('caps', Gst.caps_from_string('audio/x-raw'))
    element.set_property('uri', builder.resolve_file(node['src']))

    # These properties are about the slice itself
    (pts, duration) = audio_pts_and_duration(start, stop, samplerate)
    element.set_property('inpoint', pts)
    #element.set_property('media-duration', duration)

    # These properties are about the position of the slice in the composition
    (pts, duration) = audio_pts_and_duration(
        offset, offset + samples, samplerate
    )
    element.set_property('start', pts)
    element.set_property('duration', duration)

    return (samples, element)


def build_sequence(builder, doc, offset=0):
    sequence_duration = 0
    for src in doc['node']['src']:
        duration = builder.build(src, offset)
        offset += duration
        sequence_duration += duration
    return sequence_duration


_builders = {
    'slice': build_slice,
    'sequence': build_sequence,
}


class Builder:
    def __init__(self):
        self.last = None
        self.audio = None
        self.video = None

    def get_audio(self):
        if self.audio is None:
            self.audio = make_element('gnlcomposition')
        return self.audio

    def get_video(self):
        if self.video is None:
            self.video = make_element('gnlcomposition')
        return self.video

    def add(self, element, stream):
        assert stream in ('video', 'audio')
        if stream == 'video':
            target = self.get_video()
        else:
            target = self.get_audio()
        target.add(element)
        self.last = element

    def build(self, _id, offset=0):
        doc = self.get_doc(_id)
        func = _builders[doc['node']['type']]
        return func(self, doc, offset)

    def build_root(self, _id):
        duration = self.build(_id, 0)
        sources = tuple(filter(lambda s: s is not None, (self.video, self.audio)))
        for src in sources:
            src.set_property('duration', duration)
        return sources

    def resolve_file(self, _id):
        pass

    def get_doc(self, _id):
        pass


class Builder2:
    def __init__(self, Dmedia, novacut_db):
        self.Dmedia = Dmedia
        self.novacut_db = novacut_db
        self.last = None
        self.audio = None
        self.video = None
        self.builders = {
            'video/sequence': self.build_video_sequence,
            'video/slice': self.build_video_slice,
        }

    def build_root(self, _id):
        frames = self.build(_id, 0)
        log.info('total video frames: %s', frames)
        sources = filter(lambda s: s is not None, (self.video, self.audio))
#        for src in sources:
#            src.set_property('duration', duration)
        
        return sources

    def get_doc(self, _id):
        return self.novacut_db.get(_id)

    def resolve_file(self, _id):
        (_id, status, filename) = self.Dmedia.Resolve(_id)
        if status != 0:
            msg = 'not local: {}'.format(_id)
            log.error(msg)
            raise SystemExit(msg)
        return 'file://' + filename

    def get_audio(self):
        if self.audio is None:
            self.audio = make_element('gnlcomposition')
        return self.audio

    def get_video(self):
        if self.video is None:
            self.video = make_element('gnlcomposition')
        return self.video

    def build(self, src_id, offset):
        doc = self.get_doc(src_id)
        builder = self.builders[doc['node']['type']]
        return builder(doc, offset)

    def build_video_sequence(self, doc, offset):
        frames = 0
        for src_id in doc['node']['src']:
            frames += self.build(src_id, offset + frames)
        return frames

    def build_video_slice(self, doc, offset):
        start = doc['node']['start']
        stop = doc['node']['stop']
        src = self.get_doc(doc['node']['src'])
        log.info('video slice %s: %s[%d:%d]', doc['_id'], src['_id'], start, stop)
        framerate = get_framerate(src)
        props = video_slice_to_gnl_new(offset, start, stop, framerate)
        element = make_element('gnlurisource', props)
        element.set_property('caps', Gst.caps_from_string('video/x-raw'))
        element.set_property('uri', self.resolve_file(src['_id']))
        self.get_video().add(element)
        return stop - start


class EncoderBin(Gst.Bin):
    """
    Base class for `AudioEncoder` and `VideoEncoder`.
    """

    def __init__(self, d, mime):
        super().__init__()
        self._d = d
        assert mime in ('audio/x-raw', 'video/x-raw')

        # Create elements
        self._identity = self._make('identity', {'single-segment': True})
        self._q1 = self._make('queue')
        self._q2 = self._make('queue')
        self._q3 = self._make('queue')
        self._enc = self._from_desc(d['encoder'])

        # Create the filter caps
        self._caps = make_caps(mime, d.get('caps'))

        # Link elements
        self._identity.link(self._q1)
        if self._caps is None:
            self._q2.link(self._enc)
        else:
            self._q2.link_filtered(self._enc, self._caps)
        self._enc.link(self._q3)

        # Ghost Pads
        self.add_pad(
            Gst.GhostPad.new('sink', self._identity.get_static_pad('sink'))
        )
        self.add_pad(
            Gst.GhostPad.new('src', self._q3.get_static_pad('src'))
        )

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self._d)

    def _make(self, name, props=None):
        element = make_element(name, props)
        self.add(element)
        return element

    def _from_desc(self, desc):
        element = element_from_desc(desc)
        self.add(element)
        return element


class AudioEncoder(EncoderBin):
    def __init__(self, d):
        super().__init__(d, 'audio/x-raw')

        # Create elements:
        self._conv = self._make('audioconvert')
        self._rsp = self._make('audioresample', {'quality': 10})
        self._rate = self._make('audiorate',
            {'tolerance': Gst.SECOND * 4 // 48000}
        )

        # Link elements:
        self._q1.link(self._conv)
        self._conv.link(self._rsp)
        self._rsp.link(self._rate)
        self._rate.link(self._q2)


class VideoEncoder(EncoderBin):
    def __init__(self, d):
        super().__init__(d, 'video/x-raw')

        # Create elements:
        self._scale = self._make('videoscale', {'method': 3})
        self._color = self._make('videoconvert')

        # Link elements:
        self._q1.link(self._scale)
        self._scale.link(self._color)
        self._color.link(self._q2)


class Renderer:
    def __init__(self, root, settings, builder, dst):
        """
        Initialize.

        :param job: a ``dict`` describing the transcode to perform.
        :param fs: a `FileStore` instance in which to store transcoded file
        """
        self.root = root
        self.settings = settings
        self.builder = builder
        self.mainloop = GLib.MainLoop()
        self.pipeline = Gst.Pipeline()

        # Create bus and connect several handlers
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::eos', self.on_eos)
        self.bus.connect('message::error', self.on_error)

        # Create elements
        self.mux = element_from_desc(settings['muxer'])
        self.sink = make_element('filesink')

        self.pipeline.add(self.mux)
        self.pipeline.add(self.sink)

        # Add elements to pipeline
        self.sources = builder.build_root(root)
        self.encoders = {}
        for key in ('video', 'audio'):
            src = getattr(builder, key)
            if src is None:
                continue
            self.encoders[key] = self.create_encoder(key)
            src.connect('pad-added', self.on_pad_added, key)
            self.pipeline.add(src)

        # Set properties
        self.sink.set_property('location', dst)

        # Link *some* elements
        # This is completed in self.on_pad_added()
        self.mux.link(self.sink)

        self.audio = None
        self.video = None
 
    def run(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        self.mainloop.run()

    def kill(self):
        self.pipeline.set_state(Gst.State.NULL)
        self.mainloop.quit()

    def create_encoder(self, key):
        if key in self.settings:
            klass = {'audio': AudioEncoder, 'video': VideoEncoder}[key]
            el = klass(self.settings[key])
        else:
            el = make_element('fakesink')
        self.pipeline.add(el)
        if key in self.settings:
            log.info(el)
            el.link(self.mux)
        return el

    def on_pad_added(self, element, pad, key):
        try:
            string = pad.query_caps(None).to_string()
            log.info('pad-added: %r %r', key, string)
            enc = self.encoders[key]
            pad.link(enc.get_static_pad('sink'))
        except Exception as e:
            log.exception('Error in Renderer.on_pad_added():')

    def on_eos(self, bus, msg):
        log.info('eos')
        self.kill()

    def on_error(self, bus, msg):
        self.error = msg.parse_error()
        log.error(self.error)
        self.kill()


class Worker:
    def __init__(self, Dmedia, env):
        self.Dmedia = Dmedia
        self.novacut_db = Database('novacut-1', env)
        self.dmedia_db = Database('dmedia-1', env)

    def run(self, job_id):
        job = self.novacut_db.get(job_id)
        log.info('Rendering: %s', dumps(job, pretty=True))
        root = job['node']['root']
        settings = self.novacut_db.get(job['node']['settings'])
        log.info('With settings: %s', dumps(settings['node']))
        builder = Builder2(self.Dmedia, self.novacut_db)
        dst = self.Dmedia.AllocateTmp()
        renderer = Renderer(root, settings['node'], builder, dst)
        renderer.run()
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
