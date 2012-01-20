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

import sys
import gst
import gobject


gobject.threads_init()


class FakeBin(gst.Bin):
    def __init__(self, rate):
        super(FakeBin, self).__init__()
        self._doc = {}
        self._q = gst.element_factory_make('queue')
        self._rate = gst.element_factory_make(rate)
        self._sink = gst.element_factory_make('fakesink')
        self.add(self._q, self._rate, self._sink)
        self._q.link(self._rate)
        self._rate.link(self._sink)

        # Ghost Pads
        pad = self._q.get_pad('sink')
        self.add_pad(
            gst.GhostPad('sink', pad)
        )
        pad.connect('notify::caps', self._on_notify_caps)

    def _get_doc(self):
        self._finalize()
        return self._doc
        
    def _query_duration(self, pad):
        q = gst.query_new_duration(gst.FORMAT_TIME)
        if pad.get_peer().query(q):
            (format, duration) = q.parse_duration()
            if format == gst.FORMAT_TIME:
                return duration


class VideoBin(FakeBin):
    def __init__(self):
        super(VideoBin, self).__init__('videorate')

    def _on_notify_caps(self, pad, args):
        caps = pad.get_negotiated_caps()
        if not caps:
            return
        d = caps[0]
        self._doc['framerate'] = {
            'num': d['framerate'].num,
            'denom': d['framerate'].denom,
        }
        self._doc['width'] = d['width']
        self._doc['height'] = d['height']
        duration = self._query_duration(pad)
        if duration:
            self._doc['ns'] = duration
            self._doc['duration'] = float(duration) / gst.SECOND

    def _finalize(self):
        self._doc['frames'] = self._rate.get_property('in')


class AudioBin(FakeBin):
    def __init__(self):
        super(AudioBin, self).__init__('audiorate')

    def _on_notify_caps(self, pad, args):
        caps = pad.get_negotiated_caps()
        if not caps:
            return
        d = caps[0]
        self._doc['samplerate'] = d['rate']
        self._doc['channels'] = d['channels']
        duration = self._query_duration(pad)
        if duration:
            self._doc['samples'] = d['rate'] * duration / gst.SECOND

    def _finalize(self):
        # FIXME: why is this so worthless?
        if 'samples' not in self._doc:
            self._doc['samples'] = self._rate.get_property('in')


class Extractor(object):
    def __init__(self, filename):
        self.doc = {}
        self.mainloop = gobject.MainLoop()
        self.pipeline = gst.Pipeline()

        # Create bus and connect several handlers
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::eos', self.on_eos)
        self.bus.connect('message::error', self.on_error)

        # Create elements
        self.src = gst.element_factory_make('filesrc')
        self.dec = gst.element_factory_make('decodebin2')

        # Set properties
        self.src.set_property('location', filename)

        # Connect handler for 'new-decoded-pad' signal
        self.dec.connect('pad-added', self.on_pad_added)
        self.typefind = self.dec.get_by_name('typefind')
        self.typefind.connect('have-type', self.on_have_type)

        # Add elements to pipeline
        self.pipeline.add(self.src, self.dec)

        # Link elements
        self.src.link(self.dec)

        self.audio = None
        self.video = None

    def run(self):
        self.pipeline.set_state(gst.STATE_PLAYING)
        self.mainloop.run()

    def kill(self):
        self.pipeline.set_state(gst.STATE_NULL)
        self.pipeline.get_state()
        self.mainloop.quit()

    def link_pad(self, pad, name):
        cls = {'audio': AudioBin, 'video': VideoBin}[name]
        fakebin = cls()
        self.pipeline.add(fakebin)
        pad.link(fakebin.get_pad('sink'))
        fakebin.set_state(gst.STATE_PLAYING)
        return fakebin

    def on_pad_added(self, element, pad):
        name = pad.get_caps()[0].get_name()
        if name.startswith('audio/'):
            assert self.audio is None
            self.audio = self.link_pad(pad, 'audio')
        elif name.startswith('video/'):
            assert self.video is None
            self.video = self.link_pad(pad, 'video')

    def on_have_type(self, element, prop, caps):
        self.doc['content_type'] = caps.to_string()

    def on_eos(self, bus, msg):
        if self.video is not None:
            self.doc.update(self.video._get_doc())
        if self.audio is not None:
            self.doc.update(self.audio._get_doc())
        self.kill()

    def on_error(self, bus, msg):
        error = msg.parse_error()[1]
        self.kill()
        print(error)
        sys.exit(2)

