"""
Patch the built-in httplib/http.client libraries to trace all HTTP calls.


Usage::

    # Patch all supported modules/functions
    from ddtrace import patch
    patch(httplib=True)

    # Python 2
    import urllib
    resp = urllib.urlopen('http://www.datadog.com/')

    # Python 3
    import urllib.request
    resp = urllib.request.urlopen('http://www.datadog.com/')

"""
from .patch import patch, unpatch
__all__ = ['patch', 'unpatch']
