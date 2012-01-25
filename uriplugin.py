from filestore import FileStore, DIGEST_BYTES

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

    __gproperties__ = {
        'id': (
            GObject.TYPE_STRING,
            'id',
            'dmedia file ID',
            None,
            GObject.PARAM_READWRITE,
        ),
    }

    def __init__(self):
        super(DmediaSrc, self).__init__()
        self._id = None
        self._filesrc = Gst.ElementFactory.make('filesrc', None)
        self._fs = FileStore('/home')
        self.add(self._filesrc)
        self.add_pad(
            Gst.GhostPad.new('src', self._filesrc.get_static_pad('src'))
        )

    def do_get_property(self, name):
        return self._id

    def do_set_property(self, name, value):
        self._id = value
        if value is None:
            self._filesrc.set_property('location', None)
        else:
            self._filesrc.set_property('location', self._fs.path(value))


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
_id = 'KK4E4DKZDHQGDDIETMEFI3RFQEQYZWAJPMBOZBXM4GM4VLIO'
src.set_property('id', _id)
print(src.get_property('id'))
print(src._filesrc.get_property('location'))

