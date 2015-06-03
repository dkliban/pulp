import time

import pymongo

from connection import TestDocument


t = TestDocument(test_field='test 2')

success = False
attempts = 0

while not success:
    attempts += 1
    try:
        # The fsync will override the default write concern!
        t.save(write_concern={'fsync': True})
        success = True
    except pymongo.errors.AutoReconnect:
        time.sleep(1)


print 'Successfully written in %s attempts.' % attempts
