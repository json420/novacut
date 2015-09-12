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

"""
A few Python helpers for working with `gi.repository.Gst`.

Please exercise thoughtful restraint when adding things to this module as we
don't want to accumulate too much magic wrapper sauce!
"""

from fractions import Fraction
import logging

from gi.repository import Gst, GLib


log = logging.getLogger(__name__)
Gst.init()


# Provide very clear TypeError messages:
TYPE_ERROR = '{}: need a {!r}; got a {!r}: {!r}'


class ElementFactoryError(Exception):
    """
    Raised when `Gst.ElementFactory.make()` fails.

    When `Gst.ElementFactory.make()` fails to create an element, it returns
    `None` rather than raising an exception.  This can make debugging
    difficult if the calling code doesn't immediately check it, because
    otherwise you'll later get a mystery error like this::

        AttributeError: 'NoneType' object has no attribute 'set_property'

    So the guidance for Novacut is to use the `make_element()` function below,
    which will raise this exception if `Gst.ElementFactory.make()` returns
    `None`.
    """

    def __init__(self, name):
        self.name = name
        super().__init__('Could not make Gst.Element {!r}'.format(name))


def make_element(name, props=None):
    """
    Create a new `Gst.Element`, optionally setting its GObject properties.

    This function will return a new `Gst.Element`, for example:

    >>> enc = make_element('theoraenc')

    If provided, the optional *props* argument must be a `dict` mapping GObject
    property names to the values you wish to set.  This is a nice shorthand when
    setting multiple properties.

    For example, we could now set the "quality" and "keyframe-freq" properties
    on the `enc` element we created above:

    >>> enc.set_property('quality', 56)
    >>> enc.set_property('keyframe-freq', 16)

    Or we could have achieved the same all in one go like this:

    >>> enc = make_element('theoraenc', {'quality': 56, 'keyframe-freq': 16})

    Note: in Novacut code, please use this function instead of directly using
    `Gst.ElementFactory.make()`.

    This function will raise our custom `ElementFactoryError` exception if the
    element could not be created, whereas the latter will simply return `None`.
    """
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
        raise ElementFactoryError(name)
    if props:
        for (key, value) in props.items():
            element.set_property(key, value)
    return element


def make_element_from_desc(desc):
    """
    Create a `Gst.Element` from a JSON-serializable description.

    For example:

    >>> enc = make_element_from_desc('theoraenc')
    >>> enc.get_factory().get_name()
    'theoraenc'
    
    Or from a ``dict`` with the element name:

    >>> enc = make_element_from_desc({'name': 'theoraenc'})
    >>> enc.get_factory().get_name()
    'theoraenc'
    >>> enc.get_property('quality')
    48

    Or from a ``dict`` with the element name and props:

    >>> enc = make_element_from_desc({'name': 'theoraenc', 'props': {'quality': 40}})
    >>> enc.get_factory().get_name()
    'theoraenc'
    >>> enc.get_property('quality')
    40

    """
    if isinstance(desc, dict):
        return make_element(desc['name'], desc.get('props'))
    return make_element(desc)


def make_caps_string(mime, desc):
    """
    Build a string for passing to `Gst.caps_from_string()`.

    For example:

    >>> make_caps_string('video/x-raw', {'width': 800, 'height': 450})
    'video/x-raw, height=450, width=800'

    This function is used by `make_caps()`.
    """
    if mime not in ('audio/x-raw', 'video/x-raw'):
        raise ValueError('bad caps mime: {!r}'.format(mime))
    if not isinstance(desc, dict):
        raise TypeError(
            TYPE_ERROR.format('desc', dict, type(desc), desc)
        )
    accum = [mime]
    for (key, val) in sorted(desc.items()):
        if isinstance(val, Fraction):
            val = '(fraction){}/{}'.format(val.numerator, val.denominator)
        accum.append('{}={}'.format(key, val))
    return ', '.join(accum)


def make_caps(mime, desc):
    """
    Build `Gst.Caps` from a JSON-serializable description in *desc*.

    For example:

    >>> caps = make_caps('video/x-raw', {'width': 800, 'height': 450})
    >>> caps.to_string()
    'video/x-raw, height=(int)450, width=(int)800'

    """
    return Gst.caps_from_string(make_caps_string(mime, desc))


