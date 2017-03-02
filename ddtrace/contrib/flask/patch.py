from .app import patch_app, unpatch_app
from .render import patch_render, unpatch_render


def patch(app=None, pin=None):
    patch_app(app=app, pin=pin)
    patch_render(pin=pin)


def unpatch(app=None):
    unpatch_app(app=app)
    unpatch_render()
