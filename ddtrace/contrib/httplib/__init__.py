"""
Patch the built-in urllib libraries to trace all HTTP calls.

Patched modules:

 - urllib.urlopen (Python 2)
 - httplib.HTTPConnection (Python 2)
 - httplib.client.HTTPClient (Python 3)


Usage::

    # Patch all supported modules/functions
    from ddtrace.contrib.httplib import patch
    patch()

    import urllib

    resp = urllib.urlopen('http://www.datadog.com/')

"""
from .patch import patch, unpatch
__all__ = ['patch', 'unpatch']
