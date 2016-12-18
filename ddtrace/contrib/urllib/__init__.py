"""
Patch the built-in urllib libraries to trace all HTTP calls.

Patched modules:

 - urllib.urlopen (Python 2)
 - urllib2.urlopen (Python 2)
 - urllib.request.urlopen (Python 3)


Usage::

    # Patch all supported modules/functions
    from ddtrace.contrib.urllib import patch
    patch()

    import urllib

    resp = urllib.urlopen('http://www.datadog.com/')

"""
from .patch import patch, unpatch
__all__ = ['patch', 'unpatch']
