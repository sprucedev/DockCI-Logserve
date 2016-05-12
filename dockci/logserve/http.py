""" Setup and run the DockCI log server API server """
import logging

from aiohttp import web

from .util import run_wrapper


APP = web.Application()


@run_wrapper('http')
def run(logger, add_stop_handler):
    web.run_app(APP)


async def handle_health(request):
    return web.Response(body='{"message": "Not Implemented"}'.encode())


APP.router.add_route('GET', '/_healthz', handle_health)
