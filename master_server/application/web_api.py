import json
import logging
import time

from aiohttp import web
from aiohttp.web_log import AccessLogger
from collections import defaultdict

log = logging.getLogger(__name__)
routes = web.RouteTableDef()

# Time a server entry remains cached.
TIME_SERVER_ENTRY_CACHE = 60 * 5
# Time the serverlist remains cached.
TIME_SERVER_LIST_CACHE = 60 * 5


class JSONException(web.HTTPException):
    def __init__(
        self, data, *, status=400, reason=None, headers=None, content_type="application/json", dumps=json.dumps
    ):
        self.status_code = status
        text = dumps(data)
        super().__init__(text=text, reason=reason, headers=headers, content_type=content_type)


def in_path_server_id(server_id):
    if len(server_id) != 32 or any([u not in ("abcdef1234567890") for u in server_id]):
        raise JSONException({"message": "server_id is invalid"})

    return server_id


@routes.get("/healthz")
async def healthz_handler(request):
    return web.HTTPOk()


@routes.get("/server")
async def server_list(request):
    if request.app.server_list_cache is None or time.time() > request.app.server_list_cache["expire"]:
        request.app.server_list_cache = {
            "servers": request.app.database.get_server_list_for_web(),
            "expire": time.time() + TIME_SERVER_LIST_CACHE,
        }

    server_list = request.app.server_list_cache
    return web.json_response(server_list)


@routes.get("/server/{server_id}")
async def server_entry(request):
    server_id = in_path_server_id(request.match_info["server_id"])

    if (
        request.app.server_entry_cache[server_id] is None
        or time.time() > request.app.server_entry_cache[server_id]["expire"]
    ):
        request.app.server_entry_cache[server_id] = {
            "server": request.app.database.get_server_info_for_web(server_id),
            "expire": time.time() + TIME_SERVER_ENTRY_CACHE,
        }

    server_entry = request.app.server_entry_cache[server_id]
    return web.json_response(server_entry)


@routes.route("*", "/{tail:.*}")
async def fallback(request):
    log.warning("Unexpected URL: %s", request.url)
    return web.HTTPNotFound()


class ErrorOnlyAccessLogger(AccessLogger):
    def log(self, request, response, time):
        # Only log if the status was not successful
        if not (200 <= response.status < 400):
            super().log(request, response, time)


class Application:
    def __init__(self, database):
        self._web = web.Application()
        self._web.database = database
        self._web.add_routes(routes)

        self._web.server_list_cache = None
        self._web.server_entry_cache = defaultdict(lambda: None)

    def run(self, bind, _, web_port):
        web.run_app(self._web, host=bind, port=web_port, access_log_class=ErrorOnlyAccessLogger)
