# novacut: the collaborative video editor
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

"""
`novacut` - the collaborative video editor.
"""

__version__ = '14.06.0'
BUS = 'com.novacut.Renderer'


def configure_logging():
    import sys
    import os
    from os import path
    import logging
    import platform

    script = path.abspath(sys.argv[0])
    namespace = path.basename(script)
    format = [
        '%(levelname)s',
        '%(processName)s',
        '%(threadName)s',
        '%(message)s',
    ]
    home = path.abspath(os.environ['HOME'])
    if not path.isdir(home):
        raise Exception('$HOME is not a directory: {!r}'.format(home))
    cache = path.join(home, '.cache', 'novacut')
    if not path.exists(cache):
        os.makedirs(cache)
    filename = path.join(cache, namespace + '.log')
    if path.exists(filename):
        os.rename(filename, filename + '.previous')
    logging.basicConfig(
        filename=filename,
        filemode='w',
        level=logging.DEBUG,
        format='\t'.join(format),
    )
    log = logging.getLogger()
    log.info('======== Process Start ========')
    log.info('script: %r', script)
    log.info('__file__: %r', __file__)
    log.info('__version__: %r', __version__)
    log.info('Python: %s, %s, %s',
        platform.python_version(), platform.machine(), platform.system()
    )
    log.info('===============================')
    return log

