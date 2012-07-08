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
Defines the Novacut CouchDB views.
"""

import logging

from microfiber import NotFound
from dmedia.views import _count, _sum, doc_design, media_design, camera_design

log = logging.getLogger()


# For novacut/node docs:
node_type = """
function(doc) {
    if (doc.type == 'novacut/node') {
        emit(doc.node.type, null);
    }
}
"""

node_src = """
function(doc) {
    if (doc.type == 'novacut/node') {
        var src = doc.node.src;
        if (typeof src == 'string') {
            emit(src, null);
        }
        else if (src.constructor.name == 'Array') {
            var i;
            for (i in src) {
                emit(src[i], null);
            }
        }
    }
}
"""

node_design = {
    '_id': '_design/node',
    'views': {
        'type': {'map': node_type, 'reduce': _count},
        'src': {'map': node_src, 'reduce': _count},
    },
}


# For novacut/project docs:
project_atime = """
function(doc) {
    if (doc.type == 'novacut/project') {
        emit(doc.atime, doc.title);
    }
}
"""

project_title = """
function(doc) {
    if (doc.type == 'novacut/project') {
        emit(doc.title, doc.atime);
    }
}
"""

project_design = {
    '_id': '_design/project',
    'views': {
        'atime': {'map': project_atime},
        'title': {'map': project_title},
    },
}


# Design docs for main novacut-VER database
novacut_main = (
    doc_design, 
    project_design,
)


novacut_projects = (
    node_design,
    doc_design,
    media_design,
    camera_design,
)

