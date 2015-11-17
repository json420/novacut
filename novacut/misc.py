# novacut: the distributed video editor
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
Misc functions, currently just for generating random edits.
"""

from random import SystemRandom
from collections import namedtuple


random = SystemRandom()
StartStop = namedtuple('StartStop', 'start stop')


def random_start_stop(count=123456):
    """
    Generate a random ``(start, stop)`` within media that is *count* units long.

    For example, there is only one possible slice in a one-frame-long video:

    >>> random_start_stop(1)
    StartStop(start=0, stop=1)

    This function returns a ``(start,stop)`` tuple such that::

        0 <= start < stop <= count
    """
    assert count >= 1
    start = random.randrange(0, count)
    stop = random.randrange(start + 1, count + 1)
    return StartStop(start, stop)

