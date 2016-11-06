# Project
from ddtrace import Pin


def with_pin(decorated):
    """ decorator for extracting the `Pin` from a wrapped method """
    def wrapper(wrapped, instance, args, kwargs):
        pin = Pin.get_from(instance)
        # Execute the original method if pin is not enabled
        if not pin or not pin.enabled():
            return wrapped(*args, **kwargs)

        # Execute our decorated function
        return decorated(pin, wrapped, instance, args, kwargs)
    return wrapper
