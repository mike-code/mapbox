## mapbox

### Further work/limitations:

* Allow multiple mailboxes
* Store folder structure in a DB
* When having persistent storage, fetch updates only (HIGHESTMODSEQ)
* Sent e-mails would pollute the `sender` thus no outbox
* A directory can only contain either just directories or just files, not both
* Fetch only e-mail headers and not the whole message for large mailboxes, thenget the body upon opening of the file. It's not trivial due to file sizebeing a inode entry (direct IO is not ideal way as per fuse(8))
* Implement lookup count handler
* Gmail doesn't seem to have a limit for fetching emails, but other mailboxesmay. Fetching in batches?
* more friendly configuration, not just envs
* Investigate on relation between webdav, davfs, client/server inode cache and/or generation to prevent webdav client to store incorrect inode of an entry.
* don't just supervisor in docker, just don't

### Used env variables (self explanatory):
* IMAP_HOST (required)
*  IMAP_USER (required)
*  IMAP_PASS (required)
*  MSG_LIMIT (default=None)
*  REFRESH_INTERVAL (default=120)
*  LOGURU_LEVEL (optional)
