import unittest

import celery
import mock
import wrapt

from ddtrace import Pin
from ddtrace.contrib.celery.app import patch_app, unpatch_app
from ddtrace.contrib.celery.task import patch_task, unpatch_task

from ...test_tracer import get_dummy_tracer


class CeleryTaskTest(unittest.TestCase):
    def setUp(self):
        self.tracer = get_dummy_tracer()
        self.pin = Pin(service='celery-test', tracer=self.tracer)
        patch_app(celery.Celery, pin=self.pin)
        patch_task(celery.Task, pin=self.pin)

    def tearDown(self):
        unpatch_app(celery.Celery)
        unpatch_task(celery.Task)

    def test_patch_task(self):
        """
        When celery.Task is patched
            we patch the __init__, apply, apply_async, and run methods
        """
        # Assert base class methods are patched
        self.assertIsInstance(celery.Task.__init__, wrapt.BoundFunctionWrapper)
        self.assertIsInstance(celery.Task.apply, wrapt.BoundFunctionWrapper)
        self.assertIsInstance(celery.Task.apply_async, wrapt.BoundFunctionWrapper)
        self.assertIsInstance(celery.Task.run, wrapt.BoundFunctionWrapper)

        # Create an instance of a Task
        task = celery.Task()

        # Assert instance methods are patched
        self.assertIsInstance(task.__init__, wrapt.BoundFunctionWrapper)
        self.assertIsInstance(task.apply, wrapt.BoundFunctionWrapper)
        self.assertIsInstance(task.apply_async, wrapt.BoundFunctionWrapper)
        self.assertIsInstance(task.run, wrapt.BoundFunctionWrapper)

    def test_unpatch_task(self):
        """
        When unpatch_task is called on a patched task
            we unpatch the __init__, apply, apply_async, and run methods
        """
        # Assert base class methods are patched
        self.assertIsInstance(celery.Task.__init__, wrapt.BoundFunctionWrapper)
        self.assertIsInstance(celery.Task.apply, wrapt.BoundFunctionWrapper)
        self.assertIsInstance(celery.Task.apply_async, wrapt.BoundFunctionWrapper)
        self.assertIsInstance(celery.Task.run, wrapt.BoundFunctionWrapper)

        # Unpatch the base class
        unpatch_task(celery.Task)

        # Assert the methods are no longer wrapper
        self.assertFalse(isinstance(celery.Task.__init__, wrapt.BoundFunctionWrapper))
        self.assertFalse(isinstance(celery.Task.apply, wrapt.BoundFunctionWrapper))
        self.assertFalse(isinstance(celery.Task.apply_async, wrapt.BoundFunctionWrapper))
        self.assertFalse(isinstance(celery.Task.run, wrapt.BoundFunctionWrapper))

    def test_task_init(self):
        """
        Creating an instance of a patched celery.Task
            will yield a patched instance
        """
        task = celery.Task()

        # Assert instance methods are patched
        self.assertIsInstance(task.__init__, wrapt.BoundFunctionWrapper)
        self.assertIsInstance(task.apply, wrapt.BoundFunctionWrapper)
        self.assertIsInstance(task.apply_async, wrapt.BoundFunctionWrapper)
        self.assertIsInstance(task.run, wrapt.BoundFunctionWrapper)

    def test_task_run(self):
        """
        Calling the run method of a patched task
            calls the original run() method
            creates a span for the call
        """
        # Create an instance of our patched app
        app = celery.Celery()

        # Create our test task
        task_spy = mock.Mock(__name__='patched_task')
        patched_task = app.task(task_spy)

        # Call the run method
        patched_task.run()

        # Assert it was called
        task_spy.assert_called_once()

        # Assert we created a span
        spans = self.tracer.writer.pop()
        self.assertEqual(len(spans), 1)

        span = spans[0]
        self.assertItemsEqual(
            span.to_dict().keys(),
            ['service', 'resource', 'meta', 'name', 'parent_id', 'trace_id', 'duration', 'error', 'start', 'span_id']
        )

        self.assertEqual(span.service, 'celery-test')
        self.assertEqual(span.resource, 'mock.mock.patched_task')
        self.assertEqual(span.name, 'celery.task.run')
        self.assertEqual(span.error, 0)

        # Assert the metadata is correct
        # DEV: A lot of this is `None` since calling `.run()` doesn't schedule the task,
        #   so it won't get an id, or anything else
        meta = span.meta
        self.maxDiff = None
        self.assertDictEqual(meta, dict(
            called_directly='True',
            correlation_id='None',
            delivery_info='None',
            eta='None',
            expires='None',
            hostname='None',
            id='None',
            is_eager='False',
            reply_to='None',
            retries='0',
            task='None',
            timelimit='None',
            utc='None',
        ))
