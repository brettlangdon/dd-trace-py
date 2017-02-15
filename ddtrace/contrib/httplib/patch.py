# Standard library
from importlib import import_module
import logging

# Third party
import wrapt

# Project
import ddtrace
from ...compat import PY2
from ...ext import http

if PY2:
    from httplib import HTTPSConnection
else:
    from http.client import HTTPSConnection


log = logging.getLogger(__name__)


def _wrap_urlopen(func, instance, args, kwargs):
    # Use any attached tracer if available, otherwise use the global tracer
    tracer = getattr(func, 'datadog_tracer', ddtrace.tracer)

    if not tracer.enabled:
        return func(*args, **kwargs)

    with tracer.trace('urllib.urlopen', span_type=http.TYPE) as span:
        try:
            url = kwargs.get('url') or args[0]
            data = kwargs.get('data')
            if not data and len(args) > 1:
                data = args[1]

            span.set_tag(http.URL, url)
            method = 'GET' if not data else 'POST'
            span.set_tag(http.METHOD, method)
        except Exception:
                log.warn('error applying request tags', exc_info=True)

        resp = None
        try:
            resp = func(*args, **kwargs)
            return resp
        finally:
            try:
                if resp:
                    status_code = resp.getcode()
                    span.set_tag(http.STATUS_CODE, status_code)
                    span.error = int(500 <= status_code)
            except Exception:
                log.warn('error applying response tags', exc_info=True)


def _wrap_request(func, instance, args, kwargs):
    # Use any attached tracer if available, otherwise use the global tracer
    tracer = getattr(instance, 'datadog_tracer', ddtrace.tracer)

    if not tracer.enabled:
        return func(*args, **kwargs)

    try:
        trace_name = 'httplib.request' if PY2 else 'http.client.request'
        span = tracer.trace(trace_name, span_type=http.TYPE)
        setattr(instance, 'datadog_span', span)

        method, path = args[:2]
        scheme = 'https' if isinstance(instance, HTTPSConnection) else 'http'
        port = ':{port}'.format(port=instance.port)
        if (scheme == 'http' and instance.port == 80) or (scheme == 'https' and instance.port == 443):
            port = ''
        url = '{scheme}://{host}{port}{path}'.format(scheme=scheme, host=instance.host, port=port, path=path)
        span.set_tag(http.URL, url)
        span.set_tag(http.METHOD, method)
    except Exception:
        log.warn('error applying request tags', exc_info=True)

    return func(*args, **kwargs)


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
            span = getattr(instance, 'datadog_span', None)
            if not span:
                return

            if resp:
                span.set_tag(http.STATUS_CODE, resp.status)
                span.error = int(500 <= resp.status)

            span.finish()
            delattr(instance, 'datadog_span')
        except Exception:
            log.warn('error applying request tags', exc_info=True)


wrap_modules = []
if PY2:
    wrap_modules = [
        ('urllib', 'urlopen', _wrap_urlopen),
        ('httplib', 'HTTPConnection.request', _wrap_request),
        ('httplib', 'HTTPConnection.getresponse', _wrap_getresponse),
    ]
else:
    wrap_modules = [
        ('http.client', 'HTTPConnection.request', _wrap_request),
        ('http.client', 'HTTPConnection.getresponse', _wrap_getresponse),
    ]


def patch():
    """ patch the built-in urllib/httplib/httplib.client methods for tracing"""
    for module_name, func_name, wrapper in wrap_modules:
        wrapt.wrap_function_wrapper(module_name, func_name, wrapper)


def unpatch():
    """ unpatch any previously patched modules """
    for module_name, func_name in wrap_modules:
        module = import_module(module_name)
        func = getattr(module, func_name, None)
        if func and hasattr(func, '__wrapped__'):
            setattr(module, func_name, func.__wrapped__)
