"""
Patch the built-in httplib/http.client libraries to trace all HTTP calls.

Patched modules:

 - httplib.HTTPConnection (Python 2)
 - httplib.client.HTTPConnection (Python 3)


Usage::

    # Patch all supported modules/functions
    from ddtrace.contrib.httplib import patch
    patch()

    # Python 2
    import urllib
    resp = urllib.urlopen('http://www.datadog.com/')

    # Python 3
    import urllib.request
    resp = urllib.request.urlopen('http://www.datadog.com/')

"""
from .patch import patch, unpatch
__all__ = ['patch', 'unpatch']
