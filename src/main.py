#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import trio
import pyfuse3
from loguru import logger
from pkg.ImapBox import ImapBox
from pkg.MailboxFs import MailboxFs

# Further work/limitations:
#
# - Allow multiple mailboxes
# - Store folder structure in a DB
# - When having persistent storage, fetch updates only (HIGHESTMODSEQ)
# - Sent e-mails would pollute the `sender` thus no outbox
# - A directory can only contain either just directories or just files, not both
# - Fetch only e-mail headers and not the whole message for large mailboxes, then
#       get the body upon opening of the file. It's not trivial due to file size
#       being a inode entry (direct IO is not ideal way as per fuse(8))
# - Implement lookup count handler
# - Gmail doesn't seem to have a limit for fetching emails, but other mailboxes
#   may. Fetching in batches?
# - more friendly configuration, not just envs
# - Investigate on relation between webdav, davfs, client/server inode cache and/or
#   generation to prevent webdav client to store incorrect inode of an entry.
#
# Used env variables (self explanatory):
#  - IMAP_HOST (required)
#  - IMAP_USER (required)
#  - IMAP_PASS (required)
#  - MSG_LIMIT (default=None)
#  - REFRESH_INTERVAL (default=120)
#  - LOGURU_LEVEL (optional)

# todotodo
# - sort by date asc


async def refresh_loop(box):
    while True:
        await trio.sleep(int(os.getenv('REFRESH_INTERVAL', 120)))
        box.refresh()


async def main_loop():
    box = ImapBox()
    fs  = MailboxFs(box)

    logger.info('Spinning up the FS')
    pyfuse3.init(fs, '/mnt', pyfuse3.default_options)

    async with trio.open_nursery() as nursery:
        nursery.start_soon(pyfuse3.main)
        nursery.start_soon(refresh_loop, box)


def main():
    logger.debug('Debug enabled')
    logger.trace('Trace enabled')
    logger.info('Starting Mapbox')

    try:
        trio.run(main_loop)
    except Exception as e:
        logger.exception(e)
    finally:
        pyfuse3.close(unmount=True)


main()
