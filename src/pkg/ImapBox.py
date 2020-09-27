import os
import pyfuse3
import typing

from loguru import logger
from itertools import groupby
from imap_tools import MailBox
from email.header import decode_header
from slugify import slugify
from imap_tools.message import MailMessage
from imap_tools.utils import decode_value
from pkg.structs import inode_t
from pkg.structs import mailmeta


class ImapBox:
    DIR_T  = 1
    FILE_T = 2

    @property
    def inodes(self) -> typing.Dict:
        return self._inodes

    def __init__(self):
        self._the_map = {}
        self._inodes  = {}

    def refresh(self):
        logger.info('Refreshing email data')
        imap_emails    = self._fetch_emails()
        parsed_headers = self._parse_headers(imap_emails)

        self.rebuild_object_map(parsed_headers)
        self.generate_inodes()

    def _parse_headers(self, emails) -> typing.List[mailmeta]:
        logger.debug('Parsing emails headers')
        box_data = []

        for mail in emails:
            if 'subject' not in mail.obj:
                logger.warning('Missing subject header for UID: ' + mail.uid)
                continue

            mail_subject      = ''.join(decode_value(*part) for part in decode_header(mail.obj['subject']))
            mail_subject_slug = slugify(mail_subject)

            if not mail_subject_slug:
                mail_subject_slug = '__no-subject__'

            headers = "\r\n".join([h + ": " + ''.join(str(i) for i in mail.headers[h]) for h in mail.headers])
            bodytxt = headers + "\r\n\r\n" + (mail.html if mail.text == '' else mail.text)

            box_data.append(
                mailmeta(
                    uid=mail.uid,
                    sender=mail.from_,
                    subject_slug=mail_subject_slug,
                    year=mail.date.year,
                    month=mail.date.month,
                    day=mail.date.day,
                    timestamp=int(mail.date.timestamp()),
                    contents=bytes(bodytxt, 'utf-8', errors='replace'),
                )
            )

        return box_data

    def rebuild_object_map(self, data):
        self._the_map = {
            'emails': {},
            'dates' : {},
            'uids'  : {}
        }

        logger.debug('Rebuilding the object map')

        for meta in data:
            if meta.sender not in self._the_map['emails']:
                self._the_map['emails'][meta.sender] = []

            if meta.year not in self._the_map['dates']:
                self._the_map['dates'][meta.year] = {}

            if meta.month not in self._the_map['dates'][meta.year]:
                self._the_map['dates'][meta.year][meta.month] = {}

            if meta.day not in self._the_map['dates'][meta.year][meta.month]:
                self._the_map['dates'][meta.year][meta.month][meta.day] = []

            self._the_map['uids'][meta.uid] = meta
            self._the_map['emails'][meta.sender].append(meta.uid)
            self._the_map['dates'][meta.year][meta.month][meta.day].append(meta.uid)

    def _group_duplicates(self, uids) -> typing.List[typing.Tuple[str, str]]:
        metas = [self._the_map['uids'][uid] for uid in uids]
        metas = sorted(metas, key=lambda m: m.timestamp, reverse=False)
        files = [(meta.sender + "-" + meta.subject_slug, meta.uid) for meta in metas]

        # Can't figure out how to write it clearly in python so that it doesn't
        # look like rubbish (in a reasonable amount of time :-))
        #
        # counterpart in rb:
        #
        #   files.group_by(&:first).map{ |_,v|
        #       v.size > 1 ? v.map.with_index{ |el, i| ["#{el.first}-#{i}", el.last } : v
        #   }.flatten 1

        parsedfiles = [
            item
            for sub in [t[1] if t[0] == 1 else [(v[0] + "-" + str(idx), v[1]) for idx, v in enumerate(t[1])]
                        for _, groups in groupby(files, lambda n: n[0])
                        for x in [list(groups)]
                        for t in [(len(x), x)]]
            for item in sub
        ]

        return parsedfiles

    def _append_files(self, inodes, pos, uids) -> (typing.List[int], int):
        file_inodes = []

        for file in self._group_duplicates(uids):
            [name, uid] = file
            pos += 1
            inodes[pos] = inode_t(
                inode=pos,
                name=bytes(name, 'ascii'),
                type=self.FILE_T,
                data=self._the_map['uids'][uid],
            )
            file_inodes.append(pos)
            logger.trace('Created file {} under inode {}'.format(name, pos))

        return (file_inodes, pos)

    def _append_directories(self, inodes, pos, items) -> (typing.List[int], int):
        added = []

        for item in items:
            if isinstance(items[item], dict):
                [children, pos] = self._append_directories(inodes, pos, items[item])
            elif isinstance(items[item], list):
                [children, pos] = self._append_files(inodes, pos, items[item])
            else:
                continue

            pos += 1
            inodes[pos] = inode_t(
                inode=pos,
                name=bytes(str(item), 'ascii'),
                type=self.DIR_T,
                children=children,
            )
            added.append(pos)
            logger.trace('Created directory {} under inode {}'.format(str(item), pos))

        return (added, pos)

    def generate_inodes(self):
        inodes   = {}
        root_map = {'sender': self._the_map['emails'], 'timeline': self._the_map['dates']}

        logger.debug('Generating inodes')

        [children, _] = self._append_directories(inodes, pyfuse3.ROOT_INODE, root_map)

        inodes[pyfuse3.ROOT_INODE] = inode_t(
            inode=pyfuse3.ROOT_INODE,
            name=b'',
            type=self.DIR_T,
            children=children,
        )

        self._inodes = inodes

    def _fetch_emails(self) -> typing.List[MailMessage]:
        logger.debug('Fetching emails')

        msg_limit = os.getenv('MSG_LIMIT', None)

        with MailBox(os.getenv('IMAP_HOST')).login(os.getenv('IMAP_USER'), os.getenv('IMAP_PASS')) as mailbox:
            res = mailbox.fetch(
                headers_only=False,
                mark_seen=False,
                limit=int(msg_limit) if msg_limit else None,
                bulk=True,
            )

            return [msg for msg in res]
