# Standard library
import contextlib
import sys
import unittest

# Third party
import wrapt

# Project
from ddtrace.compat import PY2
from ddtrace.contrib.httplib import patch, unpatch
from ...test_tracer import get_dummy_tracer


if PY2:
    import httplib
    import urllib
    import urllib2

    class HTTPLibPython2Test(unittest.TestCase):
        def setUp(self):
            patch()
            self.tracer = get_dummy_tracer()
            setattr(httplib.HTTPConnection, 'datadog_tracer', self.tracer)

        def tearDown(self):
            unpatch()

        def test_patch(self):
            """
            When patching httplib
                we patch the correct module/methods
            """
            self.assertIsInstance(httplib.HTTPConnection.putrequest, wrapt.BoundFunctionWrapper)
            self.assertIsInstance(httplib.HTTPConnection.getresponse, wrapt.BoundFunctionWrapper)

        def test_unpatch(self):
            """
            When unpatching httplib
                we restore the correct module/methods
            """
            original_putrequest = httplib.HTTPConnection.putrequest.__wrapped__
            original_getresponse = httplib.HTTPConnection.getresponse.__wrapped__
            unpatch()

            self.assertEqual(httplib.HTTPConnection.putrequest, original_putrequest)
            self.assertEqual(httplib.HTTPConnection.getresponse, original_getresponse)

        def test_httplib_request_get_request(self):
            """
            When making a GET request via httplib.HTTPConnection.request
                we return the original response
                we capture a span for the request
            """
            conn = httplib.HTTPConnection('httpstat.us')
            with contextlib.closing(conn):
                conn.request('GET', '/200')
                resp = conn.getresponse()
                self.assertEqual(resp.read(), '200 OK')
                self.assertEqual(resp.status, 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'httplib.request')
            self.assertEqual(span.error, 0)
            self.assertDictEqual(
                span.meta,
                {
                    'http.method': 'GET',
                    'http.status_code': '200',
                    'http.url': 'http://httpstat.us/200',
                }
            )

        def test_httplib_request_post_request(self):
            """
            When making a POST request via httplib.HTTPConnection.request
                we return the original response
                we capture a span for the request
            """
            conn = httplib.HTTPConnection('httpstat.us')
            with contextlib.closing(conn):
                conn.request('POST', '/200', body='key=value')
                resp = conn.getresponse()
                self.assertEqual(resp.read(), '200 OK')
                self.assertEqual(resp.status, 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'httplib.request')
            self.assertEqual(span.error, 0)
            self.assertDictEqual(
                span.meta,
                {
                    'http.method': 'POST',
                    'http.status_code': '200',
                    'http.url': 'http://httpstat.us/200',
                }
            )

        def test_httplib_request_get_request_query_string(self):
            """
            When making a GET request with a query string via httplib.HTTPConnection.request
                we capture a the entire url in the span
            """
            conn = httplib.HTTPConnection('httpstat.us')
            with contextlib.closing(conn):
                conn.request('GET', '/200?key=value&key2=value2')
                resp = conn.getresponse()
                self.assertEqual(resp.read(), '200 OK')
                self.assertEqual(resp.status, 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'httplib.request')
            self.assertEqual(span.error, 0)
            self.assertDictEqual(
                span.meta,
                {
                    'http.method': 'GET',
                    'http.status_code': '200',
                    'http.url': 'http://httpstat.us/200?key=value&key2=value2',
                }
            )

        def test_httplib_request_500_request(self):
            """
            When making a GET request via httplib.HTTPConnection.request
                when the response is a 500
                    we raise the original exception
                    we mark the span as an error
                    we capture the correct span tags
            """
            try:
                conn = httplib.HTTPConnection('httpstat.us')
                with contextlib.closing(conn):
                    conn.request('GET', '/500')
                    conn.getresponse()
            except httplib.HTTPException:
                resp = sys.exc_info()[1]
                self.assertEqual(resp.read(), '500 Internal Server Error')
                self.assertEqual(resp.status, 500)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'httplib.request')
            self.assertEqual(span.error, 1)
            self.assertEqual(span.get_tag('http.method'), 'GET')
            self.assertEqual(span.get_tag('http.status_code'), '500')
            self.assertEqual(span.get_tag('http.url'), 'http://httpstat.us/500')

        def test_httplib_request_non_200_request(self):
            """
            When making a GET request via httplib.HTTPConnection.request
                when the response is a non-200
                    we raise the original exception
                    we mark the span as an error
                    we capture the correct span tags
            """
            try:
                conn = httplib.HTTPConnection('httpstat.us')
                with contextlib.closing(conn):
                    conn.request('GET', '/404')
                    conn.getresponse()
            except httplib.HTTPException:
                resp = sys.exc_info()[1]
                self.assertEqual(resp.read(), '404 Not Found')
                self.assertEqual(resp.status, 404)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'httplib.request')
            self.assertEqual(span.error, 0)
            self.assertEqual(span.get_tag('http.method'), 'GET')
            self.assertEqual(span.get_tag('http.status_code'), '404')
            self.assertEqual(span.get_tag('http.url'), 'http://httpstat.us/404')

        def test_httplib_request_get_request_disabled(self):
            """
            When making a GET request via httplib.HTTPConnection.request
                when the tracer is disabled
                    we do not capture any spans
            """
            self.tracer.enabled = False
            conn = httplib.HTTPConnection('httpstat.us')
            with contextlib.closing(conn):
                conn.request('GET', '/200')
                resp = conn.getresponse()
                self.assertEqual(resp.read(), b'200 OK')
                self.assertEqual(resp.status, 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 0)

        def test_urllib_request(self):
            """
            When making a request via urllib.urlopen
               we return the original response
               we capture a span for the request
            """
            resp = urllib.urlopen('http://httpstat.us/200')
            self.assertEqual(resp.read(), '200 OK')
            self.assertEqual(resp.getcode(), 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'httplib.request')
            self.assertEqual(span.error, 0)
            self.assertEqual(span.get_tag('http.method'), 'GET')
            self.assertEqual(span.get_tag('http.status_code'), '200')
            self.assertEqual(span.get_tag('http.url'), 'http://httpstat.us/200')

        def test_urllib2_request(self):
            """
            When making a request via urllib2.urlopen
               we return the original response
               we capture a span for the request
            """
            resp = urllib2.urlopen('http://httpstat.us/200')
            self.assertEqual(resp.read(), '200 OK')
            self.assertEqual(resp.getcode(), 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'httplib.request')
            self.assertEqual(span.error, 0)
            self.assertEqual(span.get_tag('http.method'), 'GET')
            self.assertEqual(span.get_tag('http.status_code'), '200')
            self.assertEqual(span.get_tag('http.url'), 'http://httpstat.us/200')

        def test_urllib2_request_object(self):
            """
            When making a request via urllib2.urlopen
               with a urllib2.Request object
                   we return the original response
                   we capture a span for the request
            """
            req = urllib2.Request('http://httpstat.us/200')
            resp = urllib2.urlopen(req)
            self.assertEqual(resp.read(), '200 OK')
            self.assertEqual(resp.getcode(), 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'httplib.request')
            self.assertEqual(span.error, 0)
            self.assertEqual(span.get_tag('http.method'), 'GET')
            self.assertEqual(span.get_tag('http.status_code'), '200')
            self.assertEqual(span.get_tag('http.url'), 'http://httpstat.us/200')

        def test_urllib2_request_opener(self):
            """
            When making a request via urllib2.urlopen
               with a urllib2.Request object
                   we return the original response
                   we capture a span for the request
            """
            opener = urllib2.build_opener()
            resp = opener.open('http://httpstat.us/200')
            self.assertEqual(resp.read(), '200 OK')
            self.assertEqual(resp.getcode(), 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'httplib.request')
            self.assertEqual(span.error, 0)
            self.assertEqual(span.get_tag('http.method'), 'GET')
            self.assertEqual(span.get_tag('http.status_code'), '200')
            self.assertEqual(span.get_tag('http.url'), 'http://httpstat.us/200')

