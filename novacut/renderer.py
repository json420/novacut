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

import gst

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
    >>> to_gst_time({'frame': 48}, doc)
    2000000000
    >>> to_gst_time({'sample': 96000}, doc)
    2000000000

    """
    if 'frame' in spec:
        num = doc['framerate']['num']
        denom = doc['framerate']['denom']
        return spec['frame'] * gst.SECOND * denom / num
    if 'sample' in spec:
        rate = doc['samplerate']
        return spec['sample'] * gst.SECOND / rate
    raise ValueError('invalid time spec: {!r}'.format(spec))


def build_slice(doc, builder):
    src = builder.get_doc(doc['node']['src'])
    el = gst.element_factory_make('gnlfilesource')
    start = to_gst_time(doc['node']['start'], src)
    stop = to_gst_time(doc['node']['stop'], src)
    duration = stop - start
    el.set_property('media-start', start)
    el.set_property('media-duration', duration)
    el.set_property('duration', duration)
    stream = doc['node']['stream']
    el.set_property('caps', gst.caps_from_string(stream_map[stream]))
    el.set_property('location', builder.resolve_file(src['_id']))
    return el


def build_sequence(doc, builder):
    el = gst.element_factory_make('gnlcomposition')
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


class EncoderBin(gst.Bin):
    """
    Base class for `AudioEncoder` and `VideoEncoder`.
    """

    def __init__(self, d):
        super(EncoderBin, self).__init__()
        self._d = d

        # Create elements
        self._q1 = self._make('queue2')
        self._q2 = self._make('queue2')
        self._q3 = self._make('queue2')
        self._enc = self._make(d['enc'])

        # Create the filter caps
        self._caps = make_caps(d.get('filter'))

        # Link elements
        if self._caps is None:
            self._q2.link(self._enc)
        else:
            self._q2.link(self._enc, self._caps)
        self._enc.link(self._q3)

        # Ghost Pads
        self.add_pad(
            gst.GhostPad('sink', self._q1.get_pad('sink'))
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
        self._q1.link(self._conv)
        gst.element_link_many(self._conv, self._rsp, self._rate)
        self._rate.link(self._q2)
