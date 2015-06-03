import mongoengine
import pymongo


try:
    mongoengine.connect(db='test', read_preference=pymongo.read_preferences.ReadPreference.NEAREST,
                        replicaSet='rs0')
except mongoengine.connection.ConnectionError:
    # If the first DB is the one that gets killed, just try another one
    mongoengine.connect(db='test', host='localhost:27018',
                        read_preference=pymongo.read_preferences.ReadPreference.NEAREST,
                        replicaSet='rs0')


class TestDocument(mongoengine.Document):
    test_field = mongoengine.StringField(required=True, unique=True)
