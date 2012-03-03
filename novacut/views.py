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


# Design docs for main novacut-VER database
novacut_main = (
    doc_design, 

    ('project', (
        ('atime', project_atime, None),
        ('title', project_title, None),
    )),
)


novacut_projects = (
    doc_design,
    media_design,
    camera_design,

    ('node', (
        ('type', node_type, _count),
        ('src', node_src, _count),
    )),
)


def iter_views(views):
    for (name, map_, reduce_) in views:
        if reduce_ is None:
            yield (name, {'map': map_.strip()})
        else:
            yield (name, {'map': map_.strip(), 'reduce': reduce_.strip()})


def build_design_doc(design, views):
    doc = {
        '_id': '_design/' + design,
        'language': 'javascript',
        'views': dict(iter_views(views)),
    }
    return doc


def update_design_doc(db, doc):
    assert '_rev' not in doc
    try:
        old = db.get(doc['_id'])
        doc['_rev'] = old['_rev']
        if doc != old:
            db.save(doc)
            return 'changed'
        else:
            return 'same'
    except NotFound:
        db.save(doc)
        return 'new'


def init_views(db, designs):
    log.info('Initializing views in %r', db)
    for (name, views) in designs:
        doc = build_design_doc(name, views)
        update_design_doc(db, doc)
