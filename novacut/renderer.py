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

"""
Build GnonLin composition from Novacut edit description.
"""

import gst


def build_slice(doc, builder):
    element = gst.element_factory_make('gnlfilesource')
    num = doc['framerate']['num']
    denom = doc['framerate']['denom']
    start = doc['node']['start']['frame'] * gst.SECOND * denom / num
    stop = doc['node']['stop']['frame'] * gst.SECOND * denom / num
    duration = stop - start
    element.set_property('media-start', start)
    element.set_property('media-duration', duration)
    element.set_property('duration', duration)
    return element


def build_sequence(doc, builder):
    element = gst.element_factory_make('gnlcomposition')
    start = 0
    for src in doc['node']['src']:
        child = builder.build(src)
        element.add(child)
        child.set_property('start', start)
        start += child.get_property('duration')
    element.set_property('duration', start)
    return element


_builders = {
    'slice': build_slice,
    'sequence': build_sequence,
}


class Builder(object):
    def build(self, _id):
        doc = self.get_doc(_id)
        func = _builders[doc['node']['type']]
        return func(doc, self)

    def resolve_file(self, _id):
        pass

    def get_doc(self, _id):
        pass