def get_int(structure, name):
    (success, value) = structure.get_int(name)
    if not success:
        raise Exception(
            'could not get int {!r} from caps structure'.format(name)
        )
    return value


def get_fraction(structure, name):
    (success, num, denom) = structure.get_fraction(name)
    if not success:
        raise Exception(
            'could not get fraction {!r} from caps structure'.format(name)
        )
    return Fraction(num, denom)


def get_framerate(structure):
    return get_fraction(structure, 'framerate')


def add_elements(parent, *elements):
    for el in elements:
        parent.add(el)


def link_elements(*elements):
    last = None
    for el in elements:
        if last is not None:
            last.link(el)
        last = el


def add_and_link_elements(parent, *elements):
    add_elements(parent, *elements)
    link_elements(*elements)


class Pipeline:
    def __init__(self, callback):
        if not callable(callback):
            raise TypeError(
                'callback: not callable: {!r}'.format(callback)
            )
        self.callback = callback
        self.handlers = []
        self.success = None
        self.pipeline = Gst.Pipeline()
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.connect(self.bus, 'message::error', self.on_error)
        self.connect(self.bus, 'message::eos', self.on_eos)

    def connect(self, obj, signal, callback):
        hid = obj.connect(signal, callback)
        self.handlers.append((obj, hid))

    def destroy(self):
        while self.handlers:
            (obj, hid) = self.handlers.pop()
            obj.handler_disconnect(hid)
        if self.success is None:
            self.success = False
        if hasattr(self, 'bus'):
            self.bus.remove_signal_watch()
            del self.bus
        if hasattr(self, 'pipeline'):
            self.pipeline.set_state(Gst.State.NULL)
            del self.pipeline

    def do_complete(self, success):
        log.debug('%s.complete(%r)', self.__class__.__name__, success)
        if self.success is not None:
            log.error('%s.complete() already called, ignoring',
                self.__class__.__name__
            )
            return
        self.success = (True if success is True else False)
        self.destroy()
        self.callback(self, self.success)

    def complete(self, success):
        """
        Calls Pipeline.do_complete() via GLib.idle_add().

        It seems you probably can't call Gst.Bus.remove_signal_watch() from
        within a callback for a signal it fired, otherwise you get a deadlock.

        But we don't want the complexity of having to run the mainloop for most
        unit tests, so this method can be overridden in special test subclasses.
        """
        GLib.idle_add(self.do_complete, success)

    def set_state(self, state, sync=False):
        assert isinstance(sync, bool)
        self.pipeline.set_state(state)
        if sync is True:
            self.pipeline.get_state(Gst.CLOCK_TIME_NONE)

    def on_error(self, bus, msg):
        log.error('%s.on_error(): %s',
            self.__class__.__name__, msg.parse_error()
        )
        self.complete(False)

    def on_eos(self, bus, msg):
        log.error('subclass %s did not override Pipeline.on_eos()',
            self.__class__.__name__
        )
        self.complete(False)


class Decoder(Pipeline):
    def __init__(self, callback, filename, video=False, audio=False):
        super().__init__(callback)
        self.framerate = None
        self.rate = None

        # Create elements:
        self.src = make_element('filesrc', {'location': filename})
        self.dec = make_element('decodebin')
        self.video_q = (make_element('queue') if video is True else None)
        self.audio_q = (make_element('queue') if audio is True else None)

        # Add elements to pipeline and link:
        add_and_link_elements(self.pipeline, self.src, self.dec)
        for q in (self.video_q, self.audio_q):
            if q is not None:
                self.pipeline.add(q)

        # Connect signal handlers using Pipeline.connect():
        self.connect(self.dec, 'pad-added', self.on_pad_added)

    def extract_video_info(self, structure):
        self.framerate = get_fraction(structure, 'framerate')

    def extract_audio_info(self, structure):
        self.rate = get_int(structure, 'rate')

    def on_pad_added(self, dec, pad):
        caps = pad.get_current_caps()
        string = caps.to_string()
        structure = caps.get_structure(0)
        log.debug('%s.on_pad_added(): %s', self.__class__.__name__, string)
        if string.startswith('video/x-raw'):
            self.extract_video_info(structure)
            if self.video_q is not None:
                pad.link(self.video_q.get_static_pad('sink'))
        elif string.startswith('audio/x-raw'):
            self.extract_audio_info(structure)
            if self.audio_q is not None:
                pad.link(self.audio_q.get_static_pad('sink'))

