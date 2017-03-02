import flask
import flask.templating
import wrapt

from .templating import _patch_render
from ...compat import to_unicode
from ...ext import AppTypes
from ...ext import http, errors
from ...pin import Pin

SERVICE = 'flask'
APP = 'flask'


def patch(app=None, pin=None):
    """"""
    app = app or flask.Flask

    pin = pin or Pin(service=SERVICE, app=APP, app_type=AppTypes.web)

    patch_methods = [
        ('full_dispatch_request', _full_dispatch_request),
    ]

    for method_name, wrapper in patch_methods:
        method = getattr(app, method_name, None)
        if method is None:
            continue

        if isinstance(method, wrapt.ObjectProxy):
            continue

        setattr(flask.Flask, method_name, wrapt.BoundFunctionWrapper(method, app, wrapper))

    _patch_render(pin=pin)

    pin.onto(app)
    return app


def require_pin(decorated):
    """ decorator for extracting the `Pin` from a wrapped method """
    def wrapper(wrapped, instance, args, kwargs):
        pin = Pin.get_from(instance)
        # Execute the original method if pin is not enabled
        if not pin or not pin.enabled():
            return wrapped(*args, **kwargs)

        # Execute our decorated function
        return decorated(pin, wrapped, instance, args, kwargs)
    return wrapper


@require_pin
def _full_dispatch_request(pin, func, app, args, kwargs):
    """"""
    with pin.tracer.trace('flask.request', service=pin.service, span_type=http.TYPE) as span:
        response = None
        exception = None
        try:
            response = func(*args, **kwargs)
        except Exception, exception:
            raise
        finally:
            try:
                error = 0
                code = response.status_code if response else None
                if not response and exception:
                    error = 1
                    code = 500
                    span.set_tag(errors.ERROR_TYPE, type(exception))
                    span.set_tag(errors.ERROR_MSG, exception)

                resource = response.status_code if not flask.request.endpoint else flask.request.endpoint
                span.resource = to_unicode(resource).lower()
                span.set_tag(http.URL, flask.request.base_url)
                span.set_tag(http.STATUS_CODE, code)
                span.error = error
            except Exception:
                pass

        return response
