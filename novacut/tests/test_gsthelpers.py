# novacut: the collaborative video editor
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
Unit tests for the `novacut.gsthelpers` module.
"""

from unittest import TestCase
from fractions import Fraction
from random import SystemRandom
import sys

from gi.repository import Gst
from dbase32 import random_id

from ..timefuncs import frame_to_nanosecond
from .. import gsthelpers


random = SystemRandom()


class TestConstants(TestCase):
    def test_FLAGS_ACCURATE(self):
        self.assertEqual(gsthelpers.FLAGS_ACCURATE,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE
        )

    def test_FLAGS_KEY_UNIT(self):
        self.assertEqual(gsthelpers.FLAGS_KEY_UNIT,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT
        )


class TestElementFactoryError(TestCase):
    def test_init(self):
        name = random_id().lower()
        inst = gsthelpers.ElementFactoryError(name)
        self.assertIsInstance(inst, Exception)
        self.assertIs(inst.name, name)
        self.assertEqual(str(inst),
            'Could not make Gst.Element {!r}'.format(name)
        )


class TestFunctions(TestCase):
    def test_make_element(self):
        # Test with bad 'name' type:
        with self.assertRaises(TypeError) as cm:
            gsthelpers.make_element(b'theoraenc')
        self.assertEqual(
            str(cm.exception),
            "name: need a <class 'str'>; got a <class 'bytes'>: b'theoraenc'"
        )

        # Test with bad 'props' type:
        with self.assertRaises(TypeError) as cm:
            gsthelpers.make_element('video/x-raw', 'width=800')
        self.assertEqual(
            str(cm.exception),
            "props: need a <class 'dict'>; got a <class 'str'>: 'width=800'"
        )

        # Test our assumptions about Gst.ElementFactory.make():
        self.assertIsNone(Gst.ElementFactory.make('foobar', None))

        # Test that ElementFactoryError is raised
        with self.assertRaises(gsthelpers.ElementFactoryError) as cm:
            gsthelpers.make_element('foobar')
        self.assertEqual(
            str(cm.exception),
            "Could not make Gst.Element 'foobar'"
        )

        # Test with a good element
        element = gsthelpers.make_element('theoraenc')
        self.assertIsInstance(element, Gst.Element)
        self.assertEqual(element.get_factory().get_name(), 'theoraenc')
        self.assertEqual(element.get_property('quality'), 48)
        self.assertEqual(element.get_property('speed-level'), 1)

        # Test with props also
        element = gsthelpers.make_element('theoraenc',
            {'quality': 40, 'speed-level': 2}
        )
        self.assertIsInstance(element, Gst.Element)
        self.assertEqual(element.get_factory().get_name(), 'theoraenc')
        self.assertEqual(element.get_property('quality'), 40)
        self.assertEqual(element.get_property('speed-level'), 2)

    def test_make_element_from_desc(self):
        el = gsthelpers.make_element_from_desc('theoraenc')
        self.assertIsInstance(el, Gst.Element)
        self.assertEqual(el.get_factory().get_name(), 'theoraenc')
        self.assertEqual(el.get_property('keyframe-force'), 64)
        self.assertEqual(el.get_property('quality'), 48)

        d = {'name': 'theoraenc'}
        el = gsthelpers.make_element_from_desc(d)
        self.assertIsInstance(el, Gst.Element)
        self.assertEqual(el.get_factory().get_name(), 'theoraenc')
        self.assertEqual(el.get_property('keyframe-force'), 64)
        self.assertEqual(el.get_property('quality'), 48)

        d = {
            'name': 'theoraenc',
            'props': {
                'quality': 40,
                'keyframe-force': 16,
            },
        }
        el = gsthelpers.make_element_from_desc(d)
        self.assertIsInstance(el, Gst.Element)
        self.assertEqual(el.get_factory().get_name(), 'theoraenc')
        self.assertEqual(el.get_property('keyframe-force'), 16)
        self.assertEqual(el.get_property('quality'), 40)

    def test_make_make_caps_string(self):
        # mime must be video/x-raw or audio/x-raw:
        with self.assertRaises(ValueError) as cm:
            gsthelpers.make_caps_string('video/x-rawdog', {'format': 'I420'})
        self.assertEqual(str(cm.exception), "bad caps mime: 'video/x-rawdog'")

        # desc must be a dict:
        with self.assertRaises(TypeError) as cm:
            gsthelpers.make_caps_string('video/x-raw', 'format=I420')
        self.assertEqual(str(cm.exception),
            "desc: need a <class 'dict'>; got a <class 'str'>: 'format=I420'"
        )

        self.assertEqual(
            gsthelpers.make_caps_string('audio/x-raw', {}),
            'audio/x-raw'
        )
        self.assertEqual(
            gsthelpers.make_caps_string('audio/x-raw', {'rate': 44100}), 
            'audio/x-raw, rate=44100'
        )
        self.assertEqual(
            gsthelpers.make_caps_string('audio/x-raw', {'rate': 44100, 'channels': 1}),
            'audio/x-raw, channels=1, rate=44100'
        )

        # Special case when value is a Fraction:
        desc = {'whatever': Fraction(24000, 1001)}
        self.assertEqual(
            gsthelpers.make_caps_string('video/x-raw', desc),
            'video/x-raw, whatever=(fraction)24000/1001'
        )

    def test_make_caps(self):
        # audio caps:
        caps = gsthelpers.make_caps('audio/x-raw', {'rate': 44100})
        self.assertIsInstance(caps, Gst.Caps)
        self.assertEqual(caps.to_string(),
            'audio/x-raw, rate=(int)44100'
        )

        caps = gsthelpers.make_caps('audio/x-raw', {'rate': 44100, 'channels': 1})
        self.assertIsInstance(caps, Gst.Caps)
        self.assertEqual(caps.to_string(),
            'audio/x-raw, channels=(int)1, rate=(int)44100'
        )

        # video caps:
        caps = gsthelpers.make_caps('video/x-raw', {'framerate': '24000/1001'})
        self.assertIsInstance(caps, Gst.Caps)
        self.assertEqual(caps.to_string(),
            'video/x-raw, framerate=(fraction)24000/1001'
        )

        caps = gsthelpers.make_caps('video/x-raw',
            {'framerate': '24000/1001', 'format': 'I420'}
        )
        self.assertIsInstance(caps, Gst.Caps)
        self.assertEqual(caps.to_string(),
            'video/x-raw, format=(string)I420, framerate=(fraction)24000/1001'
        )

        # Special video caps case when 'framerate' is a Fraction:
        desc = {
            'framerate': Fraction(30000, 1001),
            'width': 1080,
            'height': 1920,
        }
        caps = gsthelpers.make_caps('video/x-raw', desc)
        self.assertIsInstance(caps, Gst.Caps)
        self.assertEqual(caps.to_string(),
            'video/x-raw, framerate=(fraction)30000/1001, height=(int)1920, width=(int)1080'
        )

    def test_get_int(self):
        class MockStructure:
            def __init__(self, ret):
                self._ret = ret
                self._calls = []

            def get_int(self, name):
                self._calls.append(name)
                return self._ret

        value = random.randrange(0, 1234567890)
        s = MockStructure((True, value))
        name = random_id()
        self.assertIs(gsthelpers.get_int(s, name), value)
        self.assertEqual(s._calls, [name])

        s = MockStructure((False, value))
        with self.assertRaises(Exception) as cm:
            gsthelpers.get_int(s, name)
        self.assertEqual(str(cm.exception),
            'could not get int {!r} from caps structure'.format(name)
        )
        self.assertEqual(s._calls, [name])

    def test_get_fraction(self):
        class MockStructure:
            def __init__(self, ret):
                self._ret = ret
                self._calls = []

            def get_fraction(self, name):
                self._calls.append(name)
                return self._ret

        num = random.randrange(1, 1234567890)
        denom = random.randrange(1, 1234567890)
        s = MockStructure((True, num, denom))
        name = random_id()
        self.assertEqual(gsthelpers.get_fraction(s, name), Fraction(num, denom))
        self.assertEqual(s._calls, [name])

        s = MockStructure((False, num, denom))
        with self.assertRaises(Exception) as cm:
            gsthelpers.get_fraction(s, name)
        self.assertEqual(str(cm.exception),
            'could not get fraction {!r} from caps structure'.format(name)
        )
        self.assertEqual(s._calls, [name])


class Callback:
    def __init__(self):
        self._calls = []

    def __call__(self, inst, success):
        self._calls.append((inst, success))


class TestPipeline(TestCase):
    def test_init(self):
        # callback() not callable:
        bad = random_id()
        with self.assertRaises(TypeError) as cm:
            gsthelpers.Pipeline(bad)
        self.assertEqual(str(cm.exception),
            'callback: not callable: {!r}'.format(bad)
        )

        # callback() is callable:
        def callback(inst, success):
            pass
        inst = gsthelpers.Pipeline(callback)
        self.assertIs(inst.callback, callback)
        self.assertIsNone(inst.success)
        self.assertIsInstance(inst.pipeline, Gst.Pipeline)
        self.assertIsInstance(inst.bus, Gst.Bus)
        self.assertEqual(len(inst.handlers), 2)
        self.assertIs(inst.handlers[0][0], inst.bus)
        self.assertIs(inst.handlers[1][0], inst.bus)
        self.assertIsNone(inst.destroy())
        self.assertFalse(hasattr(inst, 'pipeline'))
        self.assertFalse(hasattr(inst, 'bus'))
        self.assertEqual(sys.getrefcount(inst), 2)

    def test_connect(self):
        class DummyGObject:
            def __init__(self, hid):
                self._hid = hid
                self._calls = []

            def connect(self, signal, callback):
                self._calls.append((signal, callback))
                return self._hid

        class Subclass(gsthelpers.Pipeline):
            def __init__(self):
                self.handlers = []

        inst = Subclass()
        self.assertEqual(inst.handlers, [])
        hid = random_id()
        obj = DummyGObject(hid)
        signal = random_id()
        def callback():
            pass
        self.assertIsNone(inst.connect(obj, signal, callback))
        self.assertEqual(inst.handlers, [(obj, hid)])
        self.assertEqual(obj._calls, [(signal, callback)])

    def test_destroy(self):
        class DummyPipeline:
            def __init__(self):
                self._calls = []

            def set_state(self, state):
                self._calls.append(state)

        class DummyBus:
            def __init__(self):
                self._calls = 0

            def remove_signal_watch(self):
                self._calls += 1

        class Subclass(gsthelpers.Pipeline):
            def __init__(self, pipeline, bus, success=None):
                self.pipeline = pipeline
                self.bus = bus
                self.handlers = []
                self.success = success

        # First try when 'pipeline' and 'bus' attributes exist:
        pipeline = DummyPipeline()
        bus = DummyBus()
        inst = Subclass(pipeline, bus)
        self.assertIs(inst.pipeline, pipeline)
        self.assertIs(inst.bus, bus)
        self.assertIsNone(inst.destroy())
        self.assertFalse(hasattr(inst, 'pipeline'))
        self.assertFalse(hasattr(inst, 'bus'))
        self.assertEqual(pipeline._calls, [Gst.State.NULL])
        self.assertEqual(bus._calls, 1)
        self.assertIs(inst.success, False)
        self.assertEqual(inst.handlers, [])

        # Make sure it's well behaved after attributes have been deleted:
        self.assertIsNone(inst.destroy())
        self.assertFalse(hasattr(inst, 'pipeline'))
        self.assertFalse(hasattr(inst, 'bus'))
        self.assertEqual(pipeline._calls, [Gst.State.NULL])
        self.assertEqual(bus._calls, 1)
        self.assertIs(inst.success, False)
        self.assertEqual(inst.handlers, [])

        # Test when 'success' != None
        pipeline = DummyPipeline()
        bus = DummyBus()
        marker = random_id()
        inst = Subclass(pipeline, bus, success=marker)
        self.assertIs(inst.pipeline, pipeline)
        self.assertIs(inst.bus, bus)
        self.assertIsNone(inst.destroy())
        self.assertFalse(hasattr(inst, 'pipeline'))
        self.assertFalse(hasattr(inst, 'bus'))
        self.assertEqual(pipeline._calls, [Gst.State.NULL])
        self.assertEqual(bus._calls, 1)
        self.assertIs(inst.success, marker)
        self.assertEqual(inst.handlers, [])

        # Test Pipeline.handlers list:
        class DummyGObject:
            def __init__(self):
                self._calls = []

            def handler_disconnect(self, hid):
                self._calls.append(hid)

        pipeline = DummyPipeline()
        bus = DummyBus()
        inst = Subclass(pipeline, bus)
        pairs = tuple(
            (DummyGObject(), random_id()) for i in range(7)
        )
        for item in pairs:
            inst.handlers.append(item)
        self.assertIs(inst.pipeline, pipeline)
        self.assertIs(inst.bus, bus)
        self.assertIsNone(inst.destroy())
        self.assertFalse(hasattr(inst, 'pipeline'))
        self.assertFalse(hasattr(inst, 'bus'))
        self.assertEqual(pipeline._calls, [Gst.State.NULL])
        self.assertEqual(bus._calls, 1)
        self.assertIs(inst.success, False)
        self.assertEqual(inst.handlers, [])
        for (obj, hid) in pairs:
            self.assertEqual(obj._calls, [hid])

    def test_do_complete(self):
        class Subclass(gsthelpers.Pipeline):
            def __init__(self, callback):
                self.callback =  callback
                self.success = None
                self._destroy_calls = 0

            def destroy(self):
                self._destroy_calls += 1

        for success in (True, False):
            callback = Callback()
            inst = Subclass(callback)
            self.assertIsNone(inst.do_complete(success))
            self.assertIs(inst.success, success)
            self.assertEqual(inst._destroy_calls, 1)
            self.assertEqual(callback._calls, [(inst, success)])

    def test_set_state(self):
        class DummyPipeline:
            def __init__(self):
                self._calls = []

            def set_state(self, state):
                self._calls.append(('set_state', state))

            def get_state(self, timeout):
                self._calls.append(('get_state', timeout))

        class Subclass(gsthelpers.Pipeline):
            def __init__(self, pipeline):
                self.pipeline = pipeline

        # When sync is False:
        pipeline = DummyPipeline()
        inst = Subclass(pipeline)
        state = random_id()
        self.assertIsNone(inst.set_state(state))
        self.assertEqual(pipeline._calls, [('set_state', state)])

        # When sync is True:
        pipeline = DummyPipeline()
        inst = Subclass(pipeline)
        state = random_id()
        self.assertIsNone(inst.set_state(state, sync=True))
        self.assertEqual(pipeline._calls,
            [('set_state', state), ('get_state', Gst.CLOCK_TIME_NONE)]
        )

    def test_on_error(self):
        class DummyMessage:
            def __init__(self, error):
                self._error = error
                self._calls = 0

            def parse_error(self):
                self._calls += 1
                return self._error


        class Subclass(gsthelpers.Pipeline):
            def __init__(self):
                self._complete_calls = []

            def complete(self, success):
                self._complete_calls.append(success)

        inst = Subclass() 
        msg = DummyMessage(random_id())
        self.assertIsNone(inst.on_error('bus', msg))
        self.assertEqual(msg._calls, 1)
        self.assertEqual(inst._complete_calls, [False])

    def test_on_eos(self):
        class Subclass(gsthelpers.Pipeline):
            def __init__(self):
                self._complete_calls = []

            def complete(self, success):
                self._complete_calls.append(success)

        inst = Subclass() 
        self.assertIsNone(inst.on_eos('bus', 'msg'))
        self.assertEqual(inst._complete_calls, [False])


class MockStructure:
    def __init__(self, ret):
        assert isinstance(ret, dict)
        self._ret = ret
        self._calls = []

    def __get(self, method, name):
        self._calls.append((method, name))
        # Note: if ever it's valid to extract a value more than once, we should
        # not pop the value here:
        return self._ret.pop(name)

    def get_int(self, name):
        return self.__get('get_int', name)

    def get_fraction(self, name):
        return self.__get('get_fraction', name)


class TestDecoder(TestCase):
    def test_init(self):
        def callback(inst, success):
            pass
        filename = '/tmp/' + random_id() + '.mov'
        inst = gsthelpers.Decoder(callback, filename)
        self.assertIs(inst.unhandled_eos, False)
        self.assertIsNone(inst.check_eos_id)
        self.assertIsNone(inst.framerate)
        self.assertIsNone(inst.rate)
        self.assertIsNone(inst.video_q)
        self.assertIsNone(inst.audio_q)

        # filesrc:
        self.assertIsInstance(inst.src, Gst.Element)
        self.assertEqual(inst.src.get_factory().get_name(), 'filesrc')
        self.assertEqual(inst.src.get_property('location'), filename)

        # decodebin:
        self.assertIsInstance(inst.dec, Gst.Element)
        self.assertEqual(inst.dec.get_factory().get_name(), 'decodebin')

        # Make sure all elements have been added to Pipeline:
        for child in [inst.src, inst.dec]:
            self.assertIs(child.get_parent(), inst.pipeline)

        # Check that Pipeline.connect() was used:
        self.assertEqual(len(inst.handlers), 3)
        self.assertIs(inst.handlers[0][0], inst.bus)
        self.assertIs(inst.handlers[1][0], inst.bus)
        self.assertIs(inst.handlers[2][0], inst.dec)

        # Make sure gsthelpers.Pipeline.__init__() was called:
        self.assertIs(inst.callback, callback)
        self.assertIsInstance(inst.pipeline, Gst.Pipeline)
        self.assertIsInstance(inst.bus, Gst.Bus)
        self.assertEqual(sys.getrefcount(inst), 5)
        self.assertIsNone(inst.destroy())
        self.assertFalse(hasattr(inst, 'pipeline'))
        self.assertFalse(hasattr(inst, 'bus'))
        self.assertEqual(inst.handlers, [])
        self.assertEqual(sys.getrefcount(inst), 2)

        # video=True:
        inst = gsthelpers.Decoder(callback, filename, video=True)
        self.assertIsInstance(inst.video_q, Gst.Element)
        self.assertEqual(inst.video_q.get_factory().get_name(), 'queue')
        self.assertIs(inst.video_q.get_parent(), inst.pipeline)
        self.assertIsNone(inst.audio_q)
        self.assertIsNone(inst.destroy())
        self.assertEqual(inst.handlers, [])
        self.assertEqual(sys.getrefcount(inst), 2)

        # audio=True:
        inst = gsthelpers.Decoder(callback, filename, audio=True)
        self.assertIsNone(inst.video_q)
        self.assertIsInstance(inst.audio_q, Gst.Element)
        self.assertEqual(inst.audio_q.get_factory().get_name(), 'queue')
        self.assertIs(inst.audio_q.get_parent(), inst.pipeline)
        self.assertIsNone(inst.destroy())
        self.assertEqual(inst.handlers, [])
        self.assertEqual(sys.getrefcount(inst), 2)

        # video=True, audio=True:
        inst = gsthelpers.Decoder(callback, filename, video=True, audio=True)
        self.assertIsInstance(inst.video_q, Gst.Element)
        self.assertEqual(inst.video_q.get_factory().get_name(), 'queue')
        self.assertIs(inst.video_q.get_parent(), inst.pipeline)
        self.assertIsInstance(inst.audio_q, Gst.Element)
        self.assertEqual(inst.audio_q.get_factory().get_name(), 'queue')
        self.assertIs(inst.audio_q.get_parent(), inst.pipeline)
        self.assertIsNone(inst.destroy())
        self.assertEqual(inst.handlers, [])
        self.assertEqual(sys.getrefcount(inst), 2)

    def test_seek_simple(self):
        class DummyPipeline:
            def __init__(self):
                self._calls = []

            def seek_simple(self, frmt, flags, ns):
                self._calls.append((frmt, flags, ns))

        class Subclass(gsthelpers.Decoder):
            def __init__(self, pipeline):
                self.pipeline = pipeline

        pipeline = DummyPipeline()
        inst = Subclass(pipeline)
        ns = random.randrange(0, 1234567890)
        self.assertIsNone(inst.seek_simple(ns))
        self.assertEqual(pipeline._calls, [
            (Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE, ns),
        ])

        pipeline = DummyPipeline()
        inst = Subclass(pipeline)
        ns = random.randrange(0, 1234567890)
        self.assertIsNone(inst.seek_simple(ns, key_unit=True))
        self.assertEqual(pipeline._calls, [
            (Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, ns),
        ])

    def test_seek_by_frame(self):
        class Subclass(gsthelpers.Decoder):
            def __init__(self, framerate):
                self.framerate = framerate
                self._calls = []

            def seek_simple(self, ns, key_unit):
                self._calls.append((ns, key_unit))

        framerate = Fraction(30000, 1001)

        inst = Subclass(framerate)
        self.assertIsNone(inst.seek_by_frame(0))
        self.assertEqual(inst._calls, [(0, False)])
        inst = Subclass(framerate)
        self.assertIsNone(inst.seek_by_frame(0, key_unit=True))
        self.assertEqual(inst._calls, [(0, True)])

        inst = Subclass(framerate)
        self.assertIsNone(inst.seek_by_frame(1))
        self.assertEqual(inst._calls, [(33366666, False)])
        inst = Subclass(framerate)
        self.assertIsNone(inst.seek_by_frame(1, key_unit=True))
        self.assertEqual(inst._calls, [(33366666, True)])

        inst = Subclass(framerate)
        self.assertIsNone(inst.seek_by_frame(2))
        self.assertEqual(inst._calls, [(66733333, False)])
        inst = Subclass(framerate)
        self.assertIsNone(inst.seek_by_frame(2, key_unit=True))
        self.assertEqual(inst._calls, [(66733333, True)])

        for i in range(500):
            frame = random.randrange(1234567)
            ns = frame_to_nanosecond(frame, framerate)
            inst = Subclass(framerate)
            self.assertIsNone(inst.seek_by_frame(frame))
            self.assertEqual(inst._calls, [(ns, False)])
            inst = Subclass(framerate)
            self.assertIsNone(inst.seek_by_frame(frame, key_unit=True))
            self.assertEqual(inst._calls, [(ns, True)])

    def test_extract_video_info(self):
        class Subclass(gsthelpers.Decoder):
            def __init__(self):
                self.framerate = None

        num = random.randrange(1, 1234567890)
        denom = random.randrange(1, 1234567890)
        s = MockStructure({'framerate': (True, num, denom)})
        inst = Subclass()
        self.assertIsNone(inst.extract_video_info(s))
        self.assertEqual(inst.framerate, Fraction(num, denom))
        self.assertEqual(s._ret, {})
        self.assertEqual(s._calls, [('get_fraction', 'framerate')])

        s = MockStructure({'framerate': (False, num, denom)})
        inst = Subclass()
        with self.assertRaises(Exception) as cm:
            inst.extract_video_info(s) 
        self.assertEqual(str(cm.exception),
            "could not get fraction 'framerate' from caps structure"
        )
        self.assertEqual(s._ret, {})
        self.assertEqual(s._calls, [('get_fraction', 'framerate')])
        self.assertIsNone(inst.framerate)

    def test_extract_audio_info(self):
        class Subclass(gsthelpers.Decoder):
            def __init__(self):
                self.rate = None

        value = random.randrange(1, 1234567890)
        s = MockStructure({'rate': (True, value)})
        inst = Subclass()
        self.assertIsNone(inst.extract_audio_info(s))
        self.assertIs(inst.rate, value)
        self.assertEqual(s._ret, {})
        self.assertEqual(s._calls, [('get_int', 'rate')])

        s = MockStructure({'rate': (False, value)})
        inst = Subclass()
        with self.assertRaises(Exception) as cm:
            inst.extract_audio_info(s) 
        self.assertEqual(str(cm.exception),
            "could not get int 'rate' from caps structure"
        )
        self.assertEqual(s._ret, {})
        self.assertEqual(s._calls, [('get_int', 'rate')])
        self.assertIsNone(inst.rate)

    def test_on_pad_added(self):
        class Subclass(gsthelpers.Decoder):
            def __init__(self, video_q, audio_q):
                self.video_q = video_q
                self.audio_q = audio_q
                self._calls = []

            def complete(self, success):
                self._calls.append(('complete', success))

            def extract_video_info(self, structure):
                self._calls.append(('extract_video_info', structure))

            def extract_audio_info(self, structure):
                self._calls.append(('extract_audio_info', structure))

        class MockPad:
            def __init__(self, caps):
                self._caps = caps
                self._calls = []

            def get_current_caps(self):
                self._calls.append('get_current_caps')
                if isinstance(self._caps, Exception):
                    raise self._caps
                return self._caps

            def link(self, pad):
                self._calls.append(('link', pad))

        class MockCaps:
            def __init__(self, string):
                self._string = string
                self._s = random_id()
                self._calls = []

            def to_string(self):
                self._calls.append('to_string')
                return self._string

            def get_structure(self, index):
                self._calls.append(('get_structure', index))
                return self._s

        ####################################################
        # First test when both video_q and audio_q are None:

        # video/x-raw:
        inst = Subclass(None, None)
        caps = MockCaps('video/x-raw, foo=bar, stuff=junk')
        pad = MockPad(caps)
        self.assertIsNone(inst.on_pad_added('element', pad))
        self.assertEqual(pad._calls, ['get_current_caps'])
        self.assertEqual(caps._calls, ['to_string'])
        self.assertEqual(inst._calls, [])

        # audio/x-raw:
        inst = Subclass(None, None)
        caps = MockCaps('audio/x-raw, foo=bar, stuff=junk')
        pad = MockPad(caps)
        self.assertIsNone(inst.on_pad_added('element', pad))
        self.assertEqual(pad._calls, ['get_current_caps'])
        self.assertEqual(caps._calls, ['to_string'])
        self.assertEqual(inst._calls, [])

        # caps string that should be ignored:
        inst = Subclass(None, None)
        caps = MockCaps('audio/x-nah, foo=bar, stuff=junk')
        pad = MockPad(caps)
        self.assertIsNone(inst.on_pad_added('element', pad))
        self.assertEqual(pad._calls, ['get_current_caps'])
        self.assertEqual(caps._calls, ['to_string'])
        self.assertEqual(inst._calls, [])

        # Make sure Pipeline.complete(False) is called on unhandled exception:
        inst = Subclass(None, None)
        marker = random_id()
        exc = ValueError(marker)
        pad = MockPad(exc)
        with self.assertRaises(ValueError) as cm:
            inst.on_pad_added('element', pad)
        self.assertIs(cm.exception, exc)
        self.assertEqual(str(cm.exception), marker)
        self.assertEqual(pad._calls, ['get_current_caps'])
        self.assertEqual(inst._calls, [('complete', False)])

        ##################################################################
        # Do it all over again, this time with mocked video_q and audio_q:
        class MockQueue:
            def __init__(self):
                self._pad = random_id()
                self._calls = []

            def get_static_pad(self, name):
                self._calls.append(name)
                return self._pad

        vq = MockQueue()
        aq = MockQueue()
        inst = Subclass(vq, aq)

        # video/x-raw:
        vcaps = MockCaps('video/x-raw, foo=bar, stuff=junk')
        pad = MockPad(vcaps)
        self.assertIsNone(inst.on_pad_added('element', pad))
        self.assertEqual(pad._calls, ['get_current_caps', ('link', vq._pad)])
        self.assertEqual(vcaps._calls, ['to_string', ('get_structure', 0)])
        self.assertEqual(vq._calls, ['sink'])
        self.assertEqual(aq._calls, [])
        self.assertEqual(inst._calls, [('extract_video_info', vcaps._s)])

        # audio/x-raw:
        acaps = MockCaps('audio/x-raw, foo=bar, stuff=junk')
        pad = MockPad(acaps)
        self.assertIsNone(inst.on_pad_added('element', pad))
        self.assertEqual(pad._calls, ['get_current_caps', ('link', aq._pad)])
        self.assertEqual(vcaps._calls, ['to_string', ('get_structure', 0)])
        self.assertEqual(acaps._calls, ['to_string', ('get_structure', 0)])
        self.assertEqual(vq._calls, ['sink'])
        self.assertEqual(aq._calls, ['sink'])
        self.assertEqual(inst._calls,
            [('extract_video_info', vcaps._s), ('extract_audio_info', acaps._s)]
        )

        # caps string that should be ignored:
        vq = MockQueue()
        aq = MockQueue()
        inst = Subclass(vq, aq)
        caps = MockCaps('video/x-nah, foo=bar, stuff=junk')
        pad = MockPad(caps)
        self.assertIsNone(inst.on_pad_added('element', pad))
        self.assertEqual(pad._calls, ['get_current_caps'])
        self.assertEqual(caps._calls, ['to_string'])
        self.assertEqual(vq._calls, [])
        self.assertEqual(aq._calls, [])
        self.assertEqual(inst._calls, [])

        # Make sure Pipeline.complete(False) is called on unhandled exception:
        vq = MockQueue()
        aq = MockQueue()
        inst = Subclass(vq, aq)
        marker = random_id()
        exc = ValueError(marker)
        pad = MockPad(exc)
        with self.assertRaises(ValueError) as cm:
            inst.on_pad_added('element', pad)
        self.assertIs(cm.exception, exc)
        self.assertEqual(str(cm.exception), marker)
        self.assertEqual(pad._calls, ['get_current_caps'])
        self.assertEqual(vq._calls, [])
        self.assertEqual(aq._calls, [])
        self.assertEqual(inst._calls, [('complete', False)])

