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
        # FIXME: Is this special case when *desc* is `None` worth it?
        self.assertIsNone(gsthelpers.make_caps('audio/x-raw', None))

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

