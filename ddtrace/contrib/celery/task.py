# Third party
import wrapt

# Project
from ddtrace import Pin
from ...ext import celery as celeryx
from .util import with_pin


def patch_task(task, pin=None):
    """ patch_task will add tracing to a celery task """
    pin = pin or Pin(service=celeryx.SERVICE, app=celeryx.APP)

    patch_methods = [
        ('__init__', _task_init),
        ('run', _task_run),
        ('apply', _task_apply),
        ('apply_async', _task_apply_async),
    ]
    for method_name, wrapper in patch_methods:
        # Get original method
        method = getattr(task, method_name, None)
        if method is None:
            continue

        # Do not patch if method is already patched
        if isinstance(method, wrapt.ObjectProxy):
            continue

        # Patch method
        # DEV: Using `BoundFunctionWrapper` ensures our `task` wrapper parameter is properly set
        setattr(task, method_name, wrapt.BoundFunctionWrapper(method, task, wrapper))

    # Attach our pin to the app
    pin.onto(task)
    return task


def _task_init(func, task, args, kwargs):
    func(*args, **kwargs)

    # Patch this task if our pin is enabled
    pin = Pin.get_from(task)
    if pin and pin.enabled():
        patch_task(task, pin=pin)


@with_pin
def _task_run(pin, func, task, args, kwargs):
    with pin.tracer.trace(celeryx.TASK_RUN, service=pin.service, resource=task.name):
        return func(*args, **kwargs)


@with_pin
def _task_apply(pin, func, task, args, kwargs):
    with pin.tracer.trace(celeryx.TASK_APPLY, resource=task.name):
        return func(*args, **kwargs)


@with_pin
def _task_apply_async(pin, func, task, args, kwargs):
    with pin.tracer.trace(celeryx.TASK_APPLY_ASYNC, resource=task.name):
        return func(*args, **kwargs)
