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

"""
Common helper functions and classes shared among unit tests.
"""

from fractions import Fraction
from random import SystemRandom

from dbase32 import random_id

from ..render import Slice
from ..misc import random_start_stop


random = SystemRandom()


def random_framerate():
    num = random.randrange(1, 54321)
    denom = random.randrange(1, 54321)
    return Fraction(num, denom)


def random_filename():
    return '/tmp/' + random_id() + '.mov'


def random_slice():
    (start, stop) = random_start_stop()
    filename = random_filename()
    return Slice(start, stop, filename)

