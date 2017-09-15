

# Tao Shi tshi206

# !/usr/bin/env python

from __future__ import print_function, absolute_import, division

import logging

import os
import sys
import errno

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn
from passthrough import Passthrough
from memory import Memory
from collections import defaultdict
from errno import ENOENT
from stat import S_IFDIR, S_IFLNK, S_IFREG
from sys import argv, exit
from time import time


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


class A2Fuse2(LoggingMixIn, Passthrough, Operations):
    def __init__(self, root):
        super(A2Fuse2, self).__init__(root)
        self.root = root
        self.setup = True
        self.files = {}
        self.data = defaultdict(bytes)
        self.fd = 0
        now = time()
        self.files['/'] = dict(st_mode=(S_IFDIR | 0o755), st_ctime=now,
                               st_mtime=now, st_atime=now, st_nlink=2)

    def _full_path(self, partial):
        if partial.startswith("/"):
            partial = partial[1:]
        path = os.path.join(self.root, partial)
        return path

    def getattr(self, path, fh=None):
        if path not in self.files:
            return super(A2Fuse2, self).getattr(path, fh)
        else:
            return self.files[path]

    def readdir(self, path, fh):
        full_path = self._full_path(path)

        dirents = ['.', '..']
        if os.path.isdir(full_path):
            dirents.extend(os.listdir(full_path))
        # print([y[1:] for y in dirents])
        dirents.extend([x[1:] for x in self.files if x != '/'])
        for r in dirents:
            yield r
        # return [x[1:] for x in self.files if x != '/']

    def open(self, path, flags):
        if path not in self.files:
            return super(A2Fuse2, self).open(path, flags)
        else:
            self.fd += 1
            return self.fd

    def create(self, path, mode, fi=None):
        self.files[path] = dict(st_mode=(S_IFREG | mode), st_nlink=1,
                                st_size=0, st_ctime=time(), st_mtime=time(),
                                st_atime=time())

        self.fd += 1
        return self.fd

    def unlink(self, path):
        if path not in self.files:
            super(A2Fuse2, self).unlink(path)
        else:
            self.files.pop(path)

    def write(self, path, data, offset, fh):
        if path not in self.files:
            return super(A2Fuse2, self).write(path, data, offset, fh)
        else:
            self.data[path] = self.data[path][:offset] + data
            self.files[path]['st_size'] = len(self.data[path])
            return len(data)

    def read(self, path, size, offset, fh):
        if path not in self.files:
            return super(A2Fuse2, self).read(path, size, offset, fh)
        else:
            return self.data[path][offset:offset + size]

    def flush(self, path, fh):
        if path not in self.files:
            return os.fsync(fh)

    def release(self, path, fh):
        if path not in self.files:
            return os.close(fh)

    def fsync(self, path, fdatasync, fh):
        if path not in self.files:
            return self.flush(path, fh)

    def chmod(self, path, mode):
        if path not in self.files:
            return super(A2Fuse2, self).chmod(path, mode)
        else:
            self.files[path]['st_mode'] &= 0o770000
            self.files[path]['st_mode'] |= mode
            return 0

    def chown(self, path, uid, gid):
        if path not in self.files:
            super(A2Fuse2, self).chown(path, uid, gid)
        else:
            self.files[path]['st_uid'] = uid
            self.files[path]['st_gid'] = gid

    def getxattr(self, path, name, position=0):
        if path not in self.files:
            return super(A2Fuse2, self).getxattr(path, name, position)
        else:
            attrs = self.files[path].get('attrs', {})

            try:
                return attrs[name]
            except KeyError:
                return ''       # Should return ENOATTR

    def listxattr(self, path):
        if path not in self.files:
            return super(A2Fuse2, self).listxattr(path)
        else:
            attrs = self.files[path].get('attrs', {})
            return attrs.keys()

    def mkdir(self, path, mode):
        if path not in self.files:
            super(A2Fuse2, self).mkdir(path, mode)
        else:
            self.files[path] = dict(st_mode=(S_IFDIR | mode), st_nlink=2,
                                st_size=0, st_ctime=time(), st_mtime=time(),
                                st_atime=time())

            self.files['/']['st_nlink'] += 1

    def readlink(self, path):
        if path not in self.files:
            return super(A2Fuse2, self).readlink(path)
        else:
            return self.data[path]

    def removexattr(self, path, name):
        if path not in self.files:
            return super(A2Fuse2, self).removexattr(path, name)
        else:
            attrs = self.files[path].get('attrs', {})

            try:
                del attrs[name]
            except KeyError:
                pass        # Should return ENOATTR

    def rename(self, old, new):
        if '/'+old not in self.files:
            return super(A2Fuse2, self).rename(old, new)
        else:
            self.files[new] = self.files.pop(old)

    def rmdir(self, path):
        if path not in self.files:
            super(A2Fuse2, self).rmdir(path)
        else:
            self.files.pop(path)
            self.files['/']['st_nlink'] -= 1

    def setxattr(self, path, name, value, options, position=0):
        if path not in self.files:
            return super(A2Fuse2, self).setxattr(path, name, value, options, position)
        else:
            # Ignore options
            attrs = self.files[path].setdefault('attrs', {})
            attrs[name] = value

    def statfs(self, path):
        if path not in self.files:
            return super(A2Fuse2, self).statfs(path)
        else:
            return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)

    def symlink(self, target, source):
        if target not in self.files:
            super(A2Fuse2, self).symlink(target, source)
        else:
            self.files[target] = dict(st_mode=(S_IFLNK | 0o777), st_nlink=1,
                                  st_size=len(source))

            self.data[target] = source

    def truncate(self, path, length, fh=None):
        if path not in self.files:
            super(A2Fuse2, self).truncate(path, length)
        else:
            self.data[path] = self.data[path][:length]
            self.files[path]['st_size'] = length


    def utimens(self, path, times=None):
        if path not in self.files:
            return super(A2Fuse2, self).utimens(path)
        else:
            now = time()
            atime, mtime = times if times else (now, now)
            self.files[path]['st_atime'] = atime
            self.files[path]['st_mtime'] = mtime


def main(mountpoint, root):
    FUSE(A2Fuse2(root), mountpoint, nothreads=True, foreground=True)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main(sys.argv[2], sys.argv[1])
