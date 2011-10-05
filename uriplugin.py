import gobject
import gst


class DmediaSrc(gst.Bin):
    __gstdetails__ = (
        'Dmedia File Source',
        'Source/File',
        'Resolves a dmedia ID to a file path, then acts like a filesrc',
        'Jason Gerard DeRose <jderose@novacut.com>',
    )

    __gsttemplates__ = (
        gst.PadTemplate('src', gst.PAD_SRC, gst.PAD_ALWAYS, gst.Caps('ANY')),
    )

    def __init__(self):
        super(DmediaSrc, self).__init__()
        self._filesrc = gst.element_factory_make('filesrc')
        self.add(self._filesrc)
        self.add_pad(
            gst.GhostPad('src', self._filesrc.get_pad('src'))
        )


gobject.type_register(DmediaSrc)
gst.element_register(DmediaSrc, 'dmediasrc')

src = gst.element_factory_make('dmediasrc')

