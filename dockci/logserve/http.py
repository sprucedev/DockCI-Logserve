""" Setup and run the DockCI log server API server """
from aiohttp import web

from .util import run_wrapper


APP = web.Application()


@run_wrapper('http')
def run(*_):
    """ Run the HTTP API server """
    web.run_app(APP)


@asyncio.coroutine
def handle_health(_):
    """ API health check """
    return web.Response(body='{"message": "Not Implemented"}'.encode())


APP.router.add_route('GET', '/_healthz', handle_health)
