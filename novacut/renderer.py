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


def build_slice(doc):
    element = gst.element_factory_make('gnlfilesource')
    numerator = doc['framerate']['numerator']
    denominator = doc['framerate']['denominator']
    start = doc['node']['start']['frame'] * gst.SECOND * denominator / numerator
    stop = doc['node']['stop']['frame'] * gst.SECOND * denominator / numerator
    duration = stop - start
    element.set_property('media-start', start)
    element.set_property('media-duration', duration)
    element.set_property('duration', duration)
    return element
