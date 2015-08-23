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

from gi.repository import Gst
from dbase32 import random_id

from .. import gsthelpers


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

    def test_get_framerate(self):
        class MockStructure:
            def __init__(self, ret):
                self._ret = ret

            def get_fraction(self, key):
                assert not hasattr(self, '_key')
                self._key = key
                return self._ret

        s = MockStructure((True, 24000, 1001))
        f = gsthelpers.get_framerate(s)
        self.assertIsInstance(f, Fraction)
        self.assertEqual(f, Fraction(24000, 1001))
        self.assertEqual(s._key, 'framerate')

        s = MockStructure((False, 24000, 1001))
        with self.assertRaises(Exception) as cm:
            gsthelpers.get_framerate(s)
        self.assertEqual(str(cm.exception),
            "could not get 'framerate' from video caps structure"
        )
        self.assertEqual(s._key, 'framerate')


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
        self.assertIsNone(inst.destroy())
        self.assertFalse(hasattr(inst, 'pipeline'))
        self.assertFalse(hasattr(inst, 'bus'))

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
            def __init__(self, pipeline, bus):
                self.pipeline = pipeline
                self.bus = bus
                self.success = None
                self.handlers = []

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

        # Make sure it's well behaved after attributes have been deleted:
        self.assertIsNone(inst.destroy())
        self.assertFalse(hasattr(inst, 'pipeline'))
        self.assertFalse(hasattr(inst, 'bus'))
        self.assertEqual(pipeline._calls, [Gst.State.NULL])
        self.assertEqual(bus._calls, 1)

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

