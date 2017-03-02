import flask
import flask.templating
import wrapt

from ...compat import to_unicode
from ...ext import AppTypes
from ...ext import http, errors
from ...pin import Pin
from ...util import require_pin

SERVICE = 'flask'
APP = 'flask'


def patch_app(app=None, pin=None):
    """ Patch either a specific Flask instance or the base flask.Flask class for tracing"""
    # Use the base class if we don't have an instance
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

        setattr(app, method_name, wrapt.BoundFunctionWrapper(method, app, wrapper))

    # Attach the pin to this instance
    pin.onto(app)
    return app

def unpatch_app(app=None):
    app = app or flask.Flask

    unpatch_methods = ['full_dispatch_request']
    for method_name in unpatch_methods:
        method = getattr(app, method_name, None)
        if method is None:
            continue

        if not isinstance(method, wrapt.ObjectProxy):
            continue

        setattr(app, method_name, method.__wrapped__)


@require_pin
def _full_dispatch_request(pin, func, app, args, kwargs):
    """"""
    with pin.tracer.trace('flask.request', service=pin.service, span_type=http.TYPE) as span:
        response = None
        exception = None
        try:
            response = func(*args, **kwargs)
        except Exception as exception:
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
