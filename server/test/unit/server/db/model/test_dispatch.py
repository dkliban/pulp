# -*- coding: utf-8 -*-
#
# Copyright ©2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
"""
Tests for the pulp.server.db.model.dispatch module.
"""
from datetime import datetime, timedelta
import pickle
import time
import unittest

import bson
import celery
from celery.schedules import schedule as CelerySchedule
import mock

from pulp.common import dateutils
from pulp.server.db.model.auth import User
from pulp.server.db.model.dispatch import TaskStatus, ScheduledCall, ScheduleEntry
from pulp.server.managers.factory import initialize


initialize()


class TestTaskStatus(unittest.TestCase):
    """
    Test the TaskStatus class.
    """
    def test___init__(self):
        """
        Test the __init__() method.
        """
        task_id = 'a_task_id'
        queue = 'some_queue'
        tags = ['tag_1', 'tag_2']
        state = 'a state'

        ts = TaskStatus(task_id, state, queue=queue, tags=tags)

        self.assertEqual(ts.task_id, task_id)
        self.assertEqual(ts.queue, queue)
        self.assertEqual(ts.tags, tags)
        self.assertEqual(ts.state, state)
        self.assertEqual(ts.result, None)
        self.assertEqual(ts.traceback, None)
        self.assertEqual(ts.start_time, None)
        self.assertEqual(ts.finish_time, None)
        self.assertEqual(ts.progress_report, {})
        self.assertEqual(ts.spawned_tasks, [])

    def test___init___defaults(self):
        """
        Test the __init__() method with default values
        """
        task_id = 'a_task_id'
        queue = 'some_queue'
        state = 'waiting'

        ts = TaskStatus(task_id, state)

        self.assertEqual(ts.task_id, task_id)
        self.assertEqual(ts.state, state)
        self.assertEqual(ts.queue, None)
        self.assertEqual(ts.tags, [])
        self.assertEqual(ts.result, None)
        self.assertEqual(ts.traceback, None)
        self.assertEqual(ts.start_time, None)
        self.assertEqual(ts.finish_time, None)
        self.assertEqual(ts.progress_report, {})
        self.assertEqual(ts.spawned_tasks, [])


