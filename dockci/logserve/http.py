""" Setup and run the DockCI log server API server """
import asyncio
import concurrent

import py

from aiohttp import web

from .util import run_wrapper


APP = web.Application()


@run_wrapper('http')
def run(logger, *_):
    """ Run the HTTP API server """
    APP.logger = logger

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        APP.executor = executor
        web.run_app(APP)


@asyncio.coroutine
def handle_health(_):
    """ API health check """
    return web.Response(body='{"message": "Not Implemented"}'.encode())


APP.router.add_route('GET', '/_healthz', handle_health)


def _reader_bytes(handle, count=None, chunk_size=1024):
    """
    Read a given number of bytes

    Examples:

    >>> tmp_dir = getfixture('tmpdir')
    >>> tmp_file = tmp_dir.join('test')
    >>> tmp_file.write('abcdefghi')

    >>> handle = tmp_file.open()
    >>> handle.seek(4)
    4
    >>> list(_reader_bytes(handle, 2))
    ['ef']

    >>> handle = tmp_file.open()
    >>> handle.seek(4)
    4
    >>> list(_reader_bytes(handle, chunk_size=3))
    ['efg', 'hi']
    """
    remain = count
    while remain is None or remain > 0:
        if remain is not None:
            chunk_size = min(chunk_size, remain)

        data = handle.read(chunk_size)

        if remain is not None:
            remain -= len(data)

        if len(data) == 0:
            return

        yield data


def _reader_lines(handle, count=None):
    """
    Read a given number of lines

    Examples:

    >>> tmp_dir = getfixture('tmpdir')
    >>> tmp_file = tmp_dir.join('test')
    >>> tmp_file.write('abc\\ndef\\nghi\\njkl\\nmno')

    >>> handle = tmp_file.open()
    >>> handle.seek(4)
    4
    >>> list(_reader_lines(handle, 2))
    ['def\\n', 'ghi\\n']

    >>> handle = tmp_file.open()
    >>> handle.seek(8)
    8
    >>> list(_reader_lines(handle))
    ['ghi\\n', 'jkl\\n', 'mno']

    >>> handle = tmp_file.open()
    >>> handle.seek(5)
    5
    >>> list(_reader_lines(handle, 1))
    ['ef\\n']

    >>> tmp_file.write('abc\\n\\ndef\\n')
    >>> handle = tmp_file.open()
    >>> list(_reader_lines(handle))
    ['abc\\n', '\\n', 'def\\n', '']

    >>> handle = tmp_file.open('rb')
    >>> list(_reader_lines(handle))
    [b'abc\\n', b'\\n', b'def\\n', b'']
    """
    remain = count
    while remain is None or remain > 0:
        data = handle.readline()

        if remain is not None:
            remain -= 1

        yield data

        search_char = b'\n' if isinstance(data, bytes) else '\n'
        if search_char not in data:
            return


def _seeker_bytes(handle, seek):
    """
    Seek ahead in handle by the given number of bytes. If ``seek`` is
    negative, seeks that number of bytes from the end of the file

    Examples:

    >>> tmp_dir = getfixture('tmpdir')
    >>> tmp_file = tmp_dir.join('test')
    >>> tmp_file.write('abcdefghi')

    >>> handle = tmp_file.open()
    >>> _seeker_bytes(handle, 3)
    >>> handle.read(1)
    'd'

    >>> handle = tmp_file.open()
    >>> _seeker_bytes(handle, -3)
    >>> handle.read(1)
    'g'
    """
    if seek >= 0:
        handle.seek(seek)
    else:
        handle.seek(0, 2)
        file_size = handle.tell()
        handle.seek(file_size + seek)  # seek is negative


def _seeker_lines(handle, seek):
    """
    Seek ahead in handle by the given number of lines

    Examples:

    >>> tmp_dir = getfixture('tmpdir')
    >>> tmp_file = tmp_dir.join('test')
    >>> tmp_file.write('abc\\ndef\\nghi\\njkl\\nmno')

    >>> handle = tmp_file.open()
    >>> _seeker_lines(handle, 3)
    >>> handle.read(1)
    'j'

    >>> handle = tmp_file.open()
    >>> _seeker_lines(handle, -1)
    >>> handle.read(3)
    'mno'

    >>> handle = tmp_file.open()
    >>> _seeker_lines(handle, -3)
    >>> handle.read(1)
    'g'

    >>> handle = tmp_file.open()
    >>> _seeker_lines(handle, -20)
    >>> handle.read(3)
    'abc'

    >>> handle = tmp_file.open('rb')
    >>> _seeker_lines(handle, -20)
    >>> handle.read(3)
    b'abc'
    """
    if seek >= 0:
        for _ in range(seek):
            _seeker_lines_one_ahead(handle)
    else:
        handle.seek(0, 2)
        seek = seek * -1
        for idx in range(seek):
            current_pos = _seeker_lines_one_back(handle)

            if current_pos == 0:
                return

            # unless last iter, seek back 1 for the new line
            if idx + 1 < seek:
                handle.seek(current_pos - 1)


