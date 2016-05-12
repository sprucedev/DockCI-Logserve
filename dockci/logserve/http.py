""" Setup and run the DockCI log server API server """
import asyncio

import py

from aiohttp import web

from .util import run_wrapper


APP = web.Application()


@run_wrapper('http')
def run(logger, *_):
    """ Run the HTTP API server """
    APP.logger = logger
    web.run_app(APP)


@asyncio.coroutine
def handle_health(_):
    """ API health check """
    return web.Response(body='{"message": "Not Implemented"}'.encode())


APP.router.add_route('GET', '/_healthz', handle_health)


@asyncio.coroutine
def handle_log(request):
    # import logging
    # logging.info(request.GET['a'])
    params = request.match_info
    log_path = py.path.local('data').join(
        params['project_slug'],
        params['job_slug'],
        params['stage_slug'],
    )
    if not log_path.check():
        APP.logger.warning(
            'Log for project %s job %s stage %s not found',
            params['project_slug'], params['job_slug'], params['stage_slug'],
        )
        return web.Response(status=404)

    APP.logger.info(
        'Log for project %s job %s stage %s found',
        params['project_slug'], params['job_slug'], params['stage_slug'],
    )
    return web.Response(body="Found".encode(), status=200)


APP.router.add_route(
    'GET',
    '/projects/{project_slug}/jobs/{job_slug}/log_init/{stage_slug}',
    handle_log,
)
