#!/usr/bin/env python3

# novacut: the collaborative video editor
# Copyright (C) 2011-2015 Novacut Inc
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


import argparse
from os import path
import logging
import sys

from gi.repository import GLib

import novacut
from novacut.validate import (
    PlayThrough,
    PrerollTester,
    SeekTester,
    shuffle_indexes,
)


parser = argparse.ArgumentParser()
parser.add_argument('--version', action='version', version=novacut.__version__)
parser.add_argument('files', nargs='+',
    help='Path of video file(s) to deep test',
)
parser.add_argument('--debug', action='store_true', default=False,
    help='Turn on debug-level logging'
)
args = parser.parse_args()
count = len(args.files)


logging.basicConfig(
    level=(logging.DEBUG if args.debug else logging.INFO),
    format='\t'.join([
        '%(levelname)s',
        '%(threadName)s',
        '%(message)s',
    ]),
)
log = logging.getLogger()


mainloop = GLib.MainLoop()


def on_complete(inst, success):
    mainloop.quit()


def deep_test_one(filename):
    inst = PlayThrough(on_complete, filename)
    GLib.idle_add(inst.run)
    mainloop.run()
    if inst.success is not True:
        raise SystemError('critical error in PlayThrough')
    expected = tuple(inst.video)
    count = len(expected)
    indexes = shuffle_indexes(count)

    seek_times = [expected[i].pts for i in indexes]
    inst = PrerollTester(on_complete, filename, seek_times)
    GLib.idle_add(inst.run)
    mainloop.run()
    if inst.success is not True:
        raise SystemError('critical error in PrerollTester')
    got = tuple(inst.video)

    if len(got) != count:
        raise ValueError('{} != {}'.format(len(got), count))
    for i in range(count):
        info1 = expected[indexes[i]]
        info2 = got[i]
        if info1 != info2:
            raise ValueError('{}: {} != {}'.format( i, info1, info2))

    slices = [
        (expected[i].pts, expected[i].pts + expected[i].duration)
        for i in indexes
    ]
    inst = SeekTester(on_complete, filename, slices)
    GLib.idle_add(inst.run)
    mainloop.run()
    if inst.success is not True:
        raise SystemError('critical error in SliceTester')
    got = tuple(inst.video)

    if len(got) != count:
        raise ValueError('{} != {}'.format(len(got), count))
    for i in range(count):
        info1 = expected[indexes[i]]
        info2 = got[i]
        if info1 != info2:
            raise ValueError('{}: {} != {}'.format( i, info1, info2))


passed = []
failed = []
for f in args.files:
    filename = path.abspath(f)
    if not path.isfile(filename):
        log.error('Not a file: %r', filename)
        sys.exit(3)
    log.info('\n%s\n%s', filename, '=' * min(len(filename), 72))
    try:
        deep_test_one(filename)
        log.info('PASS: %r', filename)
        passed.append(filename)
    except:
        log.exception('FAIL: %r', filename)
        failed.append(filename)
assert len(passed) + len(failed) == count

print('PASSED {}/{}:'.format(len(passed), count))
for filename in passed:
    print('  {!r}'.format(filename))

if failed:
    print('FAILED {}/{}:'.format(len(failed), count))
    for filename in failed:
        print('  {!r}'.format(filename))
    print('** FAIL!')
    sys.exit(4)
else:
    print('** PASS!')

