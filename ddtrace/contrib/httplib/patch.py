# Standard library
import logging

# Third party
import wrapt

# Project
import ddtrace
from ...compat import PY2
from ...ext import http as ext_http

if PY2:
    from httplib import HTTPSConnection
else:
    from http.client import HTTPSConnection


log = logging.getLogger(__name__)


def _wrap_getresponse(func, instance, args, kwargs):
    # Use any attached tracer if available, otherwise use the global tracer
    tracer = getattr(instance, 'datadog_tracer', ddtrace.tracer)

    if not tracer.enabled:
        return func(*args, **kwargs)

    resp = None
    try:
        resp = func(*args, **kwargs)
        return resp
    finally:
        try:
            # Get the span attached to this instance, if available
            span = getattr(instance, 'datadog_span', None)
            if not span:
                return

            if resp:
                span.set_tag(ext_http.STATUS_CODE, resp.status)
                span.error = int(500 <= resp.status)

            span.finish()
            delattr(instance, 'datadog_span')
        except Exception:
            log.warning('error applying request tags', exc_info=True)


def _wrap_putrequest(func, instance, args, kwargs):
    # Use any attached tracer if available, otherwise use the global tracer
    # Use any attached tracer if available, otherwise use the global tracer
    tracer = getattr(instance, 'datadog_tracer', ddtrace.tracer)

    if not tracer.enabled:
        return func(*args, **kwargs)

    try:
        trace_name = 'httplib.request' if PY2 else 'http.client.request'

        # Create a new span and attach to this instance (so we can retrieve/update/close later on the response)
        span = tracer.trace(trace_name, span_type=ext_http.TYPE)
        setattr(instance, 'datadog_span', span)

        method, path = args[:2]
        scheme = 'https' if isinstance(instance, HTTPSConnection) else 'http'
        port = ':{port}'.format(port=instance.port)
        if (scheme == 'http' and instance.port == 80) or (scheme == 'https' and instance.port == 443):
            port = ''
        url = '{scheme}://{host}{port}{path}'.format(scheme=scheme, host=instance.host, port=port, path=path)
        span.set_tag(ext_http.URL, url)
        span.set_tag(ext_http.METHOD, method)
    except Exception:
        log.warning('error applying request tags', exc_info=True)

    return func(*args, **kwargs)


wrap_modules = []
if PY2:
    import httplib
    wrap_modules = [
        (httplib.HTTPConnection, 'getresponse', _wrap_getresponse),
        (httplib.HTTPConnection, 'putrequest', _wrap_putrequest),
    ]
else:
    import http.client
    wrap_modules = [
        (http.client.HTTPConnection, 'getresponse', _wrap_getresponse),
        (http.client.HTTPConnection, 'putrequest', _wrap_putrequest),
    ]


def patch():
    """ patch the built-in urllib/httplib/httplib.client methods for tracing"""
    for cls, func_name, wrapper in wrap_modules:
        method = getattr(cls, func_name)
        setattr(cls, func_name, wrapt.FunctionWrapper(method, wrapper))


def unpatch():
    """ unpatch any previously patched modules """
    for cls, func_name, _ in wrap_modules:
        func = getattr(cls, func_name, None)
        if func and hasattr(func, '__wrapped__'):
            setattr(cls, func_name, func.__wrapped__)