class TestScheduledCallInit(unittest.TestCase):
    def test_new(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething')

        # make sure the call generates its own object ID
        self.assertTrue(len(call.id) > 0)
        self.assertTrue(isinstance(call._id, bson.ObjectId))

    def test_pass_in_task_name(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething')

        self.assertEqual(call.task, 'pulp.tasks.dosomething')

    def test_set_task_name(self):
        task = mock.MagicMock()
        task.name = 'pulp.tasks.dosomething'

        call = ScheduledCall('PT1M', task)

        # make sure it saves the task's name
        self.assertEqual(call.task, task.name)

    def test_pass_in_schedule(self):
        schedule = pickle.dumps(CelerySchedule(60))

        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething', schedule=schedule)

        self.assertEqual(call.schedule, schedule)

    def test_create_schedule(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething')

        schedule = pickle.loads(call.schedule)

        self.assertTrue(isinstance(schedule, CelerySchedule))
        self.assertEqual(schedule.run_every, timedelta(minutes=1))

    def test_pass_in_principal(self):
        principal = User('me', 'letmein')
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething', principal=principal)

        self.assertEqual(call.principal, principal)

    def test_create_principal(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething')

        # See PrincipalManager.get_principal(). It returns either a User or
        # a dict. Not my idea.
        self.assertTrue(isinstance(call.principal, (User, dict)))

    def test_no_first_run(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething')

        first_run = dateutils.parse_iso8601_datetime(call.first_run)

        # generously make sure the calculated first_run is within 1 second of now
        now = datetime.utcnow().replace(tzinfo=dateutils.utc_tz())
        self.assertTrue(abs(now - first_run) < timedelta(seconds=1))

    def test_first_run_datetime(self):
        first_run = datetime.utcnow().replace(tzinfo=dateutils.utc_tz()) + timedelta(days=1)

        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething', first_run=first_run)

        # make sure it is an ISO8601 string with the correct value
        self.assertTrue(isinstance(call.first_run, basestring))
        self.assertEqual(dateutils.format_iso8601_datetime(first_run), call.first_run)

    def test_first_run_string(self):
        first_run = dateutils.format_iso8601_datetime(
            datetime.utcnow().replace(tzinfo=dateutils.utc_tz()) + timedelta(days=1))

        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething', first_run=first_run)

        self.assertEqual(first_run, call.first_run)

    def test_remaining_runs_none(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething')

        self.assertTrue(call.remaining_runs is None)

    def test_remaining_runs_in_string(self):
        call = ScheduledCall('R3/PT1M', 'pulp.tasks.dosomething')

        self.assertEqual(call.remaining_runs, 3)

    def test_remaining_runs_passed_int(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething', remaining_runs=2)

        self.assertEqual(call.remaining_runs, 2)

    def test_next_run_ignored(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething', next_run='foo')

        self.assertTrue(call.next_run != 'foo')

    @mock.patch.object(ScheduledCall, 'calculate_next_run')
    def test_next_run_calculated(self, mock_calc):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething', next_run='foo')

        self.assertEqual(call.next_run, mock_calc.return_value)
        mock_calc.assert_called_once_with()


class TestScheduledCallFromDB(unittest.TestCase):
    def setUp(self):
        super(TestScheduledCallFromDB, self).setUp()
        self.schedule = bson.SON(SCHEDULE)

    def test_returns_instance(self):
        call = ScheduledCall.from_db(self.schedule)

        self.assertTrue(isinstance(call, ScheduledCall))

    def test_preserves_id(self):
        call = ScheduledCall.from_db(self.schedule)

        self.assertEqual(call.id, '529f4bd93de3a31d0ec77338')


class TestScheduledCallAsEntry(unittest.TestCase):
    def setUp(self):
        super(TestScheduledCallAsEntry, self).setUp()
        self.schedule = bson.SON(SCHEDULE)

    def test_returns_instance(self):
        call = ScheduledCall.from_db(self.schedule)

        entry = call.as_schedule_entry()

        self.assertTrue(isinstance(entry, celery.beat.ScheduleEntry))

    def test_values(self):
        call = ScheduledCall.from_db(self.schedule)

        entry = call.as_schedule_entry()

        self.assertEqual(entry._scheduled_call, call)
        self.assertTrue(isinstance(entry.schedule, CelerySchedule))
        self.assertEqual(entry.args, call.args)
        self.assertEqual(entry.kwargs, call.kwargs)
        self.assertEqual(entry.name, call.name)
        self.assertEqual(entry.task, call.task)
        self.assertEqual(entry.options, call.options)
        self.assertEqual(entry.last_run_at, dateutils.parse_iso8601_datetime(call.last_run_at))
        self.assertFalse(entry.schedule.relative)

    def test_no_last_run(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething')

        entry = call.as_schedule_entry()

        # celery actually calculates it, so we don't need to test the value
        self.assertTrue(isinstance(entry.last_run_at, datetime))


class TestScheduledCallAsDict(unittest.TestCase):
    def test_returns_dict(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething')

        self.assertTrue(isinstance(call.as_dict(), dict))

    def test_values(self):
        schedule = bson.SON(SCHEDULE)
        call = ScheduledCall.from_db(schedule)

        result = call.as_dict()

        self.assertEqual(result['_id'], call.id)
        for k, v in SCHEDULE.items():
            self.assertEqual(v, result[k])
        self.assertTrue('next_run' in result)


class TestScheduledCallForDisplay(unittest.TestCase):
    def test_returns_dict(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething')

        self.assertTrue(isinstance(call.for_display(), dict))

    def test_values(self):
        schedule = bson.SON(SCHEDULE)
        call = ScheduledCall.from_db(schedule)

        as_dict = call.as_dict()
        result = call.for_display()

        for k, v in result.items():
            if k not in ['schedule', 'iso_schedule']:
                self.assertEqual(v, as_dict[k])
        self.assertEqual(result['schedule'], as_dict['iso_schedule'])


@mock.patch('pulp.server.db.model.base.Model.get_collection')
class TestScheduledCallSave(unittest.TestCase):
    def test_existing(self, mock_get_collection):
        mock_update = mock_get_collection.return_value.update
        fake_id = bson.ObjectId()
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething', id=fake_id)

        call.save()

        expected = call.as_dict()
        del expected['_id']
        mock_update.assert_called_once_with({'_id': fake_id}, expected)

    def test_new(self, mock_get_collection):
        mock_insert = mock_get_collection.return_value.insert
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething')

        call.save()

        expected = call.as_dict()
        expected['_id'] = bson.ObjectId(expected['_id'])
        mock_insert.assert_called_once_with(expected, safe=True)
        self.assertFalse(call._new)


class TestScheduledCallCalculateTimes(unittest.TestCase):
    def test_now(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething')

        now = call._calculate_times()[0]

        # make sure this gives us a timestamp that reasonably represents "now"
        self.assertTrue(time.time() - now < 1)

    def test_first_run_now(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething')

        first_run_s = call._calculate_times()[1]

        # make sure this gives us a timestamp that reasonably represents "now"
        self.assertTrue(time.time() - first_run_s < 1)

    def test_first_run_scheduled(self):
        call = ScheduledCall('2014-01-03T10:15Z/PT1H', 'pulp.tasks.dosomething')

        first_run_s = call._calculate_times()[1]

        # make sure this gives us a timestamp for the date and time
        # specified above
        self.assertEqual(first_run_s, 1388744100)

    def test_first_run_saved(self):
        """
        Test that when the first run is passed in from historical data.
        """
        call = ScheduledCall('PT1H', 'pulp.tasks.dosomething', first_run='2014-01-03T10:15Z')

        first_run_s = call._calculate_times()[1]

        # make sure this gives us a timestamp for the date and time
        # specified above
        self.assertEqual(first_run_s, 1388744100)

    def test_since_first(self):
        call = ScheduledCall('2014-01-03T10:15Z/PT1H', 'pulp.tasks.dosomething')

        since_first = call._calculate_times()[2]
        now = time.time()

        self.assertTrue(since_first + 1388744100 - now < 1)

    def test_run_every(self):
        call = ScheduledCall('2014-01-03T10:15Z/PT1H', 'pulp.tasks.dosomething')

        run_every_s = call._calculate_times()[3]

        # 1 hour, as specified in the ISO8601 string above
        self.assertEqual(run_every_s, 3600)

    def test_last_scheduled_run_no_first_run(self):
        call = ScheduledCall('PT1H', 'pulp.tasks.dosomething')

        last_scheduled_run_s = call._calculate_times()[4]
        first_run_s = call._calculate_times()[1]

        self.assertEqual(last_scheduled_run_s, first_run_s)

    @mock.patch('time.time')
    def test_last_scheduled_run_with_first_run(self, mock_time):
        # specify a start time and current time such that we know the difference
        mock_time.return_value = 1389307330.966561
        call = ScheduledCall('2014-01-09T17:15Z/PT1H', 'pulp.tasks.dosomething')

        last_scheduled_run_s = call._calculate_times()[4]

        self.assertEqual(last_scheduled_run_s, 1389305700)

    @mock.patch('time.time')
    def test_expected_runs_positive(self, mock_time):
        # specify a start time and current time such that we know the difference
        mock_time.return_value = 1389307330.966561
        call = ScheduledCall('2014-01-09T17:15Z/PT1H', 'pulp.tasks.dosomething')

        expected_runs = call._calculate_times()[5]

        # we know that it's been more than 5 hours since the first scheduled run
        self.assertEqual(expected_runs, 5)

    @mock.patch('time.time')
    def test_expected_runs_future(self, mock_time):
        # specify a start time and current time such that the start appears to
        # be in the future
        mock_time.return_value = 1389307330.966561
        call = ScheduledCall('2014-01-19T17:15Z/PT1H', 'pulp.tasks.dosomething')

        expected_runs = call._calculate_times()[5]

        # the first run is scheduled in the future (relative to the mock time),
        # so there should not be any runs.
        self.assertEqual(expected_runs, 0)

    def test_expected_runs_zero(self):
        call = ScheduledCall('PT1H', 'pulp.tasks.dosomething')

        expected_runs = call._calculate_times()[5]

        self.assertEqual(expected_runs, 0)


class TestScheduledCallCalculateNextRun(unittest.TestCase):
    @mock.patch('time.time')
    def test_future(self, mock_time):
        mock_time.return_value = 1389307330.966561
        call = ScheduledCall('2014-01-19T17:15Z/PT1H', 'pulp.tasks.dosomething')

        next_run = call.calculate_next_run()

        # make sure the next run is equal to the specified first run.
        # don't want to compare a generated ISO8601 string directly, because there
        # could be subtle variations that are valid but break string equality.
        self.assertEqual(dateutils.parse_iso8601_interval(call.iso_schedule)[1],
                         dateutils.parse_iso8601_datetime(next_run))

    def test_now(self):
        call = ScheduledCall('PT1H', 'pulp.tasks.dosomething')

        now = datetime.utcnow().replace(tzinfo=dateutils.utc_tz())
        next_run = dateutils.parse_iso8601_datetime(call.calculate_next_run())

        self.assertTrue(next_run - now < timedelta(seconds=1))

    @mock.patch('time.time')
    def test_with_past_runs(self, mock_time):
        # setup an hourly call that first ran not quite 2 hours ago, ran again
        # less than one hour ago, and should be scheduled to run at the end of
        # this hour
        mock_time.return_value = 1389389758.547976
        call = ScheduledCall('2014-01-10T20:00Z/PT1H', 'pulp.tasks.dosomething',
                             total_run_count=2, last_run_at='2014-01-10T21:00Z')

        next_run = call.calculate_next_run()

        self.assertEqual(dateutils.parse_iso8601_datetime('2014-01-10T22:00Z'),
                         dateutils.parse_iso8601_datetime(next_run))


class TestScheduleEntryInit(unittest.TestCase):
    def test_captures_scheduled_call(self):
        call = ScheduledCall('2014-01-19T17:15Z/PT1H', 'pulp.tasks.dosomething')
        entry = call.as_schedule_entry()

        self.assertTrue(hasattr(entry, '_scheduled_call'))
        self.assertTrue(entry._scheduled_call is call)


@mock.patch.object(ScheduledCall, 'save')
class TestScheduleEntryNextInstance(unittest.TestCase):
    def setUp(self):
        super(TestScheduleEntryNextInstance, self).setUp()
        self.call = ScheduledCall('2014-01-19T17:15Z/PT1H', 'pulp.tasks.dosomething',
                                  remaining_runs=5)
        self.entry = self.call.as_schedule_entry()

    def test_increments_last_run(self, mock_save):
        next_entry = next(self.entry)
        now = datetime.utcnow().replace(tzinfo=dateutils.utc_tz())

        self.assertTrue(now - next_entry.last_run_at < timedelta(seconds=1))

    def test_increments_run_count(self, mock_save):
        next_entry = next(self.entry)

        self.assertEqual(self.entry.total_run_count + 1, next_entry.total_run_count)

    def test_decrements_remaining_runs(self, mock_save):
        remaining = self.call.remaining_runs

        next_entry = next(self.entry)

        self.assertEqual(remaining - 1, self.call.remaining_runs)

    def test_disables_for_remaining_runs(self, mock_save):
        self.call.remaining_runs = 1
        # just verify that we have the correct starting state
        self.assertTrue(self.call.enabled)

        next_entry = next(self.entry)

        # call should have been disabled because the remaining_runs hit 0
        self.assertFalse(self.call.enabled)

    def test_calls_save(self, mock_save):
        next_entry = next(self.entry)

        mock_save.assert_called_once_with()

    def test_returns_entry(self, mock_save):
        next_entry = next(self.entry)

        self.assertTrue(isinstance(next_entry, ScheduleEntry))
        self.assertEqual(self.entry.name, next_entry.name)
        self.assertFalse(self.entry is next_entry)


class TestScheduleEntryIsDue(unittest.TestCase):
    def setUp(self):
        super(TestScheduleEntryIsDue, self).setUp()
        self.call = ScheduledCall('2014-01-19T17:15Z/PT1H', 'pulp.tasks.dosomething',
                                  remaining_runs=5)
        self.entry = self.call.as_schedule_entry()

    @mock.patch('time.time')
    def test_first_run_future(self, mock_time):
        mock_time.return_value = 1389307330

        is_due, seconds = self.entry.is_due()

        self.assertFalse(is_due)
        self.assertEqual(seconds, 844370)

    def test_no_runs(self):
        call = ScheduledCall('PT1H', 'pulp.tasks.dosomething')
        entry = call.as_schedule_entry()

        is_due, seconds = entry.is_due()

        self.assertTrue(is_due)
        # make sure this is very close to one hour
        self.assertTrue(3600 - seconds < 1)

    @mock.patch('time.time')
    def test_past_runs_due(self, mock_time):
        mock_time.return_value = 1389389758 # 2014-01-10T21:35:58
        # This call did not run at the top of the hour, so it is overdue and should
        # run now. Its next run will be back on the normal hourly schedule, at
        # the top of the next hour.
        call = ScheduledCall('2014-01-10T20:00Z/PT1H', 'pulp.tasks.dosomething',
                             last_run_at='2014-01-10T20:00Z', total_run_count= 1)
        entry = call.as_schedule_entry()

        is_due, seconds = entry.is_due()

        self.assertTrue(is_due)
        # this was hand-calculated as the remaining time until the next hourly run
        self.assertEqual(seconds, 1442)

    @mock.patch('time.time')
    def test_past_runs_not_due(self, mock_time):
        mock_time.return_value = 1389389758 # 2014-01-10T21:35:58
        # This call ran at the top of the hour, so it does not need to run again
        # until the top of the next hour.
        call = ScheduledCall('2014-01-10T20:00Z/PT1H', 'pulp.tasks.dosomething',
                             last_run_at='2014-01-10T21:00Z', total_run_count=2)
        entry = call.as_schedule_entry()

        is_due, seconds = entry.is_due()

        self.assertFalse(is_due)
        # this was hand-calculated as the remaining time until the next hourly run
        self.assertEqual(seconds, 1442)


SCHEDULE = {
    u'_id': u'529f4bd93de3a31d0ec77338',
    u'args': [u'demo1', u'puppet_distributor'],
    u'consecutive_failures': 0,
    u'enabled': True,
    u'failure_threshold': 2,
    u'first_run': u'2013-12-04T15:35:53Z',
    u'iso_schedule': u'PT1M',
    u'kwargs': {u'overrides': {}},
    u'last_run_at': u'2013-12-17T00:35:53Z',
    u'last_updated': 1387218569.811224,
    u'principal': u"(dp0\nV_id\np1\nccopy_reg\n_reconstructor\np2\n(cbson.objectid\nObjectId\np3\nc__builtin__\nobject\np4\nNtp5\nRp6\nS'R \\xab\\x06\\xe1\\x9a\\x00\\x10\\xe1i\\x05\\x89'\np7\nbsVname\np8\nVadmin\np9\nsVroles\np10\n(lp11\nVsuper-users\np12\nasV_ns\np13\nVusers\np14\nsVlogin\np15\nVadmin\np16\nsVpassword\np17\nVV76Yol1XYgM=,S/G6o5UyMrn0xAwbQCqFcrXnfXTh84RWhunanCDkSCo=\np18\nsVid\np19\nV5220ab06e19a0010e1690589\np20\ns.",
    u'remaining_runs': None,
    u'resource': u'pulp:distributor:demo:puppet_distributor',
    u'schedule': u"ccopy_reg\n_reconstructor\np0\n(ccelery.schedules\nschedule\np1\nc__builtin__\nobject\np2\nNtp3\nRp4\n(dp5\nS'relative'\np6\nI00\nsS'nowfun'\np7\nNsS'run_every'\np8\ncdatetime\ntimedelta\np9\n(I0\nI60\nI0\ntp10\nRp11\nsb.",
    u'task': u'pulp.server.tasks.repository.publish',
    u'total_run_count': 1087,
}
