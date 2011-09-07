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

from gi.repository import GObject, Gst


Gst.init(None)
SECOND = 1000000000  # FIXME: Workaround for broken SECOND
log = logging.getLogger()



stream_map = {
    'video': 'video/x-raw-rgb',
    'audio': 'audio/x-raw-int; audio/x-raw-float',
}


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
    el = Gst.ElementFactory.make(desc['name'], None)
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
    return Gst.caps_from_string(caps_string(desc))



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
        return spec['frame'] * SECOND * denom / num
    if 'sample' in spec:
        rate = doc['samplerate']
        return spec['sample'] * SECOND / rate
    raise ValueError('invalid time spec: {!r}'.format(spec))


def build_slice(doc, builder):
    src = builder.get_doc(doc['node']['src'])
    el = Gst.ElementFactory.make('gnlfilesource', None)
    start = to_gst_time(doc['node']['start'], src)
    stop = to_gst_time(doc['node']['stop'], src)
    duration = stop - start
    el.set_property('media-start', start)
    el.set_property('media-duration', duration)
    el.set_property('duration', duration)
    stream = doc['node']['stream']
    el.set_property('caps', Gst.caps_from_string(stream_map[stream]))
    el.set_property('location', builder.resolve_file(src['_id']))
    return el


def build_sequence(doc, builder):
    el = Gst.ElementFactory.make('gnlcomposition', None)
    start = 0
    for src in doc['node']['src']:
        child = builder.build(src)
        el.add(child)
        child.set_property('start', start)
        start += child.get_property('duration')
    el.set_property('duration', start)
    return el


_builders = {
    'slice': build_slice,
    'sequence': build_sequence,
}


class Builder(object):
    def build(self, _id):
        doc = self.get_doc(_id)
        func = _builders[doc['node']['type']]
        return func(doc, self)

    def resolve_file(self, _id):
        pass

    def get_doc(self, _id):
        pass


class EncoderBin(Gst.Bin):
    """
    Base class for `AudioEncoder` and `VideoEncoder`.
    """

    def __init__(self, d):
        super(EncoderBin, self).__init__()
        self._d = d

        # Create elements
        self._q1 = self._make('queue')
        self._q2 = self._make('queue')
        self._q3 = self._make('queue')
        self._enc = self._make(d['encoder'])

        # Create the filter caps
        self._caps = make_caps(d.get('filter'))

        # Link elements
        if self._caps is None:
            self._q2.link(self._enc)
        else:
            self._q2.link_filtered(self._enc, self._caps)
        self._enc.link(self._q3)

        # Ghost Pads
        self.add_pad(
            Gst.GhostPad.new('sink', self._q1.get_pad('sink'))
        )
        self.add_pad(
            Gst.GhostPad.new('src', self._q3.get_pad('src'))
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
        self._q1.link(self._conv)
        self._conv.link(self._rsp)
        self._rsp.link(self._rate)
        self._rate.link(self._q2)


class VideoEncoder(EncoderBin):
    def __init__(self, d):
        super(VideoEncoder, self).__init__(d)

        # Create elements:
        self._scale = self._make('ffvideoscale', {'method': 10})
        self._color = self._make('ffmpegcolorspace')
        self._rate = self._make('videorate')

        # Link elements:
        self._q1.link(self._scale)
        self._scale.link(self._color)
        self._color.link(self._rate)
        self._rate.link(self._q2)


class Renderer(object):
    def __init__(self, job, builder, dst):
        """
        Initialize.

        :param job: a ``dict`` describing the transcode to perform.
        :param fs: a `FileStore` instance in which to store transcoded file
        """
        self.job = job
        self.builder = builder
        self.mainloop = GObject.MainLoop()
        self.pipeline = Gst.Pipeline()

        # Create bus and connect several handlers
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::eos', self.on_eos)
        self.bus.connect('message::error', self.on_error)

        # Create elements
        self.src = builder.build(job['src'])
        self.mux = make_element(job['muxer'])
        self.sink = Gst.ElementFactory.make('filesink', None)

        # Add elements to pipeline
        self.pipeline.add(self.src, self.mux, self.sink)

        # Set properties
        self.sink.set_property('location', dst)

        # Connect handler for 'new-decoded-pad' signal
        self.src.connect('pad-added', self.on_pad_added)

        # Link *some* elements
        # This is completed in self.on_pad_added()
        self.mux.link(self.sink)

        self.audio = None
        self.video = None

    def run(self):
        self.pipeline.set_state(Gst.STATE_PLAYING)
        self.mainloop.run()

    def kill(self):
        self.pipeline.set_state(Gst.STATE_NULL)
        self.pipeline.get_state()
        self.mainloop.quit()

    def link_pad(self, pad, name, key):
        log.info('link_pad: %r, %r, %r', pad, name, key)
        if key in self.job:
            klass = {'audio': AudioEncoder, 'video': VideoEncoder}[key]
            el = klass(self.job[key])
        else:
            el = Gst.ElementFactory.make('fakesink', None)
        self.pipeline.add(el)
        log.info('Linking pad %r with %r', name, el)
        pad.link(el.get_compatible_pad(pad, pad.get_caps()))
        if key in self.job:
            el.link(self.mux)
        el.set_state(Gst.STATE_PLAYING)
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
