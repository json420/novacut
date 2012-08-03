# novacut: the collaborative video editor
# Copyright (C) 2012 Novacut Inc
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
Opinionated video and audio encoder settings.
"""

from copy import deepcopy

from . import schema


vp8enc = {
    'name': 'vp8enc',
    'props': {
        'quality': 9,
        'tune': 1,  # Tune for SSIM
        'threads': 2,
    },
}


x264enc = {
    'name': 'x264enc',
    'props': {
        'pass': 5,  # Quality-based encoding
        'quantizer': 15,  # Lower means higher-quality, default=21
        'psy-tune': 5,  # Tune for SSIM
    },
}


avenc_aac = {
    'name': 'avenc_aac',
    'props': {
        'bitrate': 256000,
    },
}


vorbisenc = {
    'name': 'vorbisenc',
    'props': {
        'quality': 0.5,
    },
}


webm = {
    'muxer': 'webmmux',
    'ext': 'webm',
    'video': {
        'encoder': vp8enc,
    },
    'audio': {
        'encoder': vorbisenc,
    },
}


def default_settings():
    node = {
        'muxer': 'matroskamux',
        'ext': 'mkv',
        'video': {
            'encoder': x264enc,
#            'caps': {
#                'width': 1280,
#                'height': 720,
#            }
        },
        'audio': {
            'encoder': vorbisenc,
        },
    }
    return schema.create_settings(node)

