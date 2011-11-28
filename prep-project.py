from filestore import _start_thread
from gi.repository import GObject

from novacut.download import Downloader, init_project

GObject.threads_init()


mainloop = GObject.MainLoop()

def done(success):
    print('done', success)
    mainloop.quit()


def download():
    try:
        d = Downloader()
        d.run()
        init_project()
        success = True
    except Exception:
        success = False
    GObject.idle_add(done, success)


_start_thread(download)

mainloop.run()
