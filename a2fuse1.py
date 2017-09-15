# !/usr/bin/env python

from __future__ import print_function, absolute_import, division

import logging

import os
import sys
import errno

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn
from passthrough import Passthrough


# class LoggingMixIn:
#     log = logging.getLogger("A2")
#
#     def __call__(self, op, path, *args):
#         self.log.debug('-> path:%s %s %s', path, op, repr(args))
#         ret = '[Unhandled Exception]'
#         try:
#             ret = getattr(self, op)(path, *args)
#             return ret
#         except OSError as e:
#             ret = str(e)
#             raise
#         finally:
#             self.log.debug('<- %s %s', op, repr(ret))


class A2Fuse1(LoggingMixIn, Passthrough):
    pass


def main(mountpoint, root):
    FUSE(A2Fuse1(root), mountpoint, nothreads=True, foreground=True)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main(sys.argv[2], sys.argv[1])
