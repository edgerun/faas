import readerwriterlock.rwlock


class ReadWriteLock:
    """ A lock object that allows many simultaneous "read locks", but
    only one "write lock." """

    def __init__(self):
        self.lock = readerwriterlock.rwlock.RWLockRead()
