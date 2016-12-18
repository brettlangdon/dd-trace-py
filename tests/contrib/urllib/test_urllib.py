# Standard library
import sys
import unittest

# Third party
import wrapt

# Project
from ddtrace.compat import PY2
from ddtrace.contrib.urllib import patch, unpatch
from ...test_tracer import get_dummy_tracer


if PY2:
    import urllib
    import urllib2

    class UrllibPython2Test(unittest.TestCase):
        def setUp(self):
            patch()
            self.tracer = get_dummy_tracer()
            setattr(urllib.urlopen, 'datadog_tracer', self.tracer)
            setattr(urllib2.urlopen, 'datadog_tracer', self.tracer)

        def tearDown(self):
            unpatch()

        def test_patch(self):
            """
            When patching urllib
                we patch the correct module/methods
            """
            self.assertIsInstance(urllib.urlopen, wrapt.FunctionWrapper)
            self.assertIsInstance(urllib2.urlopen, wrapt.FunctionWrapper)

        def test_unpatch(self):
            """
            When unpatching urllib
                we restore the correct module/methods
            """
            original_urllib = urllib.urlopen.__wrapped__
            original_urllib2 = urllib2.urlopen.__wrapped__
            unpatch()

            self.assertEqual(urllib.urlopen, original_urllib)
            self.assertEqual(urllib2.urlopen, original_urllib2)

        def test_urllib_get_request(self):
            """
            When making a GET request via urllib.urlopen
                we return the original response
                we capture a span for the request
            """
            url = 'http://httpstat.us/200'
            resp = urllib.urlopen(url)
            self.assertEqual(resp.read(), '200 OK')
            self.assertEqual(resp.code, 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'urllib.urlopen')
            self.assertEqual(span.error, 0)
            self.assertDictEqual(
                span.meta,
                {
                    'http.method': 'GET',
                    'http.status_code': '200',
                    'http.url': 'http://httpstat.us/200',
                }
            )

        def test_urllib_post_request(self):
            """
            When making a GET request via urllib.urlopen
                we return the original response
                we capture a span for the request
            """
            url = 'http://httpstat.us/200'
            resp = urllib.urlopen(url, data='key=value')
            self.assertEqual(resp.read(), '200 OK')
            self.assertEqual(resp.code, 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'urllib.urlopen')
            self.assertEqual(span.error, 0)
            self.assertDictEqual(
                span.meta,
                {
                    'http.method': 'POST',
                    'http.status_code': '200',
                    'http.url': 'http://httpstat.us/200',
                }
            )

        def test_urllib_500_request(self):
            """
            When making a GET request via urllib.urlopen
                when the response is a 500
                    we return the original response
                    we capture a span for the request
                    we capture the span as an error
            """
            url = 'http://httpstat.us/500'
            resp = urllib.urlopen(url)
            self.assertEqual(resp.read(), '500 Internal Server Error')
            self.assertEqual(resp.code, 500)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'urllib.urlopen')
            self.assertEqual(span.error, 1)
            self.assertDictEqual(
                span.meta,
                {
                    'http.method': 'GET',
                    'http.status_code': '500',
                    'http.url': 'http://httpstat.us/500',
                }
            )

        def test_urllib_non_200_request(self):
            """
            When making a GET request via urllib.urlopen
                when the response is a non-200
                    we return the original response
                    we capture a span for the request
                    we do not capture the response as an error
            """
            url = 'http://httpstat.us/404'
            resp = urllib.urlopen(url)
            self.assertEqual(resp.read(), '404 Not Found')
            self.assertEqual(resp.code, 404)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'urllib.urlopen')
            self.assertEqual(span.error, 0)
            self.assertDictEqual(
                span.meta,
                {
                    'http.method': 'GET',
                    'http.status_code': '404',
                    'http.url': 'http://httpstat.us/404',
                }
            )

        def test_urllib_query_string_request(self):
            """
            When making a GET request with a query string via urllib.urlopen
                we capture the correct url in the span
            """
            url = 'http://httpstat.us/200?key=value&key2=value2'
            resp = urllib.urlopen(url)
            self.assertEqual(resp.read(), '200 OK')
            self.assertEqual(resp.code, 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'urllib.urlopen')
            self.assertEqual(span.error, 0)
            self.assertDictEqual(
                span.meta,
                {
                    'http.method': 'GET',
                    'http.status_code': '200',
                    'http.url': 'http://httpstat.us/200?key=value&key2=value2',
                }
            )

        def test_urllib_get_request_disabled(self):
            """
            When making a GET request via urllib.urlopen
                when the tracer is disabled
                    we do not capture any spans
            """
            self.tracer.enabled = False
            url = 'http://httpstat.us/200'
            resp = urllib.urlopen(url)
            self.assertEqual(resp.read(), b'200 OK')
            self.assertEqual(resp.code, 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 0)

        def test_urllib2_get_request_string(self):
            """
            When making a GET request via urllib2.urlopen
                we return the original response
                we capture a span for the request
            """
            url = 'http://httpstat.us/200'
            resp = urllib2.urlopen(url)
            self.assertEqual(resp.read(), '200 OK')
            self.assertEqual(resp.code, 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'urllib2.urlopen')
            self.assertEqual(span.error, 0)
            self.assertDictEqual(
                span.meta,
                {
                    'http.method': 'GET',
                    'http.status_code': '200',
                    'http.url': 'http://httpstat.us/200',
                }
            )

        def test_urllib2_post_request_string(self):
            """
            When making a POST request via urllib2.urlopen
                we return the original response
                we capture a span for the request
            """
            url = 'http://httpstat.us/200'
            resp = urllib2.urlopen(url, data='key=value')
            self.assertEqual(resp.read(), '200 OK')
            self.assertEqual(resp.code, 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'urllib2.urlopen')
            self.assertEqual(span.error, 0)
            self.assertDictEqual(
                span.meta,
                {
                    'http.method': 'POST',
                    'http.status_code': '200',
                    'http.url': 'http://httpstat.us/200',
                }
            )

        def test_urllib2_get_request_query_string(self):
            """
            When making a GET request with a query string via urllib2.urlopen
                we capture a the entire url in the span
            """
            url = 'http://httpstat.us/200?key=value&key2=value2'
            resp = urllib2.urlopen(url)
            self.assertEqual(resp.read(), '200 OK')
            self.assertEqual(resp.code, 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'urllib2.urlopen')
            self.assertEqual(span.error, 0)
            self.assertDictEqual(
                span.meta,
                {
                    'http.method': 'GET',
                    'http.status_code': '200',
                    'http.url': 'http://httpstat.us/200?key=value&key2=value2',
                }
            )

        def test_urllib2_500_request(self):
            """
            When making a GET request via urllib2.urlopen
                when the response is a 500
                    we raise the original exception
                    we mark the span as an error
                    we capture the correct span tags
            """
            url = 'http://httpstat.us/500'
            try:
                urllib2.urlopen(url)
            except urllib2.HTTPError:
                resp = sys.exc_info()[1]
                self.assertEqual(resp.read(), '500 Internal Server Error')
                self.assertEqual(resp.code, 500)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'urllib2.urlopen')
            self.assertEqual(span.error, 1)
            self.assertEqual(span.get_tag('http.method'), 'GET')
            self.assertEqual(span.get_tag('http.status_code'), '500')
            self.assertEqual(span.get_tag('http.url'), 'http://httpstat.us/500')

        def test_urllib2_non_200_request(self):
            """
            When making a GET request via urllib2.urlopen
                when the response is a non-200
                    we raise the original exception
                    we mark the span as an error
                    we capture the correct span tags
            """
            url = 'http://httpstat.us/404'
            try:
                urllib2.urlopen(url)
            except urllib2.HTTPError:
                resp = sys.exc_info()[1]
                self.assertEqual(resp.read(), '404 Not Found')
                self.assertEqual(resp.code, 404)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'urllib2.urlopen')
            self.assertEqual(span.error, 1)
            self.assertEqual(span.get_tag('http.method'), 'GET')
            self.assertEqual(span.get_tag('http.status_code'), '404')
            self.assertEqual(span.get_tag('http.url'), 'http://httpstat.us/404')

        def test_urllib2_get_request_object(self):
            """
            When making a GET request via urllib2.urlopen
                when the request is a urllib.Request object
                    we capture the span as expected
            """
            url = 'http://httpstat.us/200'
            req = urllib2.Request(url=url)
            resp = urllib2.urlopen(req)
            self.assertEqual(resp.read(), '200 OK')
            self.assertEqual(resp.code, 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'urllib2.urlopen')
            self.assertEqual(span.error, 0)
            self.assertDictEqual(
                span.meta,
                {
                    'http.method': 'GET',
                    'http.status_code': '200',
                    'http.url': 'http://httpstat.us/200',
                }
            )

        def test_urllib2_post_request_object(self):
            """
            When making a POST request via urllib2.urlopen
                when the request is a urllib.Request object
                    we capture the span as expected
            """
            url = 'http://httpstat.us/200'
            req = urllib2.Request(url=url, data='key=value')
            resp = urllib2.urlopen(req)
            self.assertEqual(resp.read(), '200 OK')
            self.assertEqual(resp.code, 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'urllib2.urlopen')
            self.assertEqual(span.error, 0)
            self.assertDictEqual(
                span.meta,
                {
                    'http.method': 'POST',
                    'http.status_code': '200',
                    'http.url': 'http://httpstat.us/200',
                }
            )

        def test_urllib2_get_request_disabled(self):
            """
            When making a GET request via urllib2.urlopen
                when the tracer is disabled
                    we do not capture any spans
            """
            self.tracer.enabled = False
            url = 'http://httpstat.us/200'
            resp = urllib2.urlopen(url)
            self.assertEqual(resp.read(), b'200 OK')
            self.assertEqual(resp.code, 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 0)

