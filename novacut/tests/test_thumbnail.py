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
Unit tests for the `novacut.validate` module.
"""

from unittest import TestCase
import os
import sys
from base64 import b64encode

from gi.repository import Gst
from dbase32 import random_id

from .helpers import random
from ..gsthelpers import USE_HACKS, VIDEOSCALE_METHOD
from ..misc import random_start_stop
from .. import thumbnail


class TestFunctions(TestCase):
    def test_get_slice_for_thumbnail(self):
        get_slice_for_thumbnail = thumbnail.get_slice_for_thumbnail

        # frame in existing:
        for frame in range(100):
            self.assertIsNone(get_slice_for_thumbnail({frame}, frame, 200))

        # frame=0, no existing, then existing at frame 3:
        for eg in [set(), {3}]:
            s = get_slice_for_thumbnail(eg, 0, 99)
            self.assertIsInstance(s, thumbnail.StartStop)
            self.assertEqual(s, (0, 3))
            self.assertEqual(s.stop - s.start, 3)

        # frame=0, existing at frame 2:
        s = get_slice_for_thumbnail({2}, 0, 99)
        self.assertIsInstance(s, thumbnail.StartStop)
        self.assertEqual(s, (0, 2))
        self.assertEqual(s.stop - s.start, 2)

        # frame=0, existing at frame 1:
        s = get_slice_for_thumbnail({1}, 0, 99)
        self.assertIsInstance(s, thumbnail.StartStop)
        self.assertEqual(s, (0, 1))
        self.assertEqual(s.stop - s.start, 1)

        # frame=98, no existing, then existing at frame 95:
        for eg in [set(), {95}]:
            s = get_slice_for_thumbnail(eg, 98, 99)
            self.assertIsInstance(s, thumbnail.StartStop)
            self.assertEqual(s, (96, 99))
            self.assertEqual(s.stop - s.start, 3)

        # frame=98, existing at frame 96:
        s = get_slice_for_thumbnail({96}, 98, 99)
        self.assertIsInstance(s, thumbnail.StartStop)
        self.assertEqual(s, (97, 99))
        self.assertEqual(s.stop - s.start, 2)

        # frame=98, existing at frame 97:
        s = get_slice_for_thumbnail({97}, 98, 99)
        self.assertIsInstance(s, thumbnail.StartStop)
        self.assertEqual(s, (98, 99))
        self.assertEqual(s.stop - s.start, 1)

        # frame=33, not constrained on either side:
        for eg in [set(), {31, 35}]:
            s = get_slice_for_thumbnail(eg, 33, 99)
            self.assertIsInstance(s, thumbnail.StartStop)
            self.assertEqual(s, (32, 35))
            self.assertEqual(s.stop - s.start, 3)

        # frame=33, constrained by {32, 34}:
        s = get_slice_for_thumbnail({32, 34}, 33, 99)
        self.assertIsInstance(s, thumbnail.StartStop)
        self.assertEqual(s, (33, 34))
        self.assertEqual(s.stop - s.start, 1)

        # frame=33, constrained by 32 behind, should walk forward 10 frames:
        s = get_slice_for_thumbnail({32}, 33, 99)
        self.assertIsInstance(s, thumbnail.StartStop)
        self.assertEqual(s, (33, 43))
        self.assertEqual(s.stop - s.start, 10)

        # frame=33, constrained by 34 ahead, should walk backward 10 frames:
        s = get_slice_for_thumbnail({34}, 33, 99)
        self.assertIsInstance(s, thumbnail.StartStop)
        self.assertEqual(s, (24, 34))
        self.assertEqual(s.stop - s.start, 10)

    def test_attachments_to_existing(self):
        indexes = tuple(random.randrange(0, 5000) for i in range(17))
        attachments = dict(
            (str(i), {random_id: random_id}) for i in indexes
        )
        existing = thumbnail.attachments_to_existing(attachments)
        self.assertIsInstance(existing, set)
        self.assertEqual(existing, set(indexes))

    def test_update_attachments(self):
        data1 = os.urandom(200)
        data2 = os.urandom(17)
        data3 = os.urandom(333)
        attachments = {}
        thumbnails = [
            (0, data1),
            (17, data2),
            (29, data3),
        ]
        self.assertIsNone(thumbnail.update_attachments(attachments, thumbnails))
        self.assertEqual(attachments,
            {
                '0': {
                    'content_type': 'image/jpeg',
                    'data': b64encode(data1).decode(),
                },
                '17': {
                    'content_type': 'image/jpeg',
                    'data': b64encode(data2).decode(),
                },
                '29': {
                    'content_type': 'image/jpeg',
                    'data': b64encode(data3).decode(),
                },
            }
        )


class TestThumbnailer(TestCase):
    def test_init(self):
        def callback(inst, success):
            pass

        filename = '/tmp/' + random_id() + '.mov'
        indexes = [random.randrange(0, 5000) for i in range(15)]
        existing = set(random.randrange(0, 5000) for i in range(20))
        inst = thumbnail.Thumbnailer(callback, filename, indexes, existing)
        self.assertEqual(inst.indexes, sorted(set(indexes)))
        self.assertIs(inst.existing, existing)
        self.assertIsNone(inst.framerate)
        self.assertIsNone(inst.file_stop)
        self.assertIsNone(inst.s)
        self.assertIsNone(inst.frame)
        self.assertEqual(inst.thumbnails, [])

        # filesrc:
        self.assertIsInstance(inst.src, Gst.Element)
        self.assertEqual(inst.src.get_factory().get_name(), 'filesrc')
        self.assertEqual(inst.src.get_property('location'), filename)

        # decodebin:
        self.assertIsInstance(inst.dec, Gst.Element)
        self.assertEqual(inst.dec.get_factory().get_name(), 'decodebin')

        # video and audio queues:
        self.assertIsInstance(inst.video_q, Gst.Element)
        self.assertEqual(inst.video_q.get_factory().get_name(), 'queue')
        self.assertIsNone(inst.audio_q)

        # videoconvert:
        self.assertIsInstance(inst.convert, Gst.Element)
        self.assertEqual(inst.convert.get_factory().get_name(), 'videoconvert')

        # videoscale:
        self.assertIsInstance(inst.scale, Gst.Element)
        self.assertEqual(inst.scale.get_factory().get_name(), 'videoscale')
        self.assertEqual(inst.scale.get_property('method'), VIDEOSCALE_METHOD)

        # jpegenc:
        self.assertIsInstance(inst.enc, Gst.Element)
        self.assertEqual(inst.enc.get_factory().get_name(), 'jpegenc')
        self.assertEqual(inst.enc.get_property('idct-method'), 2)

        # fakesink:
        self.assertIsInstance(inst.sink, Gst.Element)
        self.assertEqual(inst.sink.get_factory().get_name(), 'fakesink')
        self.assertEqual(inst.sink.get_property('signal-handoffs'), True)

        # Make sure all elements have been added to pipeline:
        children = (
            inst.src,
            inst.dec,
            inst.video_q,
            inst.convert,
            inst.scale,
            inst.enc,
            inst.sink,
        )
        for child in children:
            self.assertIs(child.get_parent(), inst.pipeline)

        # Check that Pipeline.connect() was used:
        self.assertEqual(len(inst.handlers), 4)
        self.assertIs(inst.handlers[0][0], inst.bus)
        self.assertIs(inst.handlers[1][0], inst.bus)
        self.assertIs(inst.handlers[2][0], inst.dec)
        self.assertIs(inst.handlers[3][0], inst.sink)

        # Make sure gsthelpers.Pipeline.__init__() was called:
        self.assertIs(inst.callback, callback)
        self.assertIsInstance(inst.pipeline, Gst.Pipeline)
        self.assertIsInstance(inst.bus, Gst.Bus)
        self.assertEqual(sys.getrefcount(inst), 6)
        self.assertIsNone(inst.destroy())
        self.assertFalse(hasattr(inst, 'pipeline'))
        self.assertFalse(hasattr(inst, 'bus'))
        self.assertEqual(inst.handlers, [])
        self.assertEqual(sys.getrefcount(inst), 2)

    def test_play_slice(self):
        class Subclass(thumbnail.Thumbnailer):
            def __init__(self, file_stop):
                assert file_stop > 0
                self.file_stop = file_stop
                self._calls = []

            def seek_by_frame(self, start, stop):
                self._calls.append((start, stop))

        inst = Subclass(1)
        s = thumbnail.StartStop(0, 1)
        self.assertIsNone(inst.play_slice(s))
        self.assertIs(inst.s, s)
        stop = (None if USE_HACKS else s.stop)
        self.assertEqual(inst._calls, [(0, stop)])

        file_stop = random.randrange(1234, 12345679)
        inst = Subclass(file_stop)
        s = thumbnail.StartStop(0, 1)
        self.assertIsNone(inst.play_slice(s))
        self.assertIs(inst.s, s)
        stop = (None if USE_HACKS else s.stop)
        self.assertEqual(inst._calls, [(0, stop)])

        inst = Subclass(file_stop)
        s = thumbnail.StartStop(file_stop - 1, file_stop)
        self.assertIsNone(inst.play_slice(s))
        self.assertIs(inst.s, s)
        stop = (None if USE_HACKS else s.stop)
        self.assertEqual(inst._calls, [(file_stop - 1, stop)])

        for i in range(100):
            inst = Subclass(file_stop)
            s = random_start_stop(file_stop)
            self.assertIsNone(inst.play_slice(s))
            self.assertIs(inst.s, s)
            stop = (None if USE_HACKS else s.stop)
            self.assertEqual(inst._calls, [(s.start, stop)])

    def test_next(self):
        class Subclass(thumbnail.Thumbnailer):
            __slots__ = (
                'indexes',
                'existing',
                'file_stop',
                'thumbnails',
                '_calls',
            )

            def __init__(self, indexes, existing, file_stop):
                self.indexes = indexes
                self.existing = existing
                self.file_stop = file_stop
                self.thumbnails = []
                self._calls = []

            def play_slice(self, s):
                self._calls.append(('play_slice', s))

            def complete(self, success):
                self._calls.append(('complete', success))

        indexes = [2, 17, 18, 19]
        existing = {18}
        inst = Subclass(indexes, existing, 23)

        # Frame 2: should play slice [1:4]
        self.assertIsNone(inst.next())
        self.assertEqual(inst.indexes, [17, 18, 19])
        self.assertEqual(inst.existing, {18})
        self.assertEqual(inst._calls, [
            ('play_slice', (1, 4)),
        ])

        # Frame 17: as 18 exists, should walk backward 10 frames
        self.assertIsNone(inst.next())
        self.assertEqual(inst.indexes, [18, 19])
        self.assertEqual(inst.existing, {18})
        self.assertEqual(inst._calls, [
            ('play_slice', (1, 4)),
            ('play_slice', (8, 18)),
        ])

        # Frame 18: exists, should be skipped
        # Frame 19: as 18 exists, should walk forward up to file_stop
        self.assertIsNone(inst.next())
        self.assertEqual(inst.indexes, [])
        self.assertEqual(inst.existing, {18})
        self.assertEqual(inst._calls, [
            ('play_slice', (1, 4)),
            ('play_slice', (8, 18)),
            ('play_slice', (19, 23)),
        ])

        # Pipeline.complete() should be called once indexes is empty:
        self.assertIsNone(inst.next())
        self.assertEqual(inst.indexes, [])
        self.assertEqual(inst.existing, {18})
        self.assertEqual(inst.thumbnails, [])
        self.assertEqual(inst._calls, [
            ('play_slice', (1, 4)),
            ('play_slice', (8, 18)),
            ('play_slice', (19, 23)),
            ('complete', True),
        ])

