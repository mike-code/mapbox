from dataclasses import dataclass


@dataclass
class mailmeta:
    uid: int
    sender: str
    subject_slug: str
    year: int
    month: int
    day: int
    contents: bytes
    timestamp: int


@dataclass
class inode_t:
    inode: int
    name: bytes
    type: str
    children: list = None  # dirs only
    data: mailmeta = None  # files only
