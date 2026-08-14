"""Solara plus a same-origin route that serves each session's tile archives.

Tile servers running inside the kernel bind ``127.0.0.1``, so a browser
anywhere else cannot reach them. For PMTiles nothing has to: the archive on
disk already is the payload the browser asks for by range, so this serves the
file and leaves the tile server out of the request path entirely.

That matters here because one container serves many authenticated SEPAL users.
``vectortileserver``'s own endpoint merges every client's allowed directories
into one process-wide config, making it only as restrictive as its most
permissive client; serving the file ourselves keeps one user's archives out of
another's reach, which :func:`_authorize` enforces per request.

Run it with::

    SOLARA_APP=app.py uvicorn asgi:app --host=0.0.0.0 --port=8768 \
        --root-path=/api/app-launcher/sepal-gee-bundle
"""

import solara.server.starlette as solara_starlette
from solara.server import kernel_context, server
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, Response
from starlette.routing import Mount, Route

from apps._commons.tiles import resolve_in_session

#: Archives are the only thing the route is willing to serve.
TILE_SUFFIX = ".pmtiles"


def _authorize(request: Request, kernel_id: str) -> Response | None:
    """Confirm the requester owns ``kernel_id``, or return the refusal.

    Mirrors the check Solara applies to its own eviction route: the kernel must
    exist, and the session cookie the browser sends must be the one that opened
    it. Fails closed -- an unknown kernel is a 404, a mismatch a 403.

    Args:
        request: the incoming tile request.
        kernel_id: the kernel whose directory is being read.

    Returns:
        ``None`` when the requester is authorized, else the response to send.
    """
    context = kernel_context.contexts.get(kernel_id, None)
    if context is None:
        return Response(status_code=404)

    session_id = request.cookies.get(server.COOKIE_KEY_SESSION_ID)
    if not session_id or session_id != context.session_id:
        return Response(status_code=403)

    return None


async def tile_archive(request: Request) -> Response:
    """Serve one PMTiles archive out of its own session's directory.

    Mirrors ``vectortileserver``'s own endpoint contract -- a literal
    ``pmtiles`` segment plus a ``filePath`` query parameter -- because the
    layer builds its URL as ``{client_prefix}/pmtiles?filePath=...`` and the
    path it sends is absolute.

    ``FileResponse`` already parses ``Range`` and answers ``206``/``416``,
    which is the whole protocol PMTiles needs.

    Args:
        request: carries the ``kernel_id`` path parameter and ``filePath``.

    Returns:
        the archive, or 400/403/404 when the requester may not have it.
    """
    kernel_id = request.path_params["kernel_id"]

    refusal = _authorize(request, kernel_id)
    if refusal is not None:
        return refusal

    file_path = request.query_params.get("filePath")
    if not file_path:
        return Response(status_code=400)

    if not file_path.endswith(TILE_SUFFIX):
        return Response(status_code=404)

    try:
        path = resolve_in_session(kernel_id, file_path)
    except ValueError:
        return Response(status_code=404)

    if not path.is_file():
        return Response(status_code=404)

    return FileResponse(path)


# Solara's own routes end in catch-alls that swallow anything mounted after
# them, so ours are listed first. Its lifespan and middleware are passed
# through: without them the pages still render, but gzip, the session and
# authentication middleware, the startup validation and the shutdown drain of
# the state worker are all lost.
app = Starlette(
    routes=[
        Route("/tiles/{kernel_id}/pmtiles", endpoint=tile_archive),
        Mount("/", routes=solara_starlette.routes),
    ],
    lifespan=solara_starlette.lifespan,
    middleware=solara_starlette.middleware,
)