else:
    import http.client
    import urllib.request

    class HTTPLibPython3Test(unittest.TestCase):
        def setUp(self):
            patch()
            self.tracer = get_dummy_tracer()
            setattr(http.client.HTTPConnection, 'datadog_tracer', self.tracer)

        def tearDown(self):
            unpatch()

        def test_patch(self):
            """
            When patching http.client
                we patch the correct module/methods
            """
            self.assertIsInstance(http.client.HTTPConnection.putrequest, wrapt.BoundFunctionWrapper)
            self.assertIsInstance(http.client.HTTPConnection.getresponse, wrapt.BoundFunctionWrapper)

        def test_unpatch(self):
            """
            When unpatching http.client
                we restore the correct module/methods
            """
            original_putrequest = http.client.HTTPConnection.putrequest.__wrapped__
            original_getresponse = http.client.HTTPConnection.getresponse.__wrapped__
            unpatch()

            self.assertEqual(http.client.HTTPConnection.putrequest, original_putrequest)
            self.assertEqual(http.client.HTTPConnection.getresponse, original_getresponse)

        def test_http_client_request_get_request(self):
            """
            When making a GET request via http.client.HTTPConnection.request
                we return the original response
                we capture a span for the request
            """
            conn = http.client.HTTPConnection('httpstat.us')
            with contextlib.closing(conn):
                conn.request('GET', '/200')
                resp = conn.getresponse()
                self.assertEqual(resp.read(), b'200 OK')
                self.assertEqual(resp.status, 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'http.client.request')
            self.assertEqual(span.error, 0)
            self.assertDictEqual(
                span.meta,
                {
                    'http.method': 'GET',
                    'http.status_code': '200',
                    'http.url': 'http://httpstat.us/200',
                }
            )

        def test_http_client_request_post_request(self):
            """
            When making a POST request via http.client.HTTPConnection.request
                we return the original response
                we capture a span for the request
            """
            conn = http.client.HTTPConnection('httpstat.us')
            with contextlib.closing(conn):
                conn.request('POST', '/200', body='key=value')
                resp = conn.getresponse()
                self.assertEqual(resp.read(), b'200 OK')
                self.assertEqual(resp.status, 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'http.client.request')
            self.assertEqual(span.error, 0)
            self.assertDictEqual(
                span.meta,
                {
                    'http.method': 'POST',
                    'http.status_code': '200',
                    'http.url': 'http://httpstat.us/200',
                }
            )

        def test_http_client_request_get_request_query_string(self):
            """
            When making a GET request with a query string via http.client.HTTPConnection.request
                we capture a the entire url in the span
            """
            conn = http.client.HTTPConnection('httpstat.us')
            with contextlib.closing(conn):
                conn.request('GET', '/200?key=value&key2=value2')
                resp = conn.getresponse()
                self.assertEqual(resp.read(), b'200 OK')
                self.assertEqual(resp.status, 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'http.client.request')
            self.assertEqual(span.error, 0)
            self.assertDictEqual(
                span.meta,
                {
                    'http.method': 'GET',
                    'http.status_code': '200',
                    'http.url': 'http://httpstat.us/200?key=value&key2=value2',
                }
            )

        def test_http_client_request_500_request(self):
            """
            When making a GET request via http.client.HTTPConnection.request
                when the response is a 500
                    we raise the original exception
                    we mark the span as an error
                    we capture the correct span tags
            """
            try:
                conn = http.client.HTTPConnection('httpstat.us')
                with contextlib.closing(conn):
                    conn.request('GET', '/500')
                    conn.getresponse()
            except http.client.HTTPException:
                resp = sys.exc_info()[1]
                self.assertEqual(resp.read(), b'500 Internal Server Error')
                self.assertEqual(resp.status, 500)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'http.client.request')
            self.assertEqual(span.error, 1)
            self.assertEqual(span.get_tag('http.method'), 'GET')
            self.assertEqual(span.get_tag('http.status_code'), '500')
            self.assertEqual(span.get_tag('http.url'), 'http://httpstat.us/500')

        def test_http_client_request_non_200_request(self):
            """
            When making a GET request via http.client.HTTPConnection.request
                when the response is a non-200
                    we raise the original exception
                    we mark the span as an error
                    we capture the correct span tags
            """
            try:
                conn = http.client.HTTPConnection('httpstat.us')
                with contextlib.closing(conn):
                    conn.request('GET', '/404')
                    conn.getresponse()
            except http.client.HTTPException:
                resp = sys.exc_info()[1]
                self.assertEqual(resp.read(), b'404 Not Found')
                self.assertEqual(resp.status, 404)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'http.client.request')
            self.assertEqual(span.error, 0)
            self.assertEqual(span.get_tag('http.method'), 'GET')
            self.assertEqual(span.get_tag('http.status_code'), '404')
            self.assertEqual(span.get_tag('http.url'), 'http://httpstat.us/404')

        def test_http_client_request_get_request_disabled(self):
            """
            When making a GET request via http.client.HTTPConnection.request
                when the tracer is disabled
                    we do not capture any spans
            """
            self.tracer.enabled = False
            conn = http.client.HTTPConnection('httpstat.us')
            with contextlib.closing(conn):
                conn.request('GET', '/200')
                resp = conn.getresponse()
                self.assertEqual(resp.read(), b'200 OK')
                self.assertEqual(resp.status, 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 0)

        def test_urllib_request(self):
            """
            When making a request via urllib.request.urlopen
               we return the original response
               we capture a span for the request
            """
            resp = urllib.request.urlopen('http://httpstat.us/200')
            self.assertEqual(resp.read(), b'200 OK')
            self.assertEqual(resp.getcode(), 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'http.client.request')
            self.assertEqual(span.error, 0)
            self.assertEqual(span.get_tag('http.method'), 'GET')
            self.assertEqual(span.get_tag('http.status_code'), '200')
            self.assertEqual(span.get_tag('http.url'), 'http://httpstat.us/200')

        def test_urllib_request_object(self):
            """
            When making a request via urllib.request.urlopen
               with a urllib.request.Request object
                   we return the original response
                   we capture a span for the request
            """
            req = urllib.request.Request('http://httpstat.us/200')
            resp = urllib.request.urlopen(req)
            self.assertEqual(resp.read(), b'200 OK')
            self.assertEqual(resp.getcode(), 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'http.client.request')
            self.assertEqual(span.error, 0)
            self.assertEqual(span.get_tag('http.method'), 'GET')
            self.assertEqual(span.get_tag('http.status_code'), '200')
            self.assertEqual(span.get_tag('http.url'), 'http://httpstat.us/200')

        def test_urllib_request_opener(self):
            """
            When making a request via urllib.request.OpenerDirector
               we return the original response
               we capture a span for the request
            """
            opener = urllib.request.build_opener()
            resp = opener.open('http://httpstat.us/200')
            self.assertEqual(resp.read(), b'200 OK')
            self.assertEqual(resp.getcode(), 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'http.client.request')
            self.assertEqual(span.error, 0)
            self.assertEqual(span.get_tag('http.method'), 'GET')
            self.assertEqual(span.get_tag('http.status_code'), '200')
            self.assertEqual(span.get_tag('http.url'), 'http://httpstat.us/200')
