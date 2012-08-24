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
Unit tests for the `novacut.migration` module.
"""

import json
from fractions import Fraction

from usercouch.misc import CouchTestCase
from microfiber import Database

from novacut.timefuncs import frame_to_sample
from novacut import schema, migration


docs_s = """
[
    {
        "_id": "WPKFHBKX2LTHAIAILWAK7PEG",
        "doodle": [
            {
                "id": "shortcuts",
                "x": null,
                "y": null
            },
            {
                "id": "ZZOAZZCEJIZV36SDRNGLNP3J",
                "x": 1302,
                "y": 408
            },
            {
                "id": "N4ZQGJFX24SQH6OY6JDHXCT2",
                "x": 195,
                "y": 230
            }
        ],
        "node": {
            "src": [
                "JDQPJVFJOEPYR64FRTEULTBB",
                "GMWUVRRSBZFSD7PD6IKSQXLU",
                "7ENE3E3H2XWAETPU4E2SGMQY",
                "ZCVOKON745KTKOZTI5JKRMNP",
                "H3BN43ZC4OUI42R7K4BSQ67Q",
                "ZITFANVLNT36I4PQ54B7XTGI",
                "B56KMP2HVW4GHAXKFDYQQ5UD",
                "7BR63KHALAAFZNZJPWMUJ77X",
                "HYHA764RM4BDVBYPA7SQG4LW",
                "6VTAXG6PHUVR7NBLIBT63JCN",
                "VJF2TXN4IDEL4FHYWBTOMYPB"
            ],
            "type": "sequence"
        },
        "selected": "N4ZQGJFX24SQH6OY6JDHXCT2",
        "session_id": "1345419541-SGIO4XPFNZ4KGXK4",
        "time": 1342803135.184,
        "type": "novacut/node",
        "ver": 0
    },
    {
        "_id": "JDQPJVFJOEPYR64FRTEULTBB",
        "node": {
            "src": "F6KHESGKSVXCRXH7FEJHLJRP44QRORF7GEMIJM4YPBDSMAMF",
            "start": {
                "frame": 127
            },
            "stop": {
                "frame": 205
            },
            "stream": "both",
            "type": "slice"
        },
        "session_id": "1345340199-RXJX3JGYQP4TFLNX",
        "time": 1343379567.943,
        "type": "novacut/node",
        "ver": 0
    },
    {
        "_id": "GMWUVRRSBZFSD7PD6IKSQXLU",
        "node": {
            "src": "NYJOQ4KHVZ3SM5SODHWFAUZ5GIJXNPDLHKASMAO2K6Y4V2LT",
            "start": {
                "frame": 238
            },
            "stop": {
                "frame": 557
            },
            "stream": "both",
            "type": "slice"
        },
        "session_id": "1345201341-QNG7X3IZHXX2UH5K",
        "time": 1343379504.205,
        "type": "novacut/node",
        "ver": 0
    },
    {
        "_id": "NYJOQ4KHVZ3SM5SODHWFAUZ5GIJXNPDLHKASMAO2K6Y4V2LT",
        "bytes": 196010853,
        "channels": 2,
        "content_type": "video/quicktime",
        "ctime": 1343161881.37,
        "duration": {
            "frames": 848,
            "nanoseconds": 33920000000,
            "samples": 1628160,
            "seconds": 33.92
        },
        "ext": "mov",
        "framerate": {
            "denom": 1,
            "num": 25
        },
        "height": 1088,
        "import": {
            "batch_id": "G43C4TNHZTQID2GYXQ7AJWKY",
            "import_id": "AQ3UCVFNDX3MD7KD7HPTBSGC",
            "machine_id": "PIZ6WYOE72XOHEXMHLMXIMEW",
            "mtime": 1343183514,
            "project_id": "PQUS2SCGWLKXE23WXF2CXVRJ",
            "src": "/run/media/jderose/EOS_DIGITAL/DCIM/100EOS5D/MVI_9316.MOV"
        },
        "media": "video",
        "meta": {
            "aperture": 3.5,
            "camera": "Canon EOS 5D Mark II",
            "camera_serial": "0820500998",
            "canon_thm": "HUDPYMFK4YMB2LDKGMBEKLAENFMNMRUSBLBINOUEGH6XCUPQ",
            "focal_length": "50.0 mm",
            "iso": 1600,
            "lens": "Canon EF 50mm f/1.2L",
            "shutter": "1/60"
        },
        "name": "MVI_9316.MOV",
        "origin": "user",
        "samplerate": 48000,
        "session_id": "1343379450-N2F6ZXTLZM46ASCJ",
        "tags": {},
        "time": 1343191600.457724,
        "type": "dmedia/file",
        "ver": 0,
        "width": 1920
    },
    {
        "_id": "F6KHESGKSVXCRXH7FEJHLJRP44QRORF7GEMIJM4YPBDSMAMF",
        "bytes": 122207749,
        "channels": 2,
        "content_type": "video/quicktime",
        "ctime": 1343163072.67,
        "duration": {
            "frames": 536,
            "nanoseconds": 21440000000,
            "samples": 1029120,
            "seconds": 21.44
        },
        "ext": "mov",
        "framerate": {
            "denom": 1,
            "num": 25
        },
        "height": 1088,
        "import": {
            "batch_id": "G43C4TNHZTQID2GYXQ7AJWKY",
            "import_id": "AQ3UCVFNDX3MD7KD7HPTBSGC",
            "machine_id": "PIZ6WYOE72XOHEXMHLMXIMEW",
            "mtime": 1343184694,
            "project_id": "PQUS2SCGWLKXE23WXF2CXVRJ",
            "src": "/run/media/jderose/EOS_DIGITAL/DCIM/100EOS5D/MVI_9320.MOV"
        },
        "media": "video",
        "meta": {
            "aperture": 3.5,
            "camera": "Canon EOS 5D Mark II",
            "camera_serial": "0820500998",
            "canon_thm": "7NB57GH3GDSEPIGI7RTRFTZ2QYU2GZMTMECUEMFO4XLRWEVH",
            "focal_length": "100.0 mm",
            "iso": 1600,
            "lens": "Canon EF 100mm f/2.8L Macro IS USM",
            "shutter": "1/60"
        },
        "name": "MVI_9320.MOV",
        "origin": "user",
        "samplerate": 48000,
        "session_id": "1343379450-N2F6ZXTLZM46ASCJ",
        "tags": {},
        "time": 1343191736.768652,
        "type": "dmedia/file",
        "ver": 0,
        "width": 1920
    }
]
"""


class TestFunctions(CouchTestCase):
    def test_migrate_slice(self):
        db = Database('foo', self.env)
        self.assertTrue(db.ensure())
        docs = json.loads(docs_s)
        db.save_many(docs)

        # Test when stream=both
        doc = db.get('JDQPJVFJOEPYR64FRTEULTBB')
        new = list(migration.migrate_slice(db, doc))
        self.assertEqual(len(new), 2)
        (audio, video) = new

        self.assertEqual(set(audio), set(['_id', 'type', 'time', 'node']))
        self.assertEqual(audio['node']['type'], 'audio/slice')
        self.assertEqual(audio['node']['src'], video['node']['src'])
        self.assertEqual(audio['node']['start'],
            frame_to_sample(127, Fraction(25, 1), 48000)
        )
        self.assertEqual(audio['node']['stop'],
            frame_to_sample(205, Fraction(25, 1), 48000)
        )
        self.assertEqual(audio['node']['start'], 243840)
        self.assertEqual(audio['node']['stop'], 393600)
        self.assertNotIn('_rev', audio)
        schema.check_audio_slice(audio)

        self.assertEqual(video,
            {
                '_id': 'JDQPJVFJOEPYR64FRTEULTBB',
                '_rev': '1-b109ac525743bbdee75fc03476ea7737',
                'type': 'novacut/node',
                'time': 1343379567.943,
                'node': {
                    'src': 'F6KHESGKSVXCRXH7FEJHLJRP44QRORF7GEMIJM4YPBDSMAMF',
                    'start': 127,
                    'stop': 205,
                    'type': 'video/slice',
                },
                'audio': [
                    {'offset': 0, 'id': audio['_id']},
                ],

            },
        )
        schema.check_video_slice(video)

        # Test when stream=video
        doc = db.get('JDQPJVFJOEPYR64FRTEULTBB')
        doc['node']['stream'] = 'video'
        new = list(migration.migrate_slice(db, doc))
        self.assertEqual(len(new), 1)

        video = new[0]
        self.assertEqual(video,
            {
                '_id': 'JDQPJVFJOEPYR64FRTEULTBB',
                '_rev': '1-b109ac525743bbdee75fc03476ea7737',
                'type': 'novacut/node',
                'time': 1343379567.943,
                'node': {
                    'src': 'F6KHESGKSVXCRXH7FEJHLJRP44QRORF7GEMIJM4YPBDSMAMF',
                    'start': 127,
                    'stop': 205,
                    'type': 'video/slice',
                },
                'audio': [],
            },
        )
        schema.check_video_slice(video)

    def test_migrate_sequence(self):
        db = Database('foo', self.env)
        self.assertTrue(db.ensure())
        docs = json.loads(docs_s)
        db.save_many(docs)

        doc = db.get('WPKFHBKX2LTHAIAILWAK7PEG')
        new_docs = list(migration.migrate_sequence(db, doc))
        self.assertEqual(len(new_docs), 1)
        new = new_docs[0]
        self.assertEqual(new,
            {
                '_id': 'WPKFHBKX2LTHAIAILWAK7PEG',
                '_rev': '1-0449c9f5e1bbc672477f6180490a0c54',
                'type': 'novacut/node',
                'time': 1342803135.184,
                'node': {
                    'type': 'video/sequence',
                    'src': [
                        'JDQPJVFJOEPYR64FRTEULTBB',
                        'GMWUVRRSBZFSD7PD6IKSQXLU',
                        '7ENE3E3H2XWAETPU4E2SGMQY',
                        'ZCVOKON745KTKOZTI5JKRMNP',
                        'H3BN43ZC4OUI42R7K4BSQ67Q',
                        'ZITFANVLNT36I4PQ54B7XTGI',
                        'B56KMP2HVW4GHAXKFDYQQ5UD',
                        '7BR63KHALAAFZNZJPWMUJ77X',
                        'HYHA764RM4BDVBYPA7SQG4LW',
                        '6VTAXG6PHUVR7NBLIBT63JCN',
                        'VJF2TXN4IDEL4FHYWBTOMYPB',
                    ],
                },
                'selected': 'N4ZQGJFX24SQH6OY6JDHXCT2',
                'audio': [],
                'doodle': [
                    {
                        'id': 'shortcuts',
                        'x': None,
                        'y': None
                    },
                    {
                        'id': 'ZZOAZZCEJIZV36SDRNGLNP3J',
                        'x': 1302,
                        'y': 408
                    },
                    {
                        'id': 'N4ZQGJFX24SQH6OY6JDHXCT2',
                        'x': 195,
                        'y': 230
                    }
                ],
            }
        )
        schema.check_video_sequence(new)

    def test_migrate_db(self):
        db = Database('foo', self.env)
        self.assertTrue(db.ensure())
        docs = json.loads(docs_s)
        db.save_many(docs)

        new_docs = list(migration.migrate_db(db))
        self.assertEqual(len(new_docs), 5)
        counts = {}
        for doc in new_docs:
            self.assertEqual(doc['type'], 'novacut/node')
            self.assertNotIn('ver', doc)
            self.assertNotIn('session_id', doc)
            node = doc['node']
            self.assertIn(node['type'],
                ['video/sequence', 'video/slice', 'audio/slice']
            )
            counts[node['type']] = counts.get(node['type'], 0) + 1
            if node['type'] == 'video/sequence':
                self.assertEqual(doc['audio'], [])
                schema.check_video_sequence(doc)
            elif node['type'] == 'video/slice':
                self.assertIsInstance(doc['audio'], list)
                self.assertEqual(len(doc['audio']), 1)
                schema.check_video_slice(doc)
            else:
                schema.check_audio_slice(doc)
        self.assertEqual(counts,
            {
                'video/sequence': 1,
                'video/slice': 2,
                'audio/slice': 2,
            }
        )