def _seeker_lines_one_ahead(handle):
    """
    Seek ahead in handle by 1 line

    Examples:

    >>> tmp_dir = getfixture('tmpdir')
    >>> tmp_file = tmp_dir.join('test')
    >>> tmp_file.write('abc\\ndef\\nghi\\njkl\\nmno')

    >>> handle = tmp_file.open()
    >>> handle.seek(10)
    10
    >>> _seeker_lines_one_ahead(handle)
    >>> handle.read(3)
    'jkl'
    >>>
    """
    while handle.read(1) not in ('\n', b'\n', None, '', b''):
        pass


def _seeker_lines_one_back(handle):
    """
    Seek back in handle by 1 line

    Examples:

    >>> tmp_dir = getfixture('tmpdir')
    >>> tmp_file = tmp_dir.join('test')
    >>> tmp_file.write('abc\\ndef\\nghi\\njkl\\nmno')

    >>> handle = tmp_file.open()
    >>> handle.seek(10)
    10
    >>> _seeker_lines_one_back(handle)
    8
    >>> handle.read(3)
    'ghi'

    >>> handle = tmp_file.open()
    >>> _seeker_lines_one_back(handle)
    0
    >>> handle.read(3)
    'abc'
    """
    first = True
    current_pos = handle.tell()
    while first or handle.read(1) not in ('\n', b'\n', None, '', b''):
        first = False
        current_pos -= 1

        if current_pos < 0:
            handle.seek(0)
            return 0

        handle.seek(current_pos)

    return current_pos + 1  # add 1 for the read


def try_qs_int(request, key):
    """
    Try to get a query string arg, and parse it as an ``int``. Returns
    ``None`` if the key doesn't exist, or if the value resolves to ``'None'``

    Examples:

    >>> from aiohttp import MultiDict
    >>> class TestClass(object):
    ...     pass
    >>> request = TestClass()

    >>> request.GET = MultiDict([
    ...     ('a', '1'),
    ...     ('b', '2'),
    ...     ('b', '3'),
    ...     ('c', b'4'),
    ...     ('d', 'None'),
    ...     ('e', b'None'),
    ...     ('f', 'null'),
    ...     ('g', b'null'),
    ... ])

    >>> try_qs_int(request, 'a')
    1

    >>> try_qs_int(request, 'b')
    2

    >>> try_qs_int(request, 'c')
    4

    >>> type(try_qs_int(request, 'no'))
    <class 'NoneType'>

    >>> type(try_qs_int(request, 'd'))
    <class 'NoneType'>

    >>> type(try_qs_int(request, 'e'))
    <class 'NoneType'>

    >>> type(try_qs_int(request, 'f'))
    <class 'NoneType'>

    >>> type(try_qs_int(request, 'g'))
    <class 'NoneType'>
    """
    try:
        value = request.GET[key]
    except KeyError:
        return None
    else:
        return (
            None if value in ('None', b'None', 'null', b'null')
            else int(value)
        )


@asyncio.coroutine
def handle_log(request):
    """ Handle streaming logs to a client """
    params = request.match_info

    log_dir = py.path.local('data').join(
        params['project_slug'],
        params['job_slug'],
    )

    # Handle .log ext for DockCI legacy data
    log_path_bare = log_dir.join(params['stage_slug'])
    log_path_ext = log_dir.join('%s.log' % params['stage_slug'])

    log_path = None
    if log_path_bare.check():
        log_path = log_path_bare
    elif log_path_ext.check():
        log_path = log_path_ext

    if log_path is None:
        return web.Response(status=404)

    byte_seek = try_qs_int(request, 'seek')
    line_seek = try_qs_int(request, 'seek_lines')
    bytes_count = try_qs_int(request, 'count')
    lines_count = try_qs_int(request, 'count_lines')

    if byte_seek and line_seek:
        return web.Response(
            body="byte_seek and line_seek are mutually exclusive".encode(),
            status=400,
        )
    if bytes_count and lines_count:
        return web.Response(
            body="bytes_count and lines_count are mutually exclusive".encode(),
            status=400,
        )

    response = web.StreamResponse(status=200, headers={
        'content-type': 'text/plain',
    })
    yield from response.prepare(request)

    with log_path.open('rb') as handle:
        if byte_seek is not None:
            _seeker_bytes(handle, byte_seek)
        if line_seek is not None:
            _seeker_lines(handle, line_seek)

        if bytes_count is not None:
            gen = _reader_bytes(handle, bytes_count)
        elif lines_count is not None:
            gen = _reader_lines(handle, lines_count)
        else:
            gen = _reader_bytes(handle)

        for data in gen:
            response.write(data)
            yield from response.drain()

    return response


APP.router.add_route(
    'GET',
    '/projects/{project_slug}/jobs/{job_slug}/log_init/{stage_slug}',
    handle_log,
)
