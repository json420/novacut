#!/usr/bin/python

import gobject
gobject.threads_init()

import gst

mainloop = gobject.MainLoop()
pipeline = gst.Pipeline()

def on_eos(bus, msg):
    print('eos: {!r}'.format(msg))
    pipeline.set_state(gst.STATE_NULL)
    mainloop.quit()

def on_message(bus, msg):
    print('message: {!r}'.format(msg))

bus = pipeline.get_bus()
bus.add_signal_watch()
bus.connect('message::eos', on_eos)
bus.connect('message', on_message)

src = gst.element_factory_make('videotestsrc')
src.set_property('num-buffers', 10)
sink = gst.element_factory_make('fakesink')
pipeline.add(src)
pipeline.add(sink)
src.link(sink)

pipeline.set_state(gst.STATE_PLAYING)
mainloop.run()
