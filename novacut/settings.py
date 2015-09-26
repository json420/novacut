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

from . import schema


def get_default_settings(width=1920, height=1080):
    return {
#        'muxer': {
#            'name': 'qtmux',
#            'props': {
#                'movie-timescale': 30000,
#                'trak-timescale': 30000, 
#            },
#        },
        'muxer': 'matroskamux',
        'ext': 'mkv',
        'video': {
            'encoder': {
                'name': 'x264enc',
                'props': {
                    'pass': 5,  # Constant Quality
                    'qp-max': 25,
                    'key-int-max': 60,
                    'b-adapt': False,
                    'rc-lookahead': 20,
                },
            },
            'caps': {
                'format': 'I420',
                'width': width,
                'height': height,
                'interlace-mode': 'progressive',
                'pixel-aspect-ratio': '1/1',
                'chroma-site': 'mpeg2',
                'colorimetry': 'bt709',
                'framerate': {
                    'num': 30000,
                    'denom': 1001,
                },
            },
        },
        'audio': {
            'encoder': {
                'name': 'vorbisenc',
                'props': {
                    'quality': 0.5,
                },
            },
        },
    }


def default_settings(width=1920, height=1080):
    node = get_default_settings(width, height)
    return schema.create_settings(node)

