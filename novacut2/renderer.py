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

# FIXME: Some of this is duplicated in dmedia's transcoder.  For now we're doing
# a bit of copy and paste to quickly get the render backend usable... then we'll
# refine and consolidate with what's in dmedia.

import logging

import gst
import gobject


log = logging.getLogger()

stream_map = {
    'video': 'video/x-raw-rgb',
    'audio': 'audio/x-raw-int; audio/x-raw-float',
}


def stream_caps(stream):
    return gst.caps_from_string(stream_map[stream])


def make_element(desc):
    """
    Create a GStreamer element and set its properties.

    For example:

    >>> enc = make_element({'name': 'theoraenc'})
    >>> enc.get_property('quality')
    48

    Or with properties:

    >>> enc = make_element({'name': 'theoraenc', 'props': {'quality': 40}})
    >>> enc.get_property('quality')
    40

    """
    el = gst.element_factory_make(desc['name'])
    if desc.get('props'):
        for (key, value) in desc['props'].iteritems():
            el.set_property(key, value)
    return el


def caps_string(desc):
    """
    Build a GStreamer caps string.

    For example:

    >>> desc = {'mime': 'video/x-raw-yuv'}
    >>> caps_string(desc)
    'video/x-raw-yuv'

    Or with specific caps:

    >>> desc = {
    ...     'mime': 'video/x-raw-yuv',
    ...     'caps': {'width': 800, 'height': 450},
    ... }
    ...
    >>> caps_string(desc)
    'video/x-raw-yuv, height=450, width=800'

    """
    accum = [desc['mime']]
    if desc.get('caps'):
        caps = desc['caps']
        for key in sorted(caps):
            accum.append('{}={}'.format(key, caps[key]))
    return ', '.join(accum)


def make_caps(desc):
    if not desc:
        return None
    return gst.caps_from_string(caps_string(desc))



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
        return spec['frame'] * gst.SECOND * denom / num
    if 'sample' in spec:
        rate = doc['samplerate']
        return spec['sample'] * gst.SECOND / rate
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
        element = gst.element_factory_make('gnlurisource')
        element.set_property('uri', 'file://' + builder.resolve_file(clip['_id']))
        element.set_property('caps', stream_caps(stream))

        # These properties are about the slice itself
        element.set_property('media-start', start)
        element.set_property('media-duration', duration)

        # These properties are about the position of the slice in the composition
        element.set_property('start', offset)
        element.set_property('duration', duration)
        
        log.info('%s %d:%d %s', stream, start, duration, clip['_id'])

        builder.add(element, stream)
        
    return duration


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


class Builder(object):
    def __init__(self):
        self.last = None
        self.audio = None
        self.video = None

    def get_audio(self):
        if self.audio is None:
            self.audio = gst.element_factory_make('gnlcomposition')
        return self.audio

    def get_video(self):
        if self.video is None:
            self.video = gst.element_factory_make('gnlcomposition')
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
        sources = filter(lambda s: s is not None, (self.video, self.audio))
        for src in sources:
            src.set_property('duration', duration)
        return sources

    def resolve_file(self, _id):
        pass

    def get_doc(self, _id):
        pass


class EncoderBin(gst.Bin):
    """
    Base class for `AudioEncoder` and `VideoEncoder`.
    """

    def __init__(self, d):
        super(EncoderBin, self).__init__()
        self._d = d

        # Create elements
        self._identity = self._make('identity', {'single-segment': True})
        self._q1 = self._make('queue')
        self._q2 = self._make('queue')
        self._q3 = self._make('queue')
        self._enc = self._make(d['encoder'])

        # Create the filter caps
        self._caps = make_caps(d.get('filter'))

        # Link elements
        self._identity.link(self._q1)
        if self._caps is None:
            self._q2.link(self._enc)
        else:
            self._q2.link(self._enc, self._caps)
        self._enc.link(self._q3)

        # Ghost Pads
        self.add_pad(
            gst.GhostPad('sink', self._identity.get_pad('sink'))
        )
        self.add_pad(
            gst.GhostPad('src', self._q3.get_pad('src'))
        )

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self._d)

    def _make(self, desc, props=None):
        """
        Create gst element, set properties, and add to this bin.
        """
        if isinstance(desc, basestring):
            desc = {'name': desc, 'props': props}
        el = make_element(desc)
        self.add(el)
        return el


