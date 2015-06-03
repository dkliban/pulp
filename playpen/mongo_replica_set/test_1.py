import time

import pymongo

from connection import TestDocument


t = TestDocument(test_field='test 1')

success = False
attempts = 0

while not success:
    attempts += 1
    try:
        t.save()
        success = True
    except pymongo.errors.AutoReconnect:
        time.sleep(1)


print 'Successfully written in %s attempts.' % attempts
