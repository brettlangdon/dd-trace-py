# Standard library
import logging

# Third party
import wrapt

# Project
from ... import tracer
from ...compat import PY2, string_type
from ...ext import http

log = logging.getLogger(__name__)


def patch():
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

    for module, func in wrap_modules:
        trace_name = '{module}.{func}'.format(module=module, func=func)
        wrapt.wrap_function_wrapper(module, func, _get_urlopen_wrapper(trace_name))


def _get_urlopen_wrapper(trace_name):
    def _wrapped_urlopen(func, instance, args, kwargs):
        if not tracer.enabled:
            return func(*args, **kwargs)

        with tracer.trace(trace_name, span_type=http.TYPE) as span:
            resp = None
            try:
                resp = func(*args, **kwargs)
                return resp
            finally:
                try:
                    _apply_tags(span, args, kwargs, resp)
                except Exception:
                    log.warn('error applying response tags', exc_info=True)

    return _wrapped_urlopen


def _apply_tags(span, args, kwargs, resp):
    if not resp:
        return

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

    status_code = resp.getcode()
    span.set_tag(http.STATUS_CODE, status_code)
    span.error = int(500 <= status_code)
