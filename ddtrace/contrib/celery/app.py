# Standard library
import types

# Third party
import wrapt

# Project
from ddtrace import Pin
from ...ext import celery as celeryx
from .task import patch_task
from .util import require_pin


def patch_app(app, pin=None):
    """ patch_app will add tracing to a celery app """
    pin = pin or Pin(service=celeryx.SERVICE, app=celeryx.APP)
    patch_methods = [
        ('task', _app_task),
    ]
    for method_name, wrapper in patch_methods:
        # Get the original method
        method = getattr(app, method_name, None)
        if method is None:
            continue

        # Do not patch if method is already patched
        if isinstance(method, wrapt.ObjectProxy):
            continue

        # Patch method
        setattr(app, method_name, wrapt.FunctionWrapper(method, wrapper))

    # Attach our pin to the app
    pin.onto(app)
    return app


@require_pin
def _app_task(pin, func, app, args, kwargs):
    task = func(*args, **kwargs)

    # `app.task` is a decorator which may return a function wrapper
    if isinstance(task, types.FunctionType):
        def wrapper(func, instance, args, kwargs):
            return patch_task(func(*args, **kwargs), pin=pin)
        return wrapt.FunctionWrapper(task, wrapper)

    return patch_task(task, pin=pin)