else:
    import urllib.error
    import urllib.request

    class UrllibPython3Test(unittest.TestCase):
        def setUp(self):
            patch()
            self.tracer = get_dummy_tracer()
            setattr(urllib.request.urlopen, 'datadog_tracer', self.tracer)

        def tearDown(self):
            unpatch()

        def test_patch(self):
            """
            When patching the urllib module
                we wrap the expected module/function
            """
            self.assertIsInstance(urllib.request.urlopen, wrapt.FunctionWrapper)

        def test_unpatch(self):
            """
            When unpatching the urllib module
                we restore the original module/function
            """
            original_urlopen = urllib.request.urlopen.__wrapped__
            unpatch()

            self.assertEqual(urllib.request.urlopen, original_urlopen)

        def test_urllib_get_request_string(self):
            """
            When making a GET request via urllib.request.urlopen
                we return the original response
                we capture a span for the request
            """
            url = 'http://httpstat.us/200'
            resp = urllib.request.urlopen(url)
            self.assertEqual(resp.read(), b'200 OK')
            self.assertEqual(resp.code, 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'urllib.request.urlopen')
            self.assertEqual(span.error, 0)
            self.assertDictEqual(
                span.meta,
                {
                    'http.method': 'GET',
                    'http.status_code': '200',
                    'http.url': 'http://httpstat.us/200',
                }
            )

        def test_urllib_post_request_string(self):
            """
            When making a POST request via urllib.request.urlopen
                we return the original response
                we capture a span for the request
            """
            url = 'http://httpstat.us/200'
            resp = urllib.request.urlopen(url, data=b'key=value')
            self.assertEqual(resp.read(), b'200 OK')
            self.assertEqual(resp.code, 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'urllib.request.urlopen')
            self.assertEqual(span.error, 0)
            self.assertDictEqual(
                span.meta,
                {
                    'http.method': 'POST',
                    'http.status_code': '200',
                    'http.url': 'http://httpstat.us/200',
                }
            )

        def test_urllib_get_request_query_string(self):
            """
            When making a GET request with a query string via urllib.request.urlopen
                we return the original response
                we capture a span for the request
                we capture the entire url in the span tags
            """
            url = 'http://httpstat.us/200?key=value&key2=value2'
            resp = urllib.request.urlopen(url)
            self.assertEqual(resp.read(), b'200 OK')
            self.assertEqual(resp.code, 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'urllib.request.urlopen')
            self.assertEqual(span.error, 0)
            self.assertDictEqual(
                span.meta,
                {
                    'http.method': 'GET',
                    'http.status_code': '200',
                    'http.url': 'http://httpstat.us/200?key=value&key2=value2',
                }
            )

        def test_urllib_500_request(self):
            """
            When making a GET request via urllib.request.urlopen
                when the response is a 500
                    we raise the original exception
                    we capture the span as an error
            """
            url = 'http://httpstat.us/500'
            try:
                urllib.request.urlopen(url)
            except urllib.error.HTTPError:
                resp = sys.exc_info()[1]
                self.assertEqual(resp.read(), b'500 Internal Server Error')
                self.assertEqual(resp.code, 500)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'urllib.request.urlopen')
            self.assertEqual(span.error, 1)
            self.assertEqual(span.get_tag('http.method'), 'GET')
            self.assertEqual(span.get_tag('http.status_code'), '500')
            self.assertEqual(span.get_tag('http.url'), 'http://httpstat.us/500')

        def test_urllib_non_200_request(self):
            """
            When making a GET request via urllib.request.urlopen
                when the response is a non-200
                    we raise the original exception
                    we capture the span as an error
            """
            url = 'http://httpstat.us/404'
            try:
                urllib.request.urlopen(url)
            except urllib.error.HTTPError:
                resp = sys.exc_info()[1]
                self.assertEqual(resp.read(), b'404 Not Found')
                self.assertEqual(resp.code, 404)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'urllib.request.urlopen')
            self.assertEqual(span.error, 1)
            self.assertEqual(span.get_tag('http.method'), 'GET')
            self.assertEqual(span.get_tag('http.status_code'), '404')
            self.assertEqual(span.get_tag('http.url'), 'http://httpstat.us/404')

        def test_urllib_get_request_object(self):
            """
            When making a GET request via urllib.request.urlopen
                when the request is a urllib.request.Request object
                    we capture the span as expected
            """
            url = 'http://httpstat.us/200'
            req = urllib.request.Request(url=url)
            resp = urllib.request.urlopen(req)
            self.assertEqual(resp.read(), b'200 OK')
            self.assertEqual(resp.code, 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'urllib.request.urlopen')
            self.assertEqual(span.error, 0)
            self.assertDictEqual(
                span.meta,
                {
                    'http.method': 'GET',
                    'http.status_code': '200',
                    'http.url': 'http://httpstat.us/200',
                }
            )

        def test_urllib_post_request_object(self):
            """
            When making a POST request via urllib.request.urlopen
                when the request is a urllib.request.Request object
                    we capture the span as expected
            """
            url = 'http://httpstat.us/200'
            req = urllib.request.Request(url=url, data=b'key=value')
            resp = urllib.request.urlopen(req)
            self.assertEqual(resp.read(), b'200 OK')
            self.assertEqual(resp.code, 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 1)
            span = spans[0]
            self.assertEqual(span.span_type, 'http')
            self.assertIsNone(span.service)
            self.assertEqual(span.name, 'urllib.request.urlopen')
            self.assertEqual(span.error, 0)
            self.assertDictEqual(
                span.meta,
                {
                    'http.method': 'POST',
                    'http.status_code': '200',
                    'http.url': 'http://httpstat.us/200',
                }
            )

        def test_urllib_get_request_disabled(self):
            """
            When making a GET request via urllib.request.urlopen
                when the tracer is disabled
                    we do not capture any spans
            """
            self.tracer.enabled = False
            url = 'http://httpstat.us/200'
            resp = urllib.request.urlopen(url)
            self.assertEqual(resp.read(), b'200 OK')
            self.assertEqual(resp.code, 200)

            spans = self.tracer.writer.pop()
            self.assertEqual(len(spans), 0)
