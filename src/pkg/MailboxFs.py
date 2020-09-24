import os
import pyfuse3
import stat
import errno
from loguru import logger
from pkg.ImapBox import ImapBox


class MailboxFs(pyfuse3.Operations):
    def __init__(self, box):
        super(MailboxFs, self).__init__()
        self.box = box
        self.box.refresh()

    async def getattr(self, inode, ctx=None):
        logger.debug('Getting attributes for {}'.format(inode))
        entry     = pyfuse3.EntryAttributes()
        timestamp = 0

        if self.box.inodes[inode].type == ImapBox.DIR_T:
            entry.st_mode = (stat.S_IFDIR | 0o755)
            entry.st_size = 0
        elif self.box.inodes[inode].type == ImapBox.FILE_T:
            timestamp     = self.box.inodes[inode].data.timestamp * 1e9
            entry.st_mode = (stat.S_IFREG | 0o644)
            entry.st_size = len(self.box.inodes[inode].data.contents)
        else:
            raise pyfuse3.FUSEError(errno.ENOENT)

        entry.st_atime_ns = timestamp
        entry.st_ctime_ns = timestamp
        entry.st_mtime_ns = timestamp
        entry.st_gid      = os.getgid()
        entry.st_uid      = os.getuid()
        entry.st_ino      = inode

        return entry

    async def lookup(self, parent_inode, name, ctx=None):
        logger.trace('Lookup for {} in {}'.format(name, parent_inode))

        if not self.box.inodes[parent_inode] or not self.box.inodes[parent_inode].children:
            raise pyfuse3.FUSEError(errno.ENOENT)

        for c_inode in self.box.inodes[parent_inode].children:
            if self.box.inodes[c_inode].name == name:
                logger.debug('Lookup found {} (inode {}) in {}'.format(name, c_inode, parent_inode))
                return await self.getattr(c_inode, ctx)

        raise pyfuse3.FUSEError(errno.ENOENT)

    async def opendir(self, inode, ctx):
        logger.trace('Opendir for {}'.format(inode))
        if not self.box.inodes[inode]:
            raise pyfuse3.FUSEError(errno.ENOENT)

        if self.box.inodes[inode].type != ImapBox.DIR_T:
            raise pyfuse3.FUSEError(errno.ENOENT)

        logger.debug('Opened directory {}'.format(str(self.box.inodes[inode].name)))

        return inode

    async def readdir(self, parent, off, token):
        idx = 0

        for child_inode in self.box.inodes[parent].children[off:]:
            idx = idx + 1
            node = self.box.inodes[child_inode]
            pyfuse3.readdir_reply(
                token, node.name, await self.getattr(node.inode), off + idx)
        return

    async def open(self, inode, flags, ctx):
        logger.trace('Opening file {}'.format(inode))
        if not self.box.inodes[inode]:
            raise pyfuse3.FUSEError(errno.ENOENT)

        if flags & os.O_RDWR or flags & os.O_WRONLY:
            raise pyfuse3.FUSEError(errno.EPERM)

        logger.debug('Opened file {}'.format(str(self.box.inodes[inode].name)))

        return pyfuse3.FileInfo(fh=inode)

    async def read(self, inode, off, size):
        logger.trace('Reading file {}'.format(inode))
        if not self.box.inodes[inode]:
            raise pyfuse3.FUSEError(errno.ENOENT)

        logger.debug('Read file {}'.format(str(self.box.inodes[inode].name)))

        return self.box.inodes[inode].data.contents[0:size]