class AudioEncoder(EncoderBin):
    def __init__(self, d):
        super(AudioEncoder, self).__init__(d)

        # Create elements:
        self._conv = self._make('audioconvert')
        self._rsp = self._make('audioresample', {'quality': 10})
        self._rate = self._make('audiorate')

        # Link elements:
        gst.element_link_many(
            self._q1, self._conv, self._rsp, self._rate, self._q2
        )


class VideoEncoder(EncoderBin):
    def __init__(self, d):
        super(VideoEncoder, self).__init__(d)

        # Create elements:
        self._scale = self._make('ffvideoscale', {'method': 10})
        self._color = self._make('ffmpegcolorspace')

        # Link elements:
        gst.element_link_many(self._q1, self._scale, self._color, self._q2)


class Renderer(object):
    def __init__(self, root, settings, builder, dst):
        """
        Initialize.

        :param job: a ``dict`` describing the transcode to perform.
        :param fs: a `FileStore` instance in which to store transcoded file
        """
        self.root = root
        self.settings = settings
        self.builder = builder
        self.mainloop = gobject.MainLoop()
        self.pipeline = gst.Pipeline()

        # Create bus and connect several handlers
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::eos', self.on_eos)
        self.bus.connect('message::error', self.on_error)

        # Create elements
        self.sources = builder.build_root(root)
        self.mux = make_element(settings['muxer'])
        self.sink = gst.element_factory_make('filesink')

        # Add elements to pipeline
        for src in self.sources:
            self.pipeline.add(src)
            src.connect('pad-added', self.on_pad_added)
            src.connect('no-more-pads', self.on_no_more_pads)
        self.pipeline.add(self.mux, self.sink)

        # Set properties
        self.sink.set_property('location', dst)

        # Link *some* elements
        # This is completed in self.on_pad_added()
        self.mux.link(self.sink)

        self.audio = None
        self.video = None

    def run(self):
        self.pipeline.set_state(gst.STATE_PLAYING)
        self.mainloop.run()

    def kill(self):
        self.pipeline.set_state(gst.STATE_NULL)
        self.pipeline.get_state()
        self.mainloop.quit()

    def link_pad(self, pad, name, key):
        log.info('link_pad: %r, %r, %r', pad, name, key)
        if key in self.settings:
            klass = {'audio': AudioEncoder, 'video': VideoEncoder}[key]
            el = klass(self.settings[key])
        else:
            el = gst.element_factory_make('fakesink')
        self.pipeline.add(el)
        log.info('Linking pad %r with %r', name, el)
        pad.link(el.get_compatible_pad(pad, pad.get_caps()))
        if key in self.settings:
            el.link(self.mux)
        el.set_state(gst.STATE_PLAYING)
        return el

    def on_pad_added(self, element, pad):
        try:
            string = pad.get_caps().to_string()
            log.debug('pad-added: %r', string)
            if string.startswith('audio/'):
                assert self.audio is None
                self.audio = self.link_pad(pad, string, 'audio')
            elif string.startswith('video/'):
                assert self.video is None
                self.video = self.link_pad(pad, string, 'video')
        except Exception as e:
            log.exception('Error in Renderer.on_pad_added():')

    def on_no_more_pads(self, element):
        log.info('no more pads')

    def on_eos(self, bus, msg):
        log.info('eos')
        self.kill()

    def on_error(self, bus, msg):
        error = msg.parse_error()[1]
        log.error(error)
        self.kill()
