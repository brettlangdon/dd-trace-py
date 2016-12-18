# Standard library
from importlib import import_module
import logging
import sys

# Third party
import wrapt

# Project
import ddtrace
from ...compat import PY2, string_type
from ...ext import http

if PY2:
    from urllib2 import HTTPError
else:
    from urllib.error import HTTPError

log = logging.getLogger(__name__)

wrap_modules = []
if PY2:
    wrap_modules = [
        ('urllib', 'urlopen'),
        ('urllib2', 'urlopen'),
    ]
else:
    wrap_modules = [
        ('urllib.request', 'urlopen'),
    ]


def patch():
    """ patch the built-in urllib/urllib2/urllib.request methods for tracing"""
    for module_name, func_name in wrap_modules:
        trace_name = '{module_name}.{func_name}'.format(module_name=module_name, func_name=func_name)
        wrapt.wrap_function_wrapper(module_name, func_name, _get_urlopen_wrapper(trace_name))


def unpatch():
    """ unpatch any previously patched modules """
    for module_name, func_name in wrap_modules:
        module = import_module(module_name)
        func = getattr(module, func_name, None)
        if func and hasattr(func, '__wrapped__'):
            setattr(module, func_name, func.__wrapped__)

def _get_urlopen_wrapper(trace_name):
    """ helper method to return a function wrapper for a specific module/function """
    def _wrapped_urlopen(func, instance, args, kwargs):
        # Use any attached tracer if available, otherwise use the global tracer
        tracer = getattr(func, 'datadog_tracer', ddtrace.tracer)

        if not tracer.enabled:
            return func(*args, **kwargs)

        # Trace the method call
        with tracer.trace(trace_name, span_type=http.TYPE) as span:
            resp = None
            try:
                resp = func(*args, **kwargs)
                return resp
            except HTTPError:
                # The captured HTTPError contains our response (has the same methods/attributes as our response)
                # DEV: Python 2 and 3 capture exceptions differently, use `sys.exc_info` to avoid a syntax error
                resp = sys.exc_info()[1]
                raise
            finally:
                try:
                    _apply_tags(span, args, kwargs, resp)
                except Exception:
                    log.warn('error applying response tags', exc_info=True)

    return _wrapped_urlopen


def _apply_tags(span, args, kwargs, resp):
    """ helper method to apply trace tags from a urllib response (or error)"""
    url = kwargs.get('url') or args[0]
    data = kwargs.get('data')
    if not data and len(args) > 1:
        data = args[1]

    if isinstance(url, string_type):
        span.set_tag(http.URL, url)
        method = 'GET' if not data else 'POST'
        span.set_tag(http.METHOD, method)
    else:
        span.set_tag(http.URL, url.get_full_url())
        span.set_tag(http.METHOD, url.get_method())

    if resp:
        status_code = resp.getcode()
        span.set_tag(http.STATUS_CODE, status_code)
        span.error = int(500 <= status_code)
