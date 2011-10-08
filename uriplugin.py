from gi.repository import GObject, Gst

GObject.threads_init()
Gst.init(None)


class DmediaSrc(Gst.Bin):
    __gstdetails__ = (
        'Dmedia File Source',
        'Source/File',
        'Resolves a dmedia ID to a file path, then acts like a filesrc',
        'Jason Gerard DeRose <jderose@novacut.com>',
    )

    __gsttemplates__ = (
        Gst.PadTemplate.new(
            'src',
            Gst.PadDirection.SRC,
            Gst.PadPresence.ALWAYS,
            Gst.caps_from_string('ANY')
        ),
    )

    def __init__(self):
        super(DmediaSrc, self).__init__()
        self._filesrc = Gst.ElementFactory.make('filesrc', None)
        self.add(self._filesrc)
        self.add_pad(
            Gst.GhostPad.new('src', self._filesrc.get_pad('src'))
        )

 
def plugin_init(plugin, userarg):
    DmediaSrcType = GObject.type_register(DmediaSrc)
    return Gst.Element.register(plugin, 'dmediasrc', 0, DmediaSrcType)


version = Gst.version()
Gst.Plugin.register_static_full(
    version[0],  # GST_VERSION_MAJOR
    version[1],  # GST_VERSION_MINOR
    'dmedia',
    'dmedia src plugin',
    plugin_init,
    '11.10',
    'LGPL',
    'dmedia',
    'dmedia',
    'https://launchpad.net/novacut',
    None,
)

src = Gst.ElementFactory.make('dmediasrc', None)
print(src)

