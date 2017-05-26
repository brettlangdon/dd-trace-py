# Standard library
import logging

# Third party
import wrapt

# Project
import ddtrace
from ...compat import httplib, PY2
from ...ext import http as ext_http
from ...util import unwrap as _u


span_name = 'httplib.request' if PY2 else 'http.client.request'

log = logging.getLogger(__name__)


def _wrap_getresponse(func, instance, args, kwargs):
    # Use any attached tracer if available, otherwise use the global tracer
    tracer = getattr(instance, 'datadog_tracer', ddtrace.tracer)

    # DEV: We explicitly set the instance tracer to `None` when using HTTPConnection internally
    if not tracer or not tracer.enabled:
        return func(*args, **kwargs)

    resp = None
    try:
        resp = func(*args, **kwargs)
        return resp
    finally:
        try:
            # Get the span attached to this instance, if available
            span = getattr(instance, '_datadog_span', None)
            if not span:
                return

            if resp:
                span.set_tag(ext_http.STATUS_CODE, resp.status)
                span.error = int(500 <= resp.status)

            span.finish()
            delattr(instance, '_datadog_span')
        except Exception:
            log.debug('error applying request tags', exc_info=True)


def _wrap_putrequest(func, instance, args, kwargs):
    # Use any attached tracer if available, otherwise use the global tracer
    tracer = getattr(instance, 'datadog_tracer', ddtrace.tracer)

    # DEV: We explicitly set the instance tracer to `None` when using HTTPConnection internally
    if not tracer or not tracer.enabled:
        return func(*args, **kwargs)

    try:
        # Create a new span and attach to this instance (so we can retrieve/update/close later on the response)
        span = tracer.trace(span_name, span_type=ext_http.TYPE)
        setattr(instance, '_datadog_span', span)

        method, path = args[:2]
        scheme = 'https' if isinstance(instance, httplib.HTTPSConnection) else 'http'
        port = ':{port}'.format(port=instance.port)
        if (scheme == 'http' and instance.port == 80) or (scheme == 'https' and instance.port == 443):
            port = ''
        url = '{scheme}://{host}{port}{path}'.format(scheme=scheme, host=instance.host, port=port, path=path)
        span.set_tag(ext_http.URL, url)
        span.set_tag(ext_http.METHOD, method)
    except Exception:
        log.debug('error applying request tags', exc_info=True)

    return func(*args, **kwargs)


def patch():
    """ patch the built-in urllib/httplib/httplib.client methods for tracing"""
    if getattr(httplib, '__datadog_patch', False):
        return
    setattr(httplib, '__datadog_patch', True)

    setattr(httplib.HTTPConnection, 'getresponse',
            wrapt.FunctionWrapper(httplib.HTTPConnection.getresponse, _wrap_getresponse))
    setattr(httplib.HTTPConnection, 'putrequest',
            wrapt.FunctionWrapper(httplib.HTTPConnection.putrequest, _wrap_putrequest))


def unpatch():
    """ unpatch any previously patched modules """
    if not getattr(httplib, '__datadog_patch', False):
        return
    setattr(httplib, '__datadog_patch', False)

    _u(httplib.HTTPConnection, 'getresponse')
    _u(httplib.HTTPConnection, 'putrequest')
