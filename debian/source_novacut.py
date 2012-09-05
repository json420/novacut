'''apport package hook for novacut.

(c) 2012 Novacut Inc
Author: Jason Gerard DeRose <jderose@novacut.com>
'''

import os
from os import path

from apport.hookutils import attach_file_if_exists

LOGS = (
    ('ServiceLog', 'novacut-service.log'),
    ('GtkLog', 'novacut-gtk.log'),
    ('RendererLog', 'novacut-renderer.log'),
)

def add_info(report):
    report['CrashDB'] = 'novacut'
    cache = path.join(os.environ['HOME'], '.cache', 'novacut')
    for (key, name) in LOGS:
        log = path.join(cache, name)
        attach_file_if_exists(report, log, key)

