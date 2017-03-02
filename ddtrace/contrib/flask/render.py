import flask.templating
import wrapt

from ...ext import http
from ...util import require_pin


def patch_render(pin=None):
    _render = getattr(flask.templating, '_render', None)

    if not _render or isinstance(_render, wrapt.ObjectProxy):
        return

    setattr(flask.templating, '_render', wrapt.FunctionWrapper(_render, _traced_render))
    pin.onto(flask.templating)


def unpatch_render():
    _render = getattr(flask.templating, '_render', None)
    if not _render or not isinstance(_render, wrapt.ObjectProxy):
        return

    setattr(flask.templating, '_render', _render.__wrapped__)


@require_pin
def _traced_render(pin, func, instance, args, kwargs):
    if not pin or not pin.enabled():
        return func(*args, **kwargs)

    template = args[0] if len(args) else None
    if not template:
        return func(*args, **kwargs)

    template_name = template.name or 'string'
    with pin.tracer.trace('flask.template', span_type=http.TEMPLATE, resource=template_name) as span:
        span.set_tag('flask.template', template_name)
        return func(*args, **kwargs)
